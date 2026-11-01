"""API endpoints for AI remediation proposals, patch verification, and draft PR generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.repository import Repository
from app.schemas.remediation import (
    CreateCorrectivePRRequest,
    PatchVerificationResponse,
    ProposeRemediationRequest,
    RemediationProposalResponse,
    RemediationPullRequestResponse,
    VerifyPatchRequest,
)
from app.services.remediation.patch_verifier import PatchVerifier
from app.services.remediation.pr_manager import RemediationPRManager
from app.services.remediation.service import RemediationService

router = APIRouter()


@router.post(
    "/remediations/propose",
    response_model=RemediationProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propose AI Remediation",
    description="Generate a reviewable corrective patch diff addressing a CI failure or finding.",
)
async def propose_remediation(
    payload: ProposeRemediationRequest,
    db: AsyncSession = Depends(get_db),
) -> RemediationProposalResponse:
    """Generate and store an AI-assisted or deterministic remediation proposal."""
    service = RemediationService()
    try:
        if payload.ci_failure_id:
            return await service.propose_for_ci_failure(db, payload.ci_failure_id)
        elif payload.finding_id:
            return await service.propose_for_finding(db, payload.finding_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify either ci_failure_id or finding_id",
            )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/remediations/{id}",
    response_model=RemediationProposalResponse,
    summary="Get Remediation Proposal",
    description="Retrieve proposal details, patch diff, and verification history.",
)
async def get_remediation(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> RemediationProposalResponse:
    """Retrieve proposal by ID."""
    service = RemediationService()
    proposal = await service.get_proposal_by_id(db, id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Proposal {id} not found"
        )
    return proposal


@router.get(
    "/repositories/{id}/remediations",
    response_model=list[RemediationProposalResponse],
    summary="List Repository Remediation Proposals",
    description="List active and historical remediation proposals for a repository.",
)
async def list_repository_remediations(
    id: str,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[RemediationProposalResponse]:
    """List proposals for a repository."""
    repo = (await db.execute(select(Repository).where(Repository.id == id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {id} not found"
        )

    service = RemediationService()
    return await service.get_proposals_for_repository(db, id, status=status_filter, limit=limit)


@router.post(
    "/remediations/{id}/verify",
    response_model=PatchVerificationResponse,
    summary="Verify Remediation in Isolated Sandbox",
    description="Execute dual-run sandbox analysis to test pre-patch vs post-patch state and detect regressions.",
)
async def verify_remediation(
    id: str,
    payload: VerifyPatchRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> PatchVerificationResponse:
    """Verify proposed patch in isolated sandbox."""
    verifier = PatchVerifier()
    base_dir = payload.base_source_dir if payload else None
    try:
        return await verifier.verify_proposal(db, id, base_source_dir=base_dir)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/remediations/{id}/create-pr",
    response_model=RemediationPullRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Corrective Draft Pull Request",
    description="Create a reviewable draft PR on GitHub containing the verified patch and evidence.",
)
async def create_corrective_pr(
    id: str,
    payload: CreateCorrectivePRRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> RemediationPullRequestResponse:
    """Create a draft pull request on GitHub."""
    pr_manager = RemediationPRManager()
    base_branch = payload.base_branch if payload else None
    try:
        return await pr_manager.create_corrective_pr(db, id, base_branch=base_branch)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
