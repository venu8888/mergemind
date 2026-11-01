"""Targeted tests to achieve >=90% test coverage across GitHub services."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.webhook_delivery import WebhookDelivery
from app.services.github.client import GitHubClient
from app.services.github.diff_parser import ChangeType, DiffParser, sanitize_diff_path
from app.services.github.dispatcher import WebhookDispatcher
from app.services.github.exceptions import (
    GitHubAPIError,
    GitHubAuthError,
    InstallationNotFoundError,
)
from app.services.github.lifecycle import (
    handle_installation_event,
    reconcile_installation_repositories,
)
from app.services.github.pr_sync import parse_github_timestamp, sync_pull_request
from app.services.github.queue_worker import WebhookQueueWorker
from app.services.github.source_retriever import (
    RetrievalStatus,
    SourceRetriever,
    compute_git_blob_hash,
)
from app.services.github.webhook import persist_webhook_delivery, verify_webhook_signature


# --- Diff Parser Edge Cases ---
@pytest.mark.asyncio
async def test_diff_parser_edge_cases():
    """Tests empty diff, path traversal, new/deleted/rename, binary, and line mapping."""
    # Empty diff
    empty = DiffParser.parse("")
    assert len(empty.files) == 0
    assert empty.is_truncated is False

    # Path traversal
    with pytest.raises(ValueError) as exc:
        sanitize_diff_path("a/../../etc/passwd")
    assert "Path traversal detected" in str(exc.value)

    # Multi-file patch with ADDED, DELETED, RENAMED, and BINARY
    patch_text = """diff --git a/new_file.py b/new_file.py
