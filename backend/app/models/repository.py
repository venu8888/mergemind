"""Repository Model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.installation import Installation
    from app.models.pull_request import PullRequest
    from app.models.repository_health import RepositoryHealthAssessment


class Repository(Base):
    """Represents a connected GitHub repository under MergeMind analysis."""

    __tablename__ = "repositories"

    installation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("installations.id", ondelete="SET NULL"), nullable=True, index=True
    )
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
    github_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __init__(self, **kwargs):
        if "name" in kwargs and "full_name" not in kwargs:
            kwargs["full_name"] = kwargs.pop("name")
        else:
            kwargs.pop("name", None)
        kwargs.pop("is_private", None)
        super().__init__(**kwargs)

    # Compatibility property
    @property
    def name(self) -> str:
        return self.full_name.split("/")[-1] if "/" in self.full_name else self.full_name

    # Relationships
    installation: Mapped[Installation | None] = relationship(
        "Installation", back_populates="repositories"
    )
    pull_requests: Mapped[list[PullRequest]] = relationship(
        "PullRequest", back_populates="repository", cascade="all, delete-orphan"
    )
    health_assessments: Mapped[list[RepositoryHealthAssessment]] = relationship(
        "RepositoryHealthAssessment", back_populates="repository", cascade="all, delete-orphan"
    )
