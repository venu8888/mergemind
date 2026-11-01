"""Installation Model for GitHub App Organizations and User Accounts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class Installation(Base):
    """Represents a GitHub App installation granting access to repositories."""

    __tablename__ = "installations"

    github_installation_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )
    account_login: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)  # User or Organization
    state: Mapped[str] = mapped_column(
        String(32), default="ACTIVE", nullable=False, index=True
    )  # ACTIVE, SUSPENDED, DELETED
    sync_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    repositories: Mapped[list[Repository]] = relationship(
        "Repository", back_populates="installation"
    )
