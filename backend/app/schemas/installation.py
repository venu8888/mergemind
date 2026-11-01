"""Installation Schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InstallationRead(BaseModel):
    """Schema for public representation of a GitHub App installation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    github_installation_id: int
    account_login: str
    account_type: str
    state: str
    sync_version: int
    installed_at: datetime
    suspended_at: datetime | None = None
