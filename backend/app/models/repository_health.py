"""Repository Health Assessment Model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.repository import Repository


class RepositoryHealthAssessment(Base):
    """Represents a point-in-time health assessment of a repository's target branch."""

    __tablename__ = "repository_health_assessments"
    __table_args__ = (
        Index("ix_repo_health_repo_id", "repository_id"),
        Index("ix_repo_health_commit_sha", "commit_sha"),
    )

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    branch_name: Mapped[str] = mapped_column(String(255), default="main", nullable=False)

    # Top-level metrics
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessment_completeness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    qualification_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Sub-scores [0.0 - 100.0]
    code_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    security_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dependency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    test_health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    maintainability_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Calibration & Availability
    scoring_policy_version: Mapped[str] = mapped_column(
        String(50), default="v2.2-calibrated", nullable=False
    )
    dimension_status: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    summary_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False
    )  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    repository: Mapped[Repository] = relationship("Repository", back_populates="health_assessments")
