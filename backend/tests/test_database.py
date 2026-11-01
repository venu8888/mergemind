"""Tests for database connectivity and ORM models."""

import pytest

from app.core.database import AsyncSessionLocal, check_db_connection
from app.models.analysis_run import AnalysisRun
from app.models.pull_request import PullRequest
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_database_connection():
    assert await check_db_connection() is True


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
