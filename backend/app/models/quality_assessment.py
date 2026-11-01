"""Quality Assessment Model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun


class QualityAssessment(Base):
    """Represents the decoupled quality assessment evaluated for an analysis run."""

    __tablename__ = "quality_assessments"
    __table_args__ = (UniqueConstraint("analysis_run_id", name="uq_assessment_run"),)

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    verification_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    gate_decision: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # PASSED, WARNING, BLOCKED
    gate_policy_name: Mapped[str] = mapped_column(String(50), default="default", nullable=False)
    rule_evaluations: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    analysis_run: Mapped[AnalysisRun] = relationship(
        "AnalysisRun", back_populates="quality_assessment"
    )
