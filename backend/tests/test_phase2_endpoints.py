"""Tests for Webhook Ingress Endpoints, Repository API Endpoints & Dispatcher."""

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.installation import Installation
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.webhook_delivery import WebhookDelivery
from app.services.github.dispatcher import WebhookDispatcher
from app.services.github.queue_worker import WebhookQueueWorker
from app.services.github.webhook import persist_webhook_delivery


def compute_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.mark.asyncio
async def test_webhook_endpoint_valid_and_duplicate():
    """POST /api/v1/webhooks/github returns 202 for new delivery, 200 for duplicate, 401 for bad signature."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        secret = settings.GITHUB_WEBHOOK_SECRET
        delivery_id = str(uuid.uuid4())
        payload = json.dumps({"action": "opened", "pull_request": {"number": 100}}).encode("utf-8")
        signature = compute_signature(secret, payload)

        headers = {
            "X-GitHub-Delivery": delivery_id,
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json",
        }

        # 1. Valid first submission -> 202 Accepted
        r1 = await client.post("/api/v1/webhooks/github", content=payload, headers=headers)
        assert r1.status_code == 202
        assert r1.json()["status"] == "accepted"

        # 2. Duplicate submission -> 200 OK
        r2 = await client.post("/api/v1/webhooks/github", content=payload, headers=headers)
        assert r2.status_code == 200
        assert r2.json()["status"] == "already_processed"

        # 3. Bad signature -> 401 Unauthorized
        bad_headers = dict(headers)
        bad_headers["X-GitHub-Delivery"] = str(uuid.uuid4())
        bad_headers["X-Hub-Signature-256"] = "sha256=invalidhash"
        r3 = await client.post("/api/v1/webhooks/github", content=payload, headers=bad_headers)
        assert r3.status_code == 401


@pytest.mark.asyncio
async def test_repository_endpoints_and_api_key():
    """Verifies GET /api/v1/repositories, /pulls, /installations/all with API key auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Seed test data
        async with AsyncSessionLocal() as db:
            inst = Installation(
                github_installation_id=88001,
                account_login="repo-test-org",
                account_type="Organization",
                state="ACTIVE",
            )
            db.add(inst)
            await db.flush()

            repo = Repository(
                github_repo_id=77001,
                name="test-repo",
                full_name="repo-test-org/test-repo",
                is_active=True,
                installation_id=inst.id,
            )
            db.add(repo)
            await db.flush()

            pr = PullRequest(
                repository_id=repo.id,
                github_pr_id=66001,
                pr_number=5,
                title="Test PR 5",
                state="open",
                head_sha="head555",
                base_sha="base555",
                author="alice",
            )
            db.add(pr)
            await db.commit()
            repo_id = repo.id

        auth_headers = {"X-API-Key": settings.API_KEY}

        # 1. Unauthorized request
        r_unauth = await client.get("/api/v1/repositories")
        assert r_unauth.status_code == 401

        # 2. List repositories
        r_repos = await client.get("/api/v1/repositories", headers=auth_headers)
        assert r_repos.status_code == 200
        data = r_repos.json()
        assert len(data) >= 1
        assert any("test-repo" in item["full_name"] for item in data)

        # 2b. List repositories with filter
        r_filtered = await client.get(
            f"/api/v1/repositories?is_active=true&installation_id={inst.id}", headers=auth_headers
        )
        assert r_filtered.status_code == 200
        assert len(r_filtered.json()) >= 1

        # 3. List PRs for repository
        r_pulls = await client.get(f"/api/v1/repositories/{repo_id}/pulls", headers=auth_headers)
        assert r_pulls.status_code == 200
        pulls = r_pulls.json()
        assert len(pulls) >= 1
        assert pulls[0]["pr_number"] == 5

        # 4. List installations
        r_inst = await client.get("/api/v1/repositories/installations/all", headers=auth_headers)
        assert r_inst.status_code == 200
        insts = r_inst.json()
        assert len(insts) >= 1
        assert any(i["account_login"] == "repo-test-org" for i in insts)


@pytest.mark.asyncio
async def test_webhook_dispatcher_process_one():
    """Verifies that WebhookDispatcher claims, processes, and completes a queued job."""
    async with AsyncSessionLocal() as db:
        # Create a queued installation event
        payload = {
            "action": "created",
            "installation": {
                "id": 991122,
                "account": {"login": "dispatcher-org", "type": "Organization"},
                "permissions": {"pull_requests": "read"},
            },
        }
        delivery = await persist_webhook_delivery(
            delivery_id=f"dispatch-test-{uuid.uuid4().hex[:8]}",
            event_type="installation",
            action="created",
            payload=payload,
            db=db,
        )

        worker = WebhookQueueWorker(worker_id="dispatcher-test-worker")
        dispatcher = WebhookDispatcher(worker=worker)

        # Process the job
        processed = await dispatcher.process_one(db)
        assert processed is True

        # Verify job was marked COMPLETED
        from sqlalchemy import select

        deliv_check = (
            await db.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery.id))
        ).scalar_one()
        assert deliv_check.processing_status == "COMPLETED"
        assert deliv_check.locked_at is None
        assert deliv_check.lease_token is None

        # Verify Installation record was created in database
        inst_check = (
            await db.execute(
                select(Installation).where(Installation.github_installation_id == 991122)
            )
        ).scalar_one_or_none()
        assert inst_check is not None
        assert inst_check.account_login == "dispatcher-org"
        assert inst_check.state == "ACTIVE"
