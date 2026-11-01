"""Repository Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RepositoryRead(BaseModel):
    """Schema for public representation of a connected repository."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    github_repo_id: int
    full_name: str
    name: str | None = None
    default_branch: str
    is_active: bool
    installation_id: str | None = None
    registered_at: datetime
    github_updated_at: datetime | None = None


class RepositorySyncResponse(BaseModel):
    """Schema returned after triggering manual repository sync."""

    repository_id: str
    full_name: str
    synced_pull_requests_count: int
    status: str
