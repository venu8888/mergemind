"""Consolidated dashboard and health improvement timeline APIs."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.analysis_run import AnalysisRun
from app.models.ci_failure import CIFailureRecord
from app.models.finding import Finding
from app.models.pull_request import PullRequest
from app.models.remediation import RemediationProposal
from app.models.repository import Repository
from app.models.repository_health import RepositoryHealthAssessment
from app.schemas.dashboard import (
    ActionableRecommendation,
    HealthTimelinePoint,
    RepositoryDashboardResponse,
)
from app.schemas.repository_health import HealthAssessmentResponse
from app.services.health.service import RepositoryHealthService

router = APIRouter()


@router.get(
    "/repositories/{id}/dashboard",
    response_model=RepositoryDashboardResponse,
    summary="Get Repository Developer Dashboard",
    description="Retrieve consolidated repository health, failure intelligence, active remediations, and recommendations.",
)
async def get_repository_dashboard(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> RepositoryDashboardResponse:
    """Retrieve full platform dashboard for a repository."""
    repo = (await db.execute(select(Repository).where(Repository.id == id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {id} not found"
        )

    # 1. Latest Health Assessment
    latest_health_stmt = (
        select(RepositoryHealthAssessment)
        .where(RepositoryHealthAssessment.repository_id == id)
        .order_by(desc(RepositoryHealthAssessment.created_at))
        .limit(1)
    )
    latest_health = (await db.execute(latest_health_stmt)).scalar_one_or_none()

    # 2. Historical Health Timeline
    history_stmt = (
        select(RepositoryHealthAssessment)
        .where(RepositoryHealthAssessment.repository_id == id)
        .order_by(desc(RepositoryHealthAssessment.created_at))
        .limit(30)
    )
    history_rows = (await db.execute(history_stmt)).scalars().all()
    health_history = [
        HealthTimelinePoint(
            id=h.id,
            commit_sha=h.commit_sha,
            branch_name=h.branch_name,
            health_score=h.health_score,
            assessment_completeness=h.assessment_completeness,
            is_qualified=h.is_qualified,
            code_quality_score=h.code_quality_score,
            security_score=h.security_score,
            dependency_score=h.dependency_score,
            test_health_score=h.test_health_score,
            maintainability_score=h.maintainability_score,
            created_at=h.created_at,
        )
        for h in reversed(history_rows)
    ]

    # 3. Open CI Failures
    failures_stmt = (
        select(CIFailureRecord)
        .where(
            CIFailureRecord.repository_id == id,
            CIFailureRecord.status.in_(
                ["DETECTED", "ANALYZED", "INVESTIGATING", "REMEDIATION_PROPOSED"]
            ),
        )
        .order_by(desc(CIFailureRecord.created_at))
        .limit(10)
    )
    open_failures = list((await db.execute(failures_stmt)).scalars().all())

    # 4. Active Remediation Proposals
    remediations_stmt = (
        select(RemediationProposal)
        .where(RemediationProposal.repository_id == id)
        .order_by(desc(RemediationProposal.created_at))
        .limit(10)
    )
    active_remediations = list((await db.execute(remediations_stmt)).scalars().all())

    # 5. Synthesize Actionable Recommendations from actual findings & CI failures (No fabricated data)
    recommendations: list[ActionableRecommendation] = []
    findings_stmt = (
        select(Finding)
        .join(AnalysisRun, Finding.analysis_run_id == AnalysisRun.id)
        .join(PullRequest, AnalysisRun.pull_request_id == PullRequest.id)
        .where(PullRequest.repository_id == id, Finding.is_blocking.is_(True))
        .order_by(desc(Finding.created_at))
        .limit(5)
    )
    blocking_findings = list((await db.execute(findings_stmt)).scalars().all())
    for f in blocking_findings:
        recommendations.append(
            ActionableRecommendation(
                category="SECURITY" if f.category == "SECURITY" else "CODE_QUALITY",
                title=f"Resolve blocking finding: {f.rule_id}",
                severity=f.severity,
                description=f.message,
                target_file=f.file_path,
                line_number=f.start_line,
                evidence_id=f.id,
            )
        )

    for fail in open_failures[:3]:
        recommendations.append(
            ActionableRecommendation(
                category="CI_FAILURE",
                title=f"Remediate {fail.failure_category} in {fail.job_name}",
                severity="CRITICAL"
                if fail.failure_category in ("SECURITY_VIOLATION", "BUILD_ERROR")
                else "HIGH",
                description=fail.error_message,
                target_file=fail.localized_files[0].get("file_path")
                if fail.localized_files
                else None,
                line_number=fail.localized_files[0].get("line_number")
                if fail.localized_files
                else None,
                evidence_id=fail.id,
            )
        )

    # Summary counts
    total_failures = len(open_failures)
    total_remediations = len(active_remediations)

    return RepositoryDashboardResponse(
        repository=repo,
        latest_health=HealthAssessmentResponse.model_validate(latest_health)
        if latest_health
        else None,
        health_history=health_history,
        open_ci_failures=open_failures,
        active_remediations=active_remediations,
        actionable_recommendations=recommendations,
        summary_counts={
            "open_ci_failures": total_failures,
            "active_remediations": total_remediations,
            "total_historical_assessments": len(history_rows),
        },
    )


@router.get(
    "/repositories/{id}/health/history",
    response_model=list[HealthTimelinePoint],
    summary="Get Health Assessment History",
    description="Retrieve chronological assessment timeline points for trend analysis.",
)
async def get_health_history(
    id: str,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[HealthTimelinePoint]:
    """Retrieve chronological health assessment history."""
    repo = (await db.execute(select(Repository).where(Repository.id == id))).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository {id} not found"
        )

    stmt = (
        select(RepositoryHealthAssessment)
        .where(RepositoryHealthAssessment.repository_id == id)
        .order_by(desc(RepositoryHealthAssessment.created_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        HealthTimelinePoint(
            id=h.id,
            commit_sha=h.commit_sha,
            branch_name=h.branch_name,
            health_score=h.health_score,
            assessment_completeness=h.assessment_completeness,
            is_qualified=h.is_qualified,
            code_quality_score=h.code_quality_score,
            security_score=h.security_score,
            dependency_score=h.dependency_score,
            test_health_score=h.test_health_score,
            maintainability_score=h.maintainability_score,
            created_at=h.created_at,
        )
        for h in reversed(rows)
    ]


@router.post(
    "/repositories/{id}/remediation/post-merge-reassess",
    response_model=HealthAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post-Merge Repository Reassessment",
    description="Enforce health score veracity: trigger fresh independent assessment only after a corrective change is merged.",
)
async def post_merge_reassess(
    id: str,
    commit_sha: str = Query(..., description="Merge commit SHA on target branch"),
    branch: str = Query("main", description="Target branch name"),
    db: AsyncSession = Depends(get_db),
) -> HealthAssessmentResponse:
    """Execute fresh whole-repo assessment post-merge and update repository health score."""
    engine = RepositoryHealthService()
    try:
        source_dir = os.getcwd()
        assessment = await engine.assess_repository(
            db=db,
            repository_id=id,
            commit_sha=commit_sha,
            branch_name=branch,
            source_dir=source_dir,
        )
        return HealthAssessmentResponse.model_validate(assessment)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
