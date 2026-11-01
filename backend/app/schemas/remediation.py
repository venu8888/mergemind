"""Pydantic schemas for AI-assisted remediation proposals and verification."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PatchVerificationResponse(BaseModel):
    """Schema representing dual-run sandbox patch verification."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    proposal_id: str
    sandbox_status: str
    is_verified: bool
    regressions_count: int
    resolved_issues_count: int
    pre_patch_findings_count: int
    post_patch_findings_count: int
    pre_patch_findings: list[dict[str, Any]] = Field(default_factory=list)
    post_patch_findings: list[dict[str, Any]] = Field(default_factory=list)
    test_results: dict[str, Any] = Field(default_factory=dict)
    sandbox_logs: str
    duration_ms: int
    created_at: datetime


class RemediationPullRequestResponse(BaseModel):
    """Schema representing a corrective draft pull request."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    proposal_id: str
    repository_id: str
    pr_number: int
    branch_name: str
    base_branch: str
    pr_url: str
    status: str
    merged_at: datetime | None = None
    created_at: datetime


class RemediationProposalResponse(BaseModel):
    """Schema representing an AI-assisted or deterministic remediation proposal."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    ci_failure_id: str | None = None
    finding_id: str | None = None
    pull_request_id: str | None = None
    title: str
    description: str
    target_commit_sha: str
    target_branch: str
    status: str
    provider_name: str
    model_identifier: str | None = None
    confidence_score: float
    patch_diff: str
    affected_files: list[str] = Field(default_factory=list)
    rationale: str
    evidence_records: dict[str, Any] = Field(default_factory=dict)
    verifications: list[PatchVerificationResponse] = Field(default_factory=list)
    remediation_pr: RemediationPullRequestResponse | None = None
    created_at: datetime
    updated_at: datetime


class ProposeRemediationRequest(BaseModel):
    """Payload to trigger a remediation proposal."""

    ci_failure_id: str | None = None
    finding_id: str | None = None


class VerifyPatchRequest(BaseModel):
    """Payload to trigger dual-run sandbox verification of a patch."""

    base_source_dir: str | None = None


class CreateCorrectivePRRequest(BaseModel):
    """Payload to trigger draft PR creation on GitHub."""

    base_branch: str | None = None
