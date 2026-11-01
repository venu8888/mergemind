"""Pydantic schemas for the comprehensive developer repository dashboard."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ci_failure import CIFailureResponse
from app.schemas.remediation import RemediationProposalResponse
from app.schemas.repository import RepositoryRead
from app.schemas.repository_health import HealthAssessmentResponse


class HealthTimelinePoint(BaseModel):
    """Historical assessment data point for trend visualization."""

    id: str
    commit_sha: str
    branch_name: str
    health_score: float | None = None
    assessment_completeness: float
    is_qualified: bool
    code_quality_score: float | None = None
    security_score: float | None = None
    dependency_score: float | None = None
    test_health_score: float | None = None
    maintainability_score: float | None = None
    created_at: datetime


class ActionableRecommendation(BaseModel):
    """Structured recommendation derived from actual defects with evidence links."""

    category: str
    title: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    target_file: str | None = None
    line_number: int | None = None
    remediation_proposal_id: str | None = None
    evidence_id: str | None = None


class RepositoryDashboardResponse(BaseModel):
    """Consolidated dashboard contract powering the developer platform interface."""

    model_config = ConfigDict(from_attributes=True)

    repository: RepositoryRead
    latest_health: HealthAssessmentResponse | None = None
    health_history: list[HealthTimelinePoint] = Field(default_factory=list)
    open_ci_failures: list[CIFailureResponse] = Field(default_factory=list)
    active_remediations: list[RemediationProposalResponse] = Field(default_factory=list)
    actionable_recommendations: list[ActionableRecommendation] = Field(default_factory=list)
    summary_counts: dict[str, int] = Field(default_factory=dict)
