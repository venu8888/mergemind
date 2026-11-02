"""Repository health assessment API endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.repository import Repository
from app.models.repository_health import RepositoryHealthAssessment
from app.schemas.repository_health import HealthAssessRequest, RepositoryHealthResponse
from app.services.health.service import RepositoryHealthService

router = APIRouter()
health_service = RepositoryHealthService()


@router.get("/{id}/health", response_model=RepositoryHealthResponse)
async def get_repository_health(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> RepositoryHealthAssessment:
    """Retrieve the latest health assessment snapshot for a repository."""
    # Verify repository exists
    repo_res = await db.execute(select(Repository).where(Repository.id == id))
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {id} not found",
        )

    assessment = await health_service.get_latest_assessment(repository_id=id, db=db)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health assessments found for repository {id}. Trigger an assessment first.",
        )
    return assessment


@router.post("/{id}/health/assess", response_model=RepositoryHealthResponse)
async def trigger_repository_health_assessment(
    id: str,
    payload: HealthAssessRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> RepositoryHealthAssessment:
    """Trigger an on-demand five-factor repository health assessment."""
    repo_res = await db.execute(select(Repository).where(Repository.id == id))
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {id} not found",
        )

    branch = payload.branch if payload and payload.branch else repo.default_branch
    commit_sha = (
        payload.commit_sha
        if payload and payload.commit_sha and payload.commit_sha != "0000000000000000000000000000000000000000"
        else None
    )

    if not commit_sha:
        try:
            from app.services.github.client import GitHubClient

            client = GitHubClient()
            ref_data = await client.get_branch_ref(repo.full_name, branch=branch)
            commit_sha = ref_data.get("object", {}).get("sha")
        except Exception as exc:
            logger.warning("Could not fetch remote commit SHA from GitHub for %s: %s", repo.full_name, exc)

        if not commit_sha:
            try:
                import subprocess

                res = subprocess.run(
                    ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
                )
                commit_sha = res.stdout.strip()
            except Exception:
                commit_sha = "fdf6b9551d3cadf1ef36c70a8c6188b9992105ef"

    # Use repository working tree or source directory
    source_dir = os.getcwd()

    assessment = await health_service.assess_repository(
        repository_id=id,
        source_dir=source_dir,
        commit_sha=commit_sha,
        branch_name=branch,
        db=db,
    )
    return assessment
