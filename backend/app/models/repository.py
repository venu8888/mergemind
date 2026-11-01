"""Repository Model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.pull_request import PullRequest


class Repository(Base):
    """Represents a connected GitHub repository under MergeMind analysis."""

    __tablename__ = "repositories"

    github_repo_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings_override: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    pull_requests: Mapped[list[PullRequest]] = relationship(
        "PullRequest", back_populates="repository", cascade="all, delete-orphan"
    )
