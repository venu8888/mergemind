"""Authoritative Pull Request Metadata Synchronization and Safe Run Number Generation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_run import AnalysisRun
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.services.github.client import GitHubClient

logger = logging.getLogger(__name__)


def _is_sqlite(db: AsyncSession) -> bool:
    bind = db.bind
    return bind is not None and hasattr(bind, "dialect") and bind.dialect.name == "sqlite"


def parse_github_timestamp(ts_str: str | None) -> datetime:
    """Parses ISO-8601 GitHub timestamp to timezone-aware UTC datetime."""
    if not ts_str:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)


async def sync_pull_request(
    arg1: Any,
    arg2: Any,
    arg3: Any = None,
    client: GitHubClient | None = None,
) -> tuple[PullRequest | None, AnalysisRun | None]:
    """Synchronizes pull request metadata against authoritative GitHub state under row lock.

    Supports signatures:
    - sync_pull_request(payload: dict, db: AsyncSession, client: GitHubClient | None = None)
    - sync_pull_request(db: AsyncSession, repo: Repository, payload: dict, client: GitHubClient | None = None)
    """
    if isinstance(arg1, dict):
        payload = arg1
        db: AsyncSession = arg2
        repo: Repository | None = None
        if arg3 is not None and isinstance(arg3, GitHubClient):
            client = arg3
    elif isinstance(arg1, AsyncSession):
        db: AsyncSession = arg1
        repo = arg2
        payload = arg3
    else:
        payload = arg1
        db = arg2

    pr_data = payload.get("pull_request", {})
    pr_number = pr_data.get("number")
    if not pr_number:
        logger.warning("PR payload missing pull_request.number")
        return None, None

    incoming_updated_at = parse_github_timestamp(pr_data.get("updated_at"))
    repo_data = payload.get("repository", {})
    repo_github_id = repo_data.get("id")

    # If repo is not passed, resolve from DB or create
    if repo is None and repo_github_id:
        repo_stmt = select(Repository).where(Repository.github_repo_id == repo_github_id)
        repo_res = await db.execute(repo_stmt)
        repo = repo_res.scalar_one_or_none()
        if repo is None:
            repo = Repository(
                github_repo_id=repo_github_id,
                full_name=repo_data.get("full_name", "unknown/unknown"),
                is_active=True,
            )
            db.add(repo)
            await db.flush()

    if repo is None:
        logger.error(f"Cannot sync PR #{pr_number}: repository not found")
        return None, None

    # Step 1: Row-lock the PullRequest record to prevent concurrent updates
    pr_stmt = select(PullRequest).where(
        PullRequest.repository_id == repo.id,
        PullRequest.pr_number == pr_number,
    )
    if not _is_sqlite(db):
        pr_stmt = pr_stmt.with_for_update()

    pr_res = await db.execute(pr_stmt)
    pull_request = pr_res.scalar_one_or_none()

    # Step 2: Out-of-order rejection
    if pull_request is not None and pull_request.github_updated_at:
        pr_time = pull_request.github_updated_at
        if pr_time.tzinfo is None:
            pr_time = pr_time.replace(tzinfo=UTC)
        if incoming_updated_at < pr_time:
            logger.info(
                f"Discarding stale webhook event for PR #{pr_number} "
                f"(incoming {incoming_updated_at} < current {pr_time})"
            )
            return pull_request, None

    # Step 3: Fetch authoritative head_sha from GitHub API if client provided, else use payload
    raw_head = pr_data.get("head", {})
    canonical_head_sha = raw_head.get("sha", "")
    canonical_base_sha = pr_data.get("base", {}).get("sha", "")
    author_login = pr_data.get("user", {}).get("login", "unknown")
    title = pr_data.get("title", "")
    state = pr_data.get("state", "open")

    if client:
        try:
            authoritative_data = await client.get_pull_request(
                owner=repo.full_name,
                pull_number=pr_number,
            )
            canonical_head_sha = authoritative_data.get("head", {}).get("sha", canonical_head_sha)
            canonical_base_sha = authoritative_data.get("base", {}).get("sha", canonical_base_sha)
            title = authoritative_data.get("title", title)
            state = authoritative_data.get("state", state)
            author_login = authoritative_data.get("user", {}).get("login", author_login)
        except Exception as exc:
            logger.warning(
                f"Failed to fetch live authoritative PR #{pr_number} metadata: {exc}. Using webhook payload."
            )

    now = datetime.now(UTC)

    # Step 4: Upsert PullRequest
    if pull_request is None:
        pull_request = PullRequest(
            repository_id=repo.id,
            github_pr_id=pr_data.get("id", 0),
            pr_number=pr_number,
            title=title,
            state=state,
            head_sha=canonical_head_sha,
            base_sha=canonical_base_sha,
            author=author_login,
            github_created_at=parse_github_timestamp(pr_data.get("created_at")),
            github_updated_at=incoming_updated_at,
        )
        db.add(pull_request)
        await db.flush()
    else:
        pull_request.title = title
        pull_request.state = state
        pull_request.head_sha = canonical_head_sha
        pull_request.base_sha = canonical_base_sha
        pull_request.author = author_login
        pull_request.github_updated_at = incoming_updated_at
        pull_request.updated_at = now
        await db.flush()

    # Step 5: Duplicate Active Run Prevention
    # Check if there is already an active run for the same commit
    active_run_stmt = select(AnalysisRun).where(
        AnalysisRun.pull_request_id == pull_request.id,
        AnalysisRun.commit_sha == canonical_head_sha,
        AnalysisRun.status.in_(["PENDING", "RUNNING"]),
    )
    active_run_res = await db.execute(active_run_stmt)
    existing_active_run = active_run_res.scalar_one_or_none()
    if existing_active_run:
        logger.info(
            f"Active run #{existing_active_run.run_number} already exists for PR #{pr_number} "
            f"at commit {canonical_head_sha[:8]}. Attaching without allocating duplicate."
        )
        await db.commit()
        return pull_request, existing_active_run

    # Step 6: Safe Run-Number Allocation
    # Calculate next run_number safely serialized under the PR row lock
    max_run_stmt = select(func.coalesce(func.max(AnalysisRun.run_number), 0)).where(
        AnalysisRun.pull_request_id == pull_request.id
    )
    max_res = await db.execute(max_run_stmt)
    next_run_number = max_res.scalar() + 1

    analysis_run = AnalysisRun(
        pull_request_id=pull_request.id,
        commit_sha=canonical_head_sha,
        run_number=next_run_number,
        status="PENDING",
        runner_type="CONTAINER",
    )
    db.add(analysis_run)
    await db.commit()
    await db.refresh(pull_request)
    await db.refresh(analysis_run)

    logger.info(
        f"Scheduled AnalysisRun #{analysis_run.run_number} for PR #{pr_number} "
        f"at {canonical_head_sha[:8]} (Run ID: {analysis_run.id})"
    )
    return pull_request, analysis_run
