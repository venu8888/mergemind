"""Analysis Run Model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.pull_request import PullRequest
    from app.models.quality_assessment import QualityAssessment
    from app.models.test_execution import TestExecution


class AnalysisRun(Base):
    """Represents a discrete verification analysis run bound to an immutable commit SHA."""

    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("pull_request_id", "commit_sha", "run_number", name="uq_pr_commit_run"),
    )

    pull_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    run_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False, index=True
    )  # PENDING, RUNNING, COMPLETED, FAILED
    runner_type: Mapped[str] = mapped_column(
        String(32), default="CONTAINER", nullable=False
    )  # CONTAINER, DISABLED
    runner_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    pull_request: Mapped[PullRequest] = relationship("PullRequest", back_populates="analysis_runs")
    findings: Mapped[list[Finding]] = relationship(
        "Finding", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    test_executions: Mapped[list[TestExecution]] = relationship(
        "TestExecution", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    quality_assessment: Mapped[QualityAssessment | None] = relationship(
        "QualityAssessment",
        back_populates="analysis_run",
        uselist=False,
        cascade="all, delete-orphan",
    )
