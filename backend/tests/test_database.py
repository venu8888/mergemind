"""Tests for database connectivity and ORM models."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal, check_db_connection
from app.models.analysis_run import AnalysisRun
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.webhook_delivery import WebhookDelivery


@pytest.mark.asyncio
async def test_database_connection():
    assert await check_db_connection() is True


@pytest.mark.asyncio
async def test_database_connection_failure(monkeypatch):
    from unittest.mock import MagicMock

    from app.core import database

    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Simulated DB Connection Timeout")
    monkeypatch.setattr(database, "engine", mock_engine)

    assert await check_db_connection() is False


@pytest.mark.asyncio
async def test_repository_and_pr_relationship():
    async with AsyncSessionLocal() as session:
        repo = Repository(
            github_repo_id=12345,
            full_name="mergemind-org/test-repo",
            default_branch="main",
            is_active=True,
            settings_override={},
        )
        session.add(repo)
        await session.commit()
        await session.refresh(repo)

        pr = PullRequest(
            repository_id=repo.id,
            pr_number=101,
            title="feat: add authentication check",
            state="open",
            author_username="developer1",
            base_branch="main",
            head_branch="feature/auth",
            current_head_sha="0123456789abcdef0123456789abcdef01234567",
        )
        session.add(pr)
        await session.commit()
        await session.refresh(pr)

        run = AnalysisRun(
            pull_request_id=pr.id,
            commit_sha=pr.current_head_sha,
            run_number=1,
            status="PENDING",
            runner_type="CONTAINER",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        assert repo.id is not None
        assert pr.repository_id == repo.id
        assert run.pull_request_id == pr.id
        assert run.commit_sha == "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.asyncio
async def test_pr_number_unique_per_repository():
    """Validates that duplicate PR numbers within the same repository violate UniqueConstraint."""
    async with AsyncSessionLocal() as session:
        repo = Repository(
            github_repo_id=99991,
            full_name="mergemind-org/unique-test",
            default_branch="main",
            is_active=True,
            settings_override={},
        )
        session.add(repo)
        await session.commit()

        pr1 = PullRequest(
            repository_id=repo.id,
            pr_number=42,
            title="PR 42 first entry",
            state="open",
            author_username="devA",
            base_branch="main",
            head_branch="patch-1",
            current_head_sha="a" * 40,
        )
        session.add(pr1)
        await session.commit()

        pr2 = PullRequest(
            repository_id=repo.id,
            pr_number=42,  # Duplicate PR number
            title="PR 42 duplicate entry",
            state="open",
            author_username="devB",
            base_branch="main",
            head_branch="patch-2",
            current_head_sha="b" * 40,
        )
        session.add(pr2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_analysis_run_unique_composite_constraint():
    """Validates that (pull_request_id, commit_sha, run_number) enforces idempotency."""
    async with AsyncSessionLocal() as session:
        repo = Repository(
            github_repo_id=99992,
            full_name="mergemind-org/run-unique-test",
            default_branch="main",
            is_active=True,
            settings_override={},
        )
        session.add(repo)
        await session.commit()

        pr = PullRequest(
            repository_id=repo.id,
            pr_number=10,
            title="PR 10",
            state="open",
            author_username="devA",
            base_branch="main",
            head_branch="patch-1",
            current_head_sha="c" * 40,
        )
        session.add(pr)
        await session.commit()

        run1 = AnalysisRun(
            pull_request_id=pr.id,
            commit_sha="c" * 40,
            run_number=1,
            status="PENDING",
            runner_type="CONTAINER",
        )
        session.add(run1)
        await session.commit()

        run2 = AnalysisRun(
            pull_request_id=pr.id,
            commit_sha="c" * 40,
            run_number=1,  # Duplicate composite key
            status="RUNNING",
            runner_type="CONTAINER",
        )
        session.add(run2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_webhook_delivery_deduplication_constraint():
    """Validates that webhook delivery_id enforces atomic deduplication."""
    async with AsyncSessionLocal() as session:
        delivery1 = WebhookDelivery(
            delivery_id="delivery-guid-12345",
            event_type="pull_request",
            action="opened",
            payload_summary={"action": "opened"},
            status="RECEIVED",
        )
        session.add(delivery1)
        await session.commit()

        delivery2 = WebhookDelivery(
            delivery_id="delivery-guid-12345",  # Duplicate delivery_id
            event_type="pull_request",
            action="opened",
            payload_summary={"action": "opened"},
            status="RECEIVED",
        )
        session.add(delivery2)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