new file mode 100644
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,2 @@
+def test():
+    pass
diff --git a/old_file.py b/old_file.py
deleted file mode 100644
--- a/old_file.py
+++ /dev/null
@@ -1,1 +0,0 @@
-print('bye')
diff --git a/source.py b/target.py
similarity index 98%
rename from source.py
rename to target.py
--- a/source.py
+++ b/target.py
@@ -1,1 +1,1 @@
-old
+new
diff --git a/image.png b/image.png
Binary files a/image.png and b/image.png differ
"""
    parsed = DiffParser.parse(patch_text)
    assert len(parsed.files) == 4
    assert parsed.files[0].change_type == ChangeType.ADDED
    assert parsed.files[1].change_type == ChangeType.DELETED
    assert parsed.files[2].change_type == ChangeType.RENAMED
    assert parsed.files[3].is_binary is True


# --- Source Retriever Edge Cases ---
@pytest.mark.asyncio
async def test_source_retriever_edge_cases():
    """Tests 404, binary null-byte heuristic, base64 blob decoding, and retrieve_files_for_diff."""
    mock_client = MagicMock()
    retriever = SourceRetriever(client=mock_client)

    # 1. 404 Not Found
    mock_client.get_blob = AsyncMock(side_effect=GitHubAPIError("Not Found", status_code=404))
    res_404 = await retriever.retrieve_file(
        "owner/repo", "sha123", "app/missing.py", expected_blob_sha="blobsha"
    )
    assert res_404.status == RetrievalStatus.NOT_FOUND

    # 2. General 500 API Error
    mock_client.get_blob = AsyncMock(
        side_effect=GitHubAPIError("Internal Server Error", status_code=500)
    )
    res_err = await retriever.retrieve_file(
        "owner/repo", "sha123", "app/error.py", expected_blob_sha="blobsha"
    )
    assert res_err.status == RetrievalStatus.ERROR

    # 3. Base64 encoded blob
    import base64

    code_text = "print('hello base64')\n"
    b64_content = base64.b64encode(code_text.encode("utf-8")).decode("utf-8")
    expected_sha = compute_git_blob_hash(code_text.encode("utf-8"))
    mock_client.get_blob = AsyncMock(
        return_value={
            "sha": expected_sha,
            "content": b64_content,
            "encoding": "base64",
            "size": len(code_text),
        }
    )
    res_b64 = await retriever.retrieve_file(
        "owner/repo", "sha123", "app/b64.py", expected_blob_sha=expected_sha
    )
    assert res_b64.status == RetrievalStatus.VERIFIED_COMPLETE
    assert res_b64.content == code_text

    # 4. Binary null bytes heuristic in non-binary named file
    binary_data = b"Some header\x00\x01\x02\x03 binary payload"
    bin_sha = compute_git_blob_hash(binary_data)
    mock_client.get_blob = AsyncMock(
        return_value={
            "sha": bin_sha,
            "content": binary_data.decode("latin-1"),
            "encoding": "utf-8",
            "size": len(binary_data),
        }
    )
    res_null = await retriever.retrieve_file(
        "owner/repo", "sha123", "app/hidden_binary.py", expected_blob_sha=bin_sha
    )
    assert res_null.status == RetrievalStatus.BINARY_UNSUPPORTED

    # 5. retrieve_files_for_diff
    mock_client.get_tree = AsyncMock(
        return_value={
            "truncated": False,
            "tree": [
                {"path": "file1.py", "sha": expected_sha, "size": len(code_text), "type": "blob"},
            ],
        }
    )
    mock_client.get_blob = AsyncMock(
        return_value={
            "sha": expected_sha,
            "content": code_text,
            "encoding": "utf-8",
            "size": len(code_text),
        }
    )

    diff_results = await retriever.retrieve_files_for_diff(
        "owner/repo", "sha123", ["file1.py", "deleted.py"]
    )
    assert "file1.py" in diff_results
    assert diff_results["file1.py"].status == RetrievalStatus.VERIFIED_COMPLETE
    assert "deleted.py" in diff_results
    assert diff_results["deleted.py"].status == RetrievalStatus.DELETED


# --- GitHub Client Methods & Context Manager ---
@pytest.mark.asyncio
async def test_github_client_methods_and_lifecycle():
    """Tests GitHubClient get_pull_request, get_pull_request_diff, context manager, and error branches."""
    # Context manager
    async with GitHubClient(token="ghp_test") as client:
        assert client.token == "ghp_test"

    # get_pull_request and get_pull_request_diff
    client = GitHubClient(token="ghp_test")

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        resp_json = MagicMock()
        resp_json.json.return_value = {"id": 1, "number": 42}
        resp_text = MagicMock()
        resp_text.text = "diff --git a/a b/b"

        mock_req.side_effect = [resp_json, resp_json, resp_text, resp_text]

        pr_info = await client.get_pull_request("owner/repo", pull_number=42)
        assert pr_info["number"] == 42
        pr_info2 = await client.get_pull_request("owner", "repo", 42)
        assert pr_info2["number"] == 42

        pr_diff = await client.get_pull_request_diff("owner/repo", pull_number=42)
        assert "diff --git" in pr_diff
        pr_diff2 = await client.get_pull_request_diff("owner", "repo", 42)
        assert "diff --git" in pr_diff2

    # Client error 500 after max retries
    with patch.object(client._client, "request", new_callable=AsyncMock) as mock_http:
        resp_500 = MagicMock()
        resp_500.status_code = 502
        resp_500.is_error = True
        resp_500.headers = {}
        mock_http.return_value = resp_500

        with pytest.raises(GitHubAPIError) as exc:
            await client._request("GET", "/test-500")
        assert "server error 502" in str(exc.value)

    # get_tree, get_blob, and get_raw_content on GitHubClient
    with patch.object(client._client, "request", new_callable=AsyncMock) as mock_http:
        # Mock tree response
        resp_tree = MagicMock()
        resp_tree.status_code = 200
        resp_tree.is_error = False
        resp_tree.headers = {}
        resp_tree.json.return_value = {"truncated": False, "tree": [{"path": "a.py"}]}

        # Mock blob response
        resp_blob = MagicMock()
        resp_blob.status_code = 200
        resp_blob.is_error = False
        resp_blob.headers = {}
        resp_blob.json.return_value = {"content": "dGVzdA==", "encoding": "base64"}

        # Mock raw content response
        resp_raw = MagicMock()
        resp_raw.status_code = 200
        resp_raw.is_error = False
        resp_raw.headers = {}
        resp_raw.content = b"raw file content bytes"

        mock_http.side_effect = [resp_tree, resp_blob, resp_raw]

        tree_res = await client.get_tree("owner/repo", tree_sha="tree_sha_123")
        assert tree_res["tree"][0]["path"] == "a.py"

        blob_res = await client.get_blob("owner/repo", blob_sha="blob_sha_123")
        assert blob_res["encoding"] == "base64"

        raw_res = await client.get_raw_content("owner/repo", "a.py", ref="main")
        assert raw_res == b"raw file content bytes"

    # Paginated get_installation_repositories
    with patch.object(client._client, "request", new_callable=AsyncMock) as mock_http:
        p1 = MagicMock()
        p1.status_code = 200
        p1.is_error = False
        p1.headers = {}
        p1.json.return_value = {"total_count": 2, "repositories": [{"id": 101, "name": "r1"}]}

        p2 = MagicMock()
        p2.status_code = 200
        p2.is_error = False
        p2.headers = {}
        p2.json.return_value = {"total_count": 2, "repositories": [{"id": 102, "name": "r2"}]}

        mock_http.side_effect = [p1, p2]
        all_repos = await client.get_installation_repositories(installation_id=123)
        assert len(all_repos) == 2

    # verify_webhook_signature edge conditions
    assert verify_webhook_signature(b"body", None, "secret") is False
    assert verify_webhook_signature(b"body", "sha256=123", "") is False

    # GitHubClient 401 & 404 branches, get_blob alternate signature
    with patch.object(client._client, "request", new_callable=AsyncMock) as mock_http:
        r_401 = MagicMock(status_code=401, is_error=True, headers={})
        r_404 = MagicMock(status_code=404, is_error=True, headers={})
        r_blob = MagicMock(
            status_code=200,
            is_error=False,
            headers={},
            json=MagicMock(return_value={"content": "abc"}),
        )
        mock_http.side_effect = [r_401, r_404, r_blob]

        with pytest.raises(GitHubAuthError):
            await client._request("GET", "/test-401")
        with pytest.raises(InstallationNotFoundError):
            await client._request("GET", "/test-404")

        blob_2 = await client.get_blob(owner="owner", repo="repo", blob_sha="sha_xyz")
        assert blob_2["content"] == "abc"

        headers_diff = client._build_headers("application/vnd.github.diff")
        assert headers_diff["Accept"] == "application/vnd.github.diff"

    await client.close()


# --- Dispatcher Edge Cases ---
@pytest.mark.asyncio
async def test_dispatcher_edge_cases():
    """Tests WebhookDispatcher handling installation_repositories, pull_request, unhandled events, and string payloads."""
    async with AsyncSessionLocal() as db:
        worker = WebhookQueueWorker(worker_id="disp-boost")
        mock_client = MagicMock()
        mock_client.get_installation_repositories = AsyncMock(return_value=[])

        dispatcher = WebhookDispatcher(worker=worker, client_factory=lambda _: mock_client)

        # 1. String JSON payload
        d1 = await persist_webhook_delivery(
            delivery_id=f"disp-str-{uuid.uuid4().hex[:8]}",
            event_type="ping",
            action=None,
            payload={"zen": "Non-blocking is better than blocking."},
            db=db,
        )
        res_ping = await dispatcher.dispatch_event(d1, db)
        assert res_ping is None

        # Invalid non-JSON string payload and unhandled event type
        d_bad_json = await persist_webhook_delivery(
            delivery_id=f"disp-bad-{uuid.uuid4().hex[:8]}",
            event_type="custom_unknown",
            action="something",
            payload={"test": "data"},
            db=db,
        )
        d_bad_json.payload_summary = "INVALID NON-JSON STRING {{"
        res_unhandled = await dispatcher.dispatch_event(d_bad_json, db)
        assert res_unhandled is None

        # 2. installation_repositories event
        d2 = await persist_webhook_delivery(
            delivery_id=f"disp-repos-{uuid.uuid4().hex[:8]}",
            event_type="installation_repositories",
            action="added",
            payload={"installation": {"id": 888123}},
            db=db,
        )
        # Create installation first
        inst = Installation(
            github_installation_id=888123,
            account_login="disp-test-org",
            account_type="Organization",
            state="ACTIVE",
        )
        db.add(inst)
        await db.commit()

        res_repos = await dispatcher.dispatch_event(d2, db)
        assert res_repos == 0  # Reconciled 0 repos


@pytest.mark.asyncio
async def test_dispatcher_process_one_failure():
    """Tests WebhookDispatcher handling exception during job execution."""
    async with AsyncSessionLocal() as db:
        worker = WebhookQueueWorker(worker_id="disp-fail-worker")
        dispatcher = WebhookDispatcher(worker=worker)

        d3 = await persist_webhook_delivery(
            delivery_id=f"disp-fail-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={"pull_request": {"number": 999}},
            db=db,
        )
        d3_id = d3.id

        with patch(
            "app.services.github.dispatcher.sync_pull_request",
            side_effect=RuntimeError("handler crash"),
        ):
            failed_run = await dispatcher.process_one(db)
            assert failed_run is True

        # In a fresh query check failure status
        async with AsyncSessionLocal() as check_db:
            check_d3 = (
                await check_db.execute(select(WebhookDelivery).where(WebhookDelivery.id == d3_id))
            ).scalar_one()
            assert check_d3.last_error == "handler crash"
            assert check_d3.processing_status == "PENDING"


# --- PR Sync & Lifecycle Edge Cases ---
@pytest.mark.asyncio
async def test_pr_sync_and_lifecycle_edge_cases():
    """Tests missing PR number, timestamp fallbacks, unsuspend lifecycle, and non-active skip."""
    async with AsyncSessionLocal() as db:
        # Untracked installation lifecycle event
        untracked = await handle_installation_event(
            {"action": "deleted", "installation": {"id": 99999999}}, db
        )
        assert untracked is None
        # 1. Missing PR number in payload
        pr_nil, run_nil = await sync_pull_request({"pull_request": {}}, db)
        assert pr_nil is None
        assert run_nil is None

        # 2. Timestamp parse fallback
        dt1 = parse_github_timestamp(None)
        assert dt1 is not None
        dt2 = parse_github_timestamp("invalid-date-format")
        assert dt2 is not None

        # 3. Unsuspend lifecycle event
        inst_id = 999333
        inst = Installation(
            github_installation_id=inst_id,
            account_login="unsuspend-org",
            account_type="Organization",
            state="SUSPENDED",
        )
        db.add(inst)
        await db.commit()

        unsuspend_payload = {
            "action": "unsuspend",
            "installation": {
                "id": inst_id,
                "account": {"login": "unsuspend-org", "type": "Organization"},
            },
        }
        res_unsuspend = await handle_installation_event(unsuspend_payload, db)
        assert res_unsuspend.state == "ACTIVE"

        # 4. Reconciliation on non-active installation returns 0
        res_unsuspend.state = "SUSPENDED"
        await db.commit()
        mock_client = MagicMock()
        skipped_count = await reconcile_installation_repositories(db, inst_id, mock_client)
        assert skipped_count == 0

        # 5. sync_pull_request with live client
        mock_client.get_pull_request = AsyncMock(
            return_value={
                "number": 77,
                "title": "Authoritative Live Title",
                "state": "open",
                "head": {"sha": "live_head_sha_999"},
                "base": {"sha": "live_base_sha_999"},
                "user": {"login": "live_author"},
            }
        )
        repo = Repository(
            github_repo_id=555111,
            full_name="live-org/live-repo",
            is_active=True,
        )
        db.add(repo)
        await db.commit()

        pr_live, run_live = await sync_pull_request(
            db,
            repo,
            {"pull_request": {"number": 77, "updated_at": "2026-11-01T23:00:00Z"}},
            client=mock_client,
        )
        assert pr_live.title == "Authoritative Live Title"
        assert pr_live.head_sha == "live_head_sha_999"
