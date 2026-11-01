"""Repository, Pull Request, and Installation Management Endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_api_key
from app.models.installation import Installation
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.schemas.installation import InstallationRead
from app.schemas.pull_request import PullRequestRead
from app.schemas.repository import RepositoryRead

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[RepositoryRead],
    summary="List Tracked Repositories",
    dependencies=[Depends(verify_api_key)],
)
async def list_repositories(
    is_active: bool | None = Query(default=None),
    installation_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[Repository]:
    """Retrieves all tracked repositories with optional filtering."""
    stmt = select(Repository).order_by(Repository.full_name.asc())
    if is_active is not None:
        stmt = stmt.where(Repository.is_active == is_active)
    if installation_id is not None:
        stmt = stmt.where(Repository.installation_id == installation_id)

    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get(
    "/{repo_id}/pulls",
    response_model=list[PullRequestRead],
    summary="List Pull Requests for Repository",
    dependencies=[Depends(verify_api_key)],
)
async def list_repository_pull_requests(
    repo_id: str,
    state: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[PullRequest]:
    """Retrieves pull requests tracked for the specified repository."""
    # Verify repository exists
    repo_stmt = select(Repository).where(Repository.id == repo_id)
    repo_res = await db.execute(repo_stmt)
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found",
        )

    stmt = (
        select(PullRequest)
        .where(PullRequest.repository_id == repo_id)
        .order_by(PullRequest.pr_number.desc())
    )
    if state:
        stmt = stmt.where(PullRequest.state == state)

    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get(
    "/installations/all",
    response_model=list[InstallationRead],
    summary="List Tracked Installations",
    dependencies=[Depends(verify_api_key)],
)
async def list_installations(
    db: AsyncSession = Depends(get_db),
) -> list[Installation]:
    """Retrieves all recorded GitHub App installations."""
    stmt = select(Installation).order_by(Installation.account_login.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())
