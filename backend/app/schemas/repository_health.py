"""Pydantic schemas for Repository Health Assessments."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HealthAssessRequest(BaseModel):
    """Request payload to trigger a repository health assessment."""

    branch: str = Field(default="main", description="Branch to assess")
    commit_sha: str | None = Field(default=None, description="Optional explicit commit SHA")
    policy_version: str | None = Field(default=None, description="Optional scoring policy version")


class DimensionScoreResponse(BaseModel):
    """Individual dimension health report."""

    dimension: str
    score: float | None
    weight: float
    status: str  # ENABLED, UNCONFIGURED, DISABLED, FAILED_DEPENDENCY
    details: dict[str, Any] = Field(default_factory=dict)


class RepositoryHealthResponse(BaseModel):
    """Complete repository health snapshot response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    commit_sha: str
    branch_name: str
    health_score: float | None = None
    assessment_completeness: float
    is_qualified: bool
    qualification_reason: str | None = None
    code_quality_score: float | None = None
    security_score: float | None = None
    dependency_score: float | None = None
    test_health_score: float | None = None
    maintainability_score: float | None = None
    scoring_policy_version: str
    dimension_status: dict[str, str]
    summary_metrics: dict[str, Any] | None = None
    status: str
    created_at: datetime
    completed_at: datetime | None = None
