"""Pydantic schemas for PR Verification and Delta Analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class VerifyPRRequest(BaseModel):
    """Request payload to manually trigger PR verification."""

    commit_sha: str | None = Field(default=None, description="Optional target commit SHA")


class CheckSummaryResponse(BaseModel):
    """Summary of a discrete verification check."""

    check_type: str  # STATIC_LINT, SECURITY_SCAN, DEPENDENCY_AUDIT, TEST_EXECUTION
    status: str  # PASSED, FAILED, TIMEOUT, UNAVAILABLE, SKIPPED
    duration_ms: int = 0
    message: str | None = None
    output_digest: str | None = None


class FindingResponse(BaseModel):
    """Detailed finding response with delta provenance."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tool_source: str
    tool_version: str
    category: str
    severity: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    rule_id: str | None = None
    title: str
    message: str
    is_blocking: bool
    delta_status: str  # INTRODUCED_NEW, EXISTING_BASELINE, FIXED_IN_PR, AMBIGUOUS_MODIFIED_CONTEXT
    fingerprint: str | None = None
    provenance_type: str  # DETERMINISTIC_TOOL, EMPIRICAL_EXECUTION, AI_ADVISORY
    advisory_confidence: float | None = None


class PRVerificationResponse(BaseModel):
    """Complete PR verification report."""

    model_config = ConfigDict(from_attributes=True)

    analysis_run_id: str
    pull_request_id: str
    commit_sha: str
    run_number: int
    status: str
    verification_completeness: float
    quality_score: float | None = None
    gate_verdict: str
    delta_summary: dict[str, Any] | None = None
    checks: list[CheckSummaryResponse] = Field(default_factory=list)
    findings: list[FindingResponse] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None
