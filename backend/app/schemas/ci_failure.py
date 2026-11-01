"""Pydantic schemas for CI/CD failure intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CIFailureResponse(BaseModel):
    """Schema representing an ingested CI failure."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    pull_request_id: str | None = None
    workflow_run_id: int
    workflow_name: str
    job_id: int | None = None
    job_name: str
    commit_sha: str
    branch: str
    failure_category: str
    status: str
    error_message: str
    log_excerpt: str
    localized_files: list[dict[str, Any]] = Field(default_factory=list)
    root_cause_analysis: dict[str, Any] = Field(default_factory=dict)
    ai_advisory_hypothesis: str | None = None
    created_at: datetime
    updated_at: datetime


class CIFailureIngestRequest(BaseModel):
    """Payload to trigger manual or simulated CI failure ingestion."""

    workflow_run_id: int = 123456
    workflow_name: str = "CI Pipeline"
    job_name: str = "Test Suite"
    commit_sha: str
    branch: str = "main"
    raw_logs: str
    pull_request_id: str | None = None
    changed_files: list[str] | None = None
