"""Tests for GitHub Lifecycle, Optimistic Repository Reconciliation & Client Rate Limiting (T-19 to T-27)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.installation import Installation
from app.models.repository import Repository
from app.services.github.client import GitHubClient
from app.services.github.exceptions import (
    GitHubAPIError,
    GitHubPermissionError,
    GitHubRateLimitError,
)
from app.services.github.lifecycle import (
    handle_installation_event,
    reconcile_installation_repositories,
)


@pytest.fixture
def mock_token_manager():
    mgr = MagicMock()
    mgr.get_token = AsyncMock(return_value="ghs_mock_token_123")
    return mgr


# --- T-19: Installation Suspension & Deletion ---
@pytest.mark.asyncio
async def test_t19_installation_suspension_and_deletion():
    """T-19: installation.deleted and installation.suspend update state and deactivate repos."""
    async with AsyncSessionLocal() as db:
        install_id = 9001
        inst = Installation(
            github_installation_id=install_id,
            account_login="org-alpha",
            account_type="Organization",
            state="ACTIVE",
            sync_version=1,
        )
        db.add(inst)
        await db.flush()

        repo = Repository(
            github_repo_id=1001,
            name="repo-alpha",
            full_name="org-alpha/repo-alpha",
            is_active=True,
            installation_id=inst.id,
        )
        db.add(repo)
        await db.commit()

        # Suspend event
        suspend_payload = {
            "action": "suspend",
            "installation": {
                "id": install_id,
                "account": {"login": "org-alpha", "type": "Organization"},
            },
        }
        res_suspend = await handle_installation_event(suspend_payload, db)
        assert res_suspend.state == "SUSPENDED"

        # Check repository was deactivated
        repo_db = (
            await db.execute(select(Repository).where(Repository.id == repo.id))
        ).scalar_one()
        assert repo_db.is_active is False

        # Delete event
        delete_payload = {
            "action": "deleted",
            "installation": {
                "id": install_id,
                "account": {"login": "org-alpha", "type": "Organization"},
            },
        }
        res_delete = await handle_installation_event(delete_payload, db)
        assert res_delete.state == "DELETED"


# --- T-20 & T-21: Authoritative Sync & Transient API Failure ---
@pytest.mark.asyncio
async def test_t20_t21_reconciliation_authoritative_and_transient_failure(mock_token_manager):
    """T-20: Authoritative sync reconciles added/removed repos. T-21: Transient API failure raises error for worker retry."""
    async with AsyncSessionLocal() as db:
        install_id = 9002
        inst = Installation(
            github_installation_id=install_id,
            account_login="org-beta",
            account_type="Organization",
            state="ACTIVE",
            sync_version=1,
        )
        db.add(inst)
        await db.flush()

        # Existing active repo
        r1 = Repository(
            github_repo_id=2001,
            name="repo-keep",
            full_name="org-beta/repo-keep",
            is_active=True,
            installation_id=inst.id,
        )
        # Existing repo to be removed
        r2 = Repository(
            github_repo_id=2002,
            name="repo-remove",
            full_name="org-beta/repo-remove",
            is_active=True,
            installation_id=inst.id,
        )
        db.add_all([r1, r2])
        await db.commit()

        client = GitHubClient(token_manager=mock_token_manager)

        # Mock API response returning repo-keep and a newly added repo-new
        api_repos = [
            {
                "id": 2001,
                "name": "repo-keep",
                "full_name": "org-beta/repo-keep",
                "private": False,
                "default_branch": "main",
            },
            {
                "id": 2003,
                "name": "repo-new",
                "full_name": "org-beta/repo-new",
                "private": True,
                "default_branch": "develop",
            },
        ]

        with patch.object(
            client, "get_installation_repositories", new_callable=AsyncMock
        ) as mock_get_repos:
            mock_get_repos.return_value = api_repos

            # T-20: Reconcile
            active_count = await reconcile_installation_repositories(install_id, client, db)
            assert active_count == 2

            # Verify r2 was deactivated and r3 was created
            r2_check = (
                await db.execute(select(Repository).where(Repository.github_repo_id == 2002))
            ).scalar_one()
            assert r2_check.is_active is False

            r3_check = (
                await db.execute(select(Repository).where(Repository.github_repo_id == 2003))
            ).scalar_one()
            assert r3_check.is_active is True
            assert r3_check.default_branch == "develop"

        # T-21: Transient failure during API call raises error without deactivating repos
        with patch.object(
            client,
            "get_installation_repositories",
            side_effect=GitHubAPIError(503, "Service Unavailable"),
        ):
            with pytest.raises(GitHubAPIError):
                await reconcile_installation_repositories(install_id, client, db)

            # Check that existing repositories are still intact
            r1_check = (
                await db.execute(select(Repository).where(Repository.github_repo_id == 2001))
            ).scalar_one()
            assert r1_check.is_active is True


# --- T-22 & T-23: Mid-Sync Suspension & Stale Sync Version Rejection ---
@pytest.mark.asyncio
async def test_t22_t23_mid_sync_suspension_and_version_rejection(mock_token_manager):
    """T-22: Aborts if suspended during API call. T-23: Aborts if sync_version changed during API call."""
    async with AsyncSessionLocal() as db:
        install_id = 9003
        inst = Installation(
            github_installation_id=install_id,
            account_login="org-gamma",
            account_type="Organization",
            state="ACTIVE",
            sync_version=10,
        )
        db.add(inst)
        await db.commit()

        client = GitHubClient(token_manager=mock_token_manager)

        # T-22: Simulate suspension during API call
        async def fake_get_repos_suspended(*args, **kwargs):
            # Mid-sync DB modification: installation gets suspended
            async with AsyncSessionLocal() as inner_db:
                await inner_db.execute(
                    update(Installation)
                    .where(Installation.github_installation_id == install_id)
                    .values(state="SUSPENDED")
                )
                await inner_db.commit()
            return [
                {
                    "id": 3001,
                    "name": "repo",
                    "full_name": "org-gamma/repo",
                    "private": False,
                    "default_branch": "main",
                }
            ]

        with patch.object(
            client, "get_installation_repositories", side_effect=fake_get_repos_suspended
        ):
            aborted_count = await reconcile_installation_repositories(install_id, client, db)
            assert aborted_count == 0

        # Reset state to ACTIVE, sync_version = 20
        await db.execute(
            update(Installation)
            .where(Installation.github_installation_id == install_id)
            .values(state="ACTIVE", sync_version=20)
        )
        await db.commit()

        # T-23: Simulate sync_version increment during API call
        async def fake_get_repos_version_bump(*args, **kwargs):
            async with AsyncSessionLocal() as inner_db:
                await inner_db.execute(
                    update(Installation)
                    .where(Installation.github_installation_id == install_id)
                    .values(sync_version=21)
                )
                await inner_db.commit()
            return [
                {
                    "id": 3001,
                    "name": "repo",
                    "full_name": "org-gamma/repo",
                    "private": False,
                    "default_branch": "main",
                }
            ]

        with patch.object(
            client, "get_installation_repositories", side_effect=fake_get_repos_version_bump
        ):
            aborted_count2 = await reconcile_installation_repositories(install_id, client, db)
            assert aborted_count2 == 0


# --- T-24: API Timeout Recovery ---
@pytest.mark.asyncio
async def test_t24_api_timeout_recovery(mock_token_manager):
    """T-24: Client handles timeout cleanly and bubbles up for queue worker retry."""
    client = GitHubClient(token_manager=mock_token_manager, timeout=0.1)

    with patch("httpx.AsyncClient.request", side_effect=TimeoutError("Request timed out")):
        with pytest.raises(GitHubAPIError) as exc_info:
            await client.request("GET", "/test-endpoint", installation_id=123)
        assert exc_info.value.status_code == 408
        assert "timed out" in exc_info.value.message.lower()


# --- T-25: Missing GitHub Permissions (HTTP 403) ---
@pytest.mark.asyncio
async def test_t25_missing_permissions_403(mock_token_manager):
    """T-25: HTTP 403 with permission error raises GitHubPermissionError."""
    client = GitHubClient(token_manager=mock_token_manager)

    resp = MagicMock()
    resp.status_code = 403
    resp.headers = {}
    resp.text = '{"message": "Resource not accessible by integration"}'
    resp.json.return_value = {"message": "Resource not accessible by integration"}

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = resp
        with pytest.raises(GitHubPermissionError):
            await client.request("GET", "/repos/owner/repo/pulls", installation_id=123)


# --- T-26: Primary Rate Limit Exhaustion ---
@pytest.mark.asyncio
async def test_t26_primary_rate_limit_exhaustion(mock_token_manager):
    """T-26: Parses x-ratelimit-reset, updates state, raises GitHubRateLimitError."""
    client = GitHubClient(token_manager=mock_token_manager)

    reset_time = int(datetime.now(UTC).timestamp()) + 300
    resp = MagicMock()
    resp.status_code = 403
    resp.headers = {
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": str(reset_time),
    }
    resp.text = '{"message": "API rate limit exceeded"}'
    resp.json.return_value = {"message": "API rate limit exceeded"}

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = resp
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client.request("GET", "/rate-limited", installation_id=123)
        assert exc_info.value.status_code == 403
        assert client.rate_limit_remaining == 0
        assert client.rate_limit_reset == reset_time


# --- T-27: Secondary Rate Limit (Retry-After) ---
@pytest.mark.asyncio
async def test_t27_secondary_rate_limit_retry_after(mock_token_manager):
    """T-27: Parses Retry-After header and raises GitHubRateLimitError with retry_after."""
    client = GitHubClient(token_manager=mock_token_manager, max_retries=2)

    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {"Retry-After": "2"}
    resp.text = '{"message": "You have exceeded a secondary rate limit"}'
    resp.json.return_value = {"message": "You have exceeded a secondary rate limit"}

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = resp
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(GitHubRateLimitError) as exc_info:
                await client.request("GET", "/secondary-limit", installation_id=123)
            assert exc_info.value.retry_after == 2
            assert mock_sleep.call_count >= 1
