"""Pull Request Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PullRequestRead(BaseModel):
    """Schema for public representation of an ingested pull request."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    pr_number: int
    title: str
    state: str
    author_username: str
    base_branch: str
    head_branch: str
    current_head_sha: str
    opened_at: datetime
    github_updated_at: datetime | None = None
