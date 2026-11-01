"""API endpoints for CI/CD failure intelligence and root-cause inspection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.repository import Repository
from app.schemas.ci_failure import CIFailureIngestRequest, CIFailureResponse
from app.services.ci_intelligence.service import CIFailureService

router = APIRouter()


@router.get(
    "/repositories/{id}/ci-failures",
    response_model=list[CIFailureResponse],
    summary="List CI Failures",
    description="Retrieve recent ingested CI/CD workflow and job failures for a repository.",
)
async def list_ci_failures(
    id: str,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[CIFailureResponse]:
    """Retrieve CI failures for a repository."""
    repo = (await db.execute(select(Repository).where(Repository.id == id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {id} not found"
        )

    service = CIFailureService()
    return await service.get_failures_for_repository(db, id, status=status_filter, limit=limit)


@router.get(
    "/repositories/{id}/ci-failures/{failure_id}",
    response_model=CIFailureResponse,
    summary="Get CI Failure Details",
    description="Retrieve root-cause localization, error logs, and advisory hypotheses for a failure.",
)
async def get_ci_failure_detail(
    id: str,
    failure_id: str,
    db: AsyncSession = Depends(get_db),
) -> CIFailureResponse:
    """Retrieve detailed failure report with localized files and advisory hypothesis."""
    repo = (await db.execute(select(Repository).where(Repository.id == id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {id} not found"
        )

    service = CIFailureService()
    failure = await service.get_failure_by_id(db, failure_id)
    if not failure or failure.repository_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"CI failure {failure_id} not found"
        )

    return failure


class CIFailureDirectIngestRequest(CIFailureIngestRequest):
    repository_id: str


@router.post(
    "/ci-failures/ingest",
    response_model=CIFailureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest CI Failure Directly",
    description="Ingest and analyze raw logs with repository_id provided in body.",
)
async def ingest_ci_failure_direct(
    payload: CIFailureDirectIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> CIFailureResponse:
    """Ingest, sanitize, classify, and localize a CI failure."""
    service = CIFailureService()
    try:
        return await service.ingest_failure(
            db=db,
            repository_id=payload.repository_id,
            workflow_run_id=payload.workflow_run_id,
            workflow_name=payload.workflow_name,
            job_name=payload.job_name,
            commit_sha=payload.commit_sha,
            branch=payload.branch,
            raw_logs=payload.raw_logs,
            pull_request_id=payload.pull_request_id,
            changed_files=payload.changed_files,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/repositories/{id}/ci-failures/ingest",
    response_model=CIFailureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest CI Failure",
    description="Ingest and analyze raw logs from a failed workflow or test run.",
)
async def ingest_ci_failure(
    id: str,
    payload: CIFailureIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> CIFailureResponse:
    """Ingest, sanitize, classify, and localize a CI failure."""
    service = CIFailureService()
    try:
        return await service.ingest_failure(
            db=db,
            repository_id=id,
            workflow_run_id=payload.workflow_run_id,
            workflow_name=payload.workflow_name,
            job_name=payload.job_name,
            commit_sha=payload.commit_sha,
            branch=payload.branch,
            raw_logs=payload.raw_logs,
            pull_request_id=payload.pull_request_id,
            changed_files=payload.changed_files,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
