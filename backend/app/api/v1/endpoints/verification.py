"""PR Verification API Endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.analysis_run import AnalysisRun
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.schemas.verification import (
    CheckSummaryResponse,
    FindingResponse,
    PRVerificationResponse,
    VerifyPRRequest,
)
from app.services.verification.verifier import PRVerificationService

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_verification_response(run: AnalysisRun) -> PRVerificationResponse:
    checks: list[CheckSummaryResponse] = []
    if run.delta_summary and isinstance(run.delta_summary.get("checks"), list):
        for c in run.delta_summary["checks"]:
            checks.append(
                CheckSummaryResponse(
                    check_type=c.get("check_type", "UNKNOWN"),
                    status=c.get("status", "UNKNOWN"),
                    duration_ms=c.get("duration_ms", 0),
                    message=c.get("message"),
                    output_digest=c.get("output_digest"),
                )
            )

    findings: list[FindingResponse] = [FindingResponse.model_validate(f) for f in run.findings]

    return PRVerificationResponse(
        analysis_run_id=run.id,
        pull_request_id=run.pull_request_id,
        commit_sha=run.commit_sha,
        run_number=run.run_number,
        status=run.status,
        verification_completeness=run.verification_completeness,
        quality_score=run.quality_score,
        gate_verdict=run.gate_verdict,
        delta_summary=run.delta_summary,
        checks=checks,
        findings=findings,
        created_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get(
    "/{id}/pulls/{number}/verification",
    response_model=PRVerificationResponse,
    summary="Get latest PR verification assessment",
)
async def get_pr_verification(
    id: str,
    number: int,
    db: AsyncSession = Depends(get_db),
) -> PRVerificationResponse:
    """Retrieve the latest verification assessment and gate verdict for a pull request."""
    # Verify repository ownership
    repo = (await db.execute(select(Repository).where(Repository.id == id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {id} not found",
        )

    # Find PR
    pr_stmt = select(PullRequest).where(
        PullRequest.repository_id == id, PullRequest.pr_number == number
    )
    pr = (await db.execute(pr_stmt)).scalar_one_or_none()
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pull request #{number} not found for repository {id}",
        )

    run_stmt = (
        select(AnalysisRun)
        .options(selectinload(AnalysisRun.findings))
        .where(AnalysisRun.pull_request_id == pr.id)
        .order_by(AnalysisRun.started_at.desc(), AnalysisRun.run_number.desc())
        .limit(1)
    )
    run = (await db.execute(run_stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verification run found for PR #{number}",
        )

    return _build_verification_response(run)


@router.post(
    "/{id}/pulls/{number}/verify",
    response_model=PRVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute on-demand PR verification",
)
async def trigger_pr_verification(
    id: str,
    number: int,
    payload: VerifyPRRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> PRVerificationResponse:
    """Trigger a complete verification pipeline for a PR commit."""
    # Verify repository ownership
    repo = (await db.execute(select(Repository).where(Repository.id == id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {id} not found",
        )

    service = PRVerificationService()
    target_sha = payload.commit_sha if payload else None

    try:
        run = await service.verify_pull_request(
            repository_id=id,
            pr_number=number,
            commit_sha=target_sha,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return _build_verification_response(run)
