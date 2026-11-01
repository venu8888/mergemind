"""Pull Request Model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.repository import Repository


class PullRequest(Base):
    """Represents a GitHub pull request being tracked and analyzed."""

    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "pr_number", name="uq_repo_pr_number"),)

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    author_username: Mapped[str] = mapped_column(String(100), nullable=False)
    base_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    head_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    current_head_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    repository: Mapped[Repository] = relationship("Repository", back_populates="pull_requests")
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        "AnalysisRun", back_populates="pull_request", cascade="all, delete-orphan"
    )
