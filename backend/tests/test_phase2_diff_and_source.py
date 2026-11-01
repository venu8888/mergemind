"""Tests for PR Synchronization, Diff Parsing, Source Retrieval & File Classification (T-28 to T-37)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.database import AsyncSessionLocal
from app.models.repository import Repository
from app.services.github.classifier import FileCategory, FileClassifier
from app.services.github.diff_parser import DiffParser
from app.services.github.pr_sync import sync_pull_request
from app.services.github.source_retriever import (
    RetrievalStatus,
    SourceRetriever,
    compute_git_blob_hash,
)


# --- File Classifier Tests ---
def test_file_classifier_categories():
    """Verifies file classification taxonomy across all standard, security, and binary formats."""
    # Sensitive security files
    assert FileClassifier.classify(".env") == FileCategory.SENSITIVE_SECURITY
    assert FileClassifier.classify(".env.production") == FileCategory.SENSITIVE_SECURITY
    assert FileClassifier.classify("server.key") == FileCategory.SENSITIVE_SECURITY
    assert FileClassifier.classify("certs/ca.pem") == FileCategory.SENSITIVE_SECURITY
    assert FileClassifier.classify("id_rsa") == FileCategory.SENSITIVE_SECURITY
    assert FileClassifier.classify(".aws/credentials") == FileCategory.SENSITIVE_SECURITY
    assert FileClassifier.classify("api_token_secret.txt") == FileCategory.SENSITIVE_SECURITY

    # Binary files
    assert FileClassifier.classify("logo.png") == FileCategory.BINARY_UNSUPPORTED
    assert FileClassifier.classify("archive.zip") == FileCategory.BINARY_UNSUPPORTED
    assert FileClassifier.classify("library.so") == FileCategory.BINARY_UNSUPPORTED
    assert FileClassifier.classify("package.whl") == FileCategory.BINARY_UNSUPPORTED

    # Test suites
    assert FileClassifier.classify("tests/test_api.py") == FileCategory.TEST_SUITE
    assert FileClassifier.classify("unit_tests/foo_test.py") == FileCategory.TEST_SUITE
    assert FileClassifier.classify("spec/test_worker.py") == FileCategory.TEST_SUITE

    # Python source
    assert FileClassifier.classify("app/main.py") == FileCategory.PYTHON_SOURCE
    assert FileClassifier.classify("types.pyi") == FileCategory.PYTHON_SOURCE

    # Configuration
    assert FileClassifier.classify("Dockerfile") == FileCategory.CONFIGURATION
    assert FileClassifier.classify("docker-compose.yml") == FileCategory.CONFIGURATION
    assert FileClassifier.classify("pyproject.toml") == FileCategory.CONFIGURATION
    assert FileClassifier.classify("requirements.txt") == FileCategory.CONFIGURATION
    assert FileClassifier.classify("config.yaml") == FileCategory.CONFIGURATION

    # Documentation
    assert FileClassifier.classify("README.md") == FileCategory.DOCUMENTATION
    assert FileClassifier.classify("LICENSE") == FileCategory.DOCUMENTATION
    assert FileClassifier.classify("docs/architecture.rst") == FileCategory.DOCUMENTATION


# --- T-28: Out-of-Order PR Webhook Events ---
@pytest.mark.asyncio
async def test_t28_out_of_order_pr_events():
    """T-28: Stale event with older github_updated_at is discarded without overwriting PR."""
    async with AsyncSessionLocal() as db:
        repo_id = 4001
        repo = Repository(
            github_repo_id=repo_id,
            full_name="test-org/repo-pr",
            is_active=True,
        )
        db.add(repo)
        await db.commit()

        # Newer event timestamp: 2026-11-01T20:00:00Z
        newer_time = "2026-11-01T20:00:00Z"
        payload_newer = {
            "action": "synchronize",
            "repository": {
                "id": repo_id,
                "name": "repo-pr",
                "full_name": "test-org/repo-pr",
                "private": False,
                "default_branch": "main",
            },
            "pull_request": {
                "number": 10,
                "title": "New Title",
                "state": "open",
                "head": {"sha": "headsha222", "ref": "feature"},
                "base": {"sha": "basesha222", "ref": "main"},
                "user": {"login": "dev1"},
                "updated_at": newer_time,
            },
        }

        pr1, run1 = await sync_pull_request(payload_newer, db)
        assert pr1.title == "New Title"
        assert pr1.head_sha == "headsha222"

        # Stale event timestamp: 2026-11-01T18:00:00Z (older)
        older_time = "2026-11-01T18:00:00Z"
        payload_older = {
            "action": "synchronize",
            "repository": {
                "id": repo_id,
                "name": "repo-pr",
                "full_name": "test-org/repo-pr",
                "private": False,
                "default_branch": "main",
            },
            "pull_request": {
                "number": 10,
                "title": "Stale Old Title",
                "state": "open",
                "head": {"sha": "headsha111", "ref": "feature"},
                "base": {"sha": "basesha111", "ref": "main"},
                "user": {"login": "dev1"},
                "updated_at": older_time,
            },
        }

        pr2, run2 = await sync_pull_request(payload_older, db)
        # Should retain newer values
        assert pr2.title == "New Title"
        assert pr2.head_sha == "headsha222"


# --- T-29 & T-30: Safe Run Number Allocation & Duplicate Active Run Prevention ---
@pytest.mark.asyncio
async def test_t29_t30_run_allocation_and_duplicate_prevention():
    """T-29: Safe incremental run number under row lock. T-30: Attaches to existing active run."""
    async with AsyncSessionLocal() as db:
        repo_id = 4002
        repo = Repository(
            github_repo_id=repo_id,
            full_name="test-org/repo-runs",
            is_active=True,
        )
        db.add(repo)
        await db.commit()

        base_payload = {
            "action": "opened",
            "repository": {
                "id": repo_id,
                "name": "repo-runs",
                "full_name": "test-org/repo-runs",
                "private": False,
                "default_branch": "main",
            },
            "pull_request": {
                "number": 25,
                "title": "Safe Runs PR",
                "state": "open",
                "head": {"sha": "sha_run_1", "ref": "feature"},
                "base": {"sha": "sha_base_1", "ref": "main"},
                "user": {"login": "dev2"},
                "updated_at": "2026-11-01T21:00:00Z",
            },
        }

        # First synchronization: creates AnalysisRun #1
        pr, run1 = await sync_pull_request(base_payload, db)
        assert run1 is not None
        assert run1.run_number == 1
        assert run1.status == "PENDING"

        # T-30: Same commit SHA received while run1 is PENDING: returns existing run1
        pr, run1_dup = await sync_pull_request(base_payload, db)
        assert run1_dup.id == run1.id
        assert run1_dup.run_number == 1

        # Complete run 1
        run1.status = "COMPLETED"
        await db.commit()

        # New push with different commit SHA: creates AnalysisRun #2 (T-29 safe increment)
        push_payload = dict(base_payload)
        push_payload["action"] = "synchronize"
        push_payload["pull_request"] = dict(base_payload["pull_request"])
        push_payload["pull_request"]["head"] = {"sha": "sha_run_2", "ref": "feature"}
        push_payload["pull_request"]["updated_at"] = "2026-11-01T21:05:00Z"

        pr, run2 = await sync_pull_request(push_payload, db)
        assert run2 is not None
        assert run2.run_number == 2
        assert run2.id != run1.id


# --- T-31: Truncated Unified Diffs ---
def test_t31_diff_parser_truncation_limits():
    """T-31: Diffs > 5 MB or > 5,000 lines are flagged with is_truncated=True."""
    # Test line limit
    huge_diff_lines = [
        "diff --git a/big.py b/big.py",
        "--- a/big.py",
        "+++ b/big.py",
        "@@ -1,1 +1,6000 @@",
    ]
    for i in range(5050):
        huge_diff_lines.append(f"+print({i})")

    diff_text = "\n".join(huge_diff_lines)
    parsed = DiffParser.parse(diff_text, max_lines=5000)

    assert parsed.is_truncated is True
    assert len(parsed.files) == 1
    assert parsed.files[0].is_truncated is True
    assert len(parsed.files[0].chunks[0].lines) == 5000


# --- T-32, T-33, T-34: Git Blob SHA Verification, SHA Binding, Oversized Exclusion ---
@pytest.mark.asyncio
async def test_t32_t33_t34_source_retriever_git_blob_verification():
    """T-32: Oversized file excluded. T-33: SHA binding. T-34: Git object hash verification."""
    mock_client = MagicMock()
    retriever = SourceRetriever(client=mock_client)

    # T-34: Verify git blob object hashing algorithm
    sample_content = b"def hello_world():\n    return 'Hello MergeMind!'\n"
    expected_hash = compute_git_blob_hash(sample_content)

    mock_client.get_blob = AsyncMock(
        return_value={
            "sha": expected_hash,
            "size": len(sample_content),
            "content": sample_content.decode("utf-8"),
            "encoding": "utf-8",
        }
    )

    file_result = await retriever.retrieve_file(
        repo_full_name="owner/repo",
        commit_sha="c0ffee1234567890abcdef",
        path="app/hello.py",
        expected_blob_sha=expected_hash,
        expected_size=len(sample_content),
    )

    assert file_result.status == RetrievalStatus.VERIFIED_COMPLETE
    assert file_result.blob_sha == expected_hash
    assert file_result.content == sample_content.decode("utf-8")
    assert file_result.category == FileCategory.PYTHON_SOURCE

    # T-32: Oversized file (> 5 MB)
    oversized_result = await retriever.retrieve_file(
        repo_full_name="owner/repo",
        commit_sha="c0ffee1234567890abcdef",
        path="data/huge_model.bin",
        expected_size=6 * 1024 * 1024,
    )
    assert oversized_result.status == RetrievalStatus.EXCLUDED_OVERSIZED


# --- T-35: Truncated Git Tree Response Fallback ---
@pytest.mark.asyncio
async def test_t35_truncated_git_tree_fallback():
    """T-35: Fallback to directory-level tree traversal when recursive tree is truncated."""
    mock_client = MagicMock()
    retriever = SourceRetriever(client=mock_client)

    # Step 1: Recursive tree returns truncated = True and lacks nested file
    mock_client.get_tree = AsyncMock()
    mock_client.get_tree.side_effect = [
        # Call 1: root directory listing
        {
            "truncated": False,
            "tree": [{"path": "nested", "sha": "sha_nested_tree", "type": "tree"}],
        },
        # Call 2: nested directory listing
        {
            "truncated": False,
            "tree": [{"path": "target.py", "sha": "sha_target_blob", "type": "blob", "size": 50}],
        },
    ]

    # Resolve "nested/target.py"
    entry = await retriever.resolve_file_tree_entry(
        repo_full_name="owner/repo",
        commit_sha="commit_sha_123",
        path="nested/target.py",
        cached_tree={"__truncated__": True, "root.py": {"sha": "sha_root"}},
    )

    assert entry is not None
    assert entry["sha"] == "sha_target_blob"
    assert entry["size"] == 50


# --- T-36: Source Content Hash Mismatch ---
@pytest.mark.asyncio
async def test_t36_source_content_hash_mismatch():
    """T-36: Tampered/corrupted byte stream rejected with HASH_MISMATCH."""
    mock_client = MagicMock()
    retriever = SourceRetriever(client=mock_client)

    correct_content = b"original content"
    tampered_content = b"tampered content"

    expected_sha = compute_git_blob_hash(correct_content)

    mock_client.get_blob = AsyncMock(
        return_value={
            "sha": expected_sha,
            "size": len(tampered_content),
            "content": tampered_content.decode("utf-8"),
            "encoding": "utf-8",
        }
    )

    result = await retriever.retrieve_file(
        repo_full_name="owner/repo",
        commit_sha="commit_sha_123",
        path="app/security.py",
        expected_blob_sha=expected_sha,
        expected_size=len(tampered_content),
    )

    assert result.status == RetrievalStatus.HASH_MISMATCH
    assert "Git blob hash mismatch" in result.error_message


# --- T-37: Incomplete Source Stream Detection ---
@pytest.mark.asyncio
async def test_t37_incomplete_source_stream_detection():
    """T-37: Byte length mismatch marked RETRIEVAL_INCOMPLETE."""
    mock_client = MagicMock()
    retriever = SourceRetriever(client=mock_client)

    partial_content = b"partial bytes"
    expected_size = 500  # Tree said 500 bytes, but transfer was aborted at 13 bytes

    mock_client.get_raw_content = AsyncMock(return_value=partial_content)

    result = await retriever.retrieve_file(
        repo_full_name="owner/repo",
        commit_sha="commit_sha_123",
        path="app/big_file.py",
        expected_blob_sha=None,
        expected_size=expected_size,
    )

    assert result.status == RetrievalStatus.RETRIEVAL_INCOMPLETE
    assert "Received 13 bytes, expected 500 bytes" in result.error_message
