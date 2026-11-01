"""Finding Model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.evidence_record import EvidenceRecord


class Finding(Base):
    """Represents a discrete defect, advisory, or security alert produced by an analysis run."""

    __tablename__ = "findings"
    __table_args__ = (
        Index("idx_findings_run_severity", "analysis_run_id", "severity", "is_blocking"),
        Index("ix_findings_fingerprint", "fingerprint"),
    )

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    tool_source: Mapped[str] = mapped_column(String(50), nullable=False)  # RUFF, BANDIT, PYTEST, AI
    tool_version: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SYNTAX, SECURITY, TEST_REGRESSION, AI_ADVISORY
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[Text] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(50), default="CONFIRMED_DETERMINISTIC", nullable=False
    )  # CONFIRMED_DETERMINISTIC, UNVERIFIED_ADVISORY
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Phase 3 Delta Classification & Provenance
    delta_status: Mapped[str] = mapped_column(
        String(32), default="UNKNOWN", nullable=False
    )  # INTRODUCED_NEW, EXISTING_BASELINE, FIXED_IN_PR, PRE_EXISTING_MODIFIED, AMBIGUOUS_MODIFIED_CONTEXT, UNKNOWN
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provenance_type: Mapped[str] = mapped_column(
        String(32), default="DETERMINISTIC_TOOL", nullable=False
    )  # DETERMINISTIC_TOOL, EMPIRICAL_EXECUTION, AI_ADVISORY
    advisory_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    analysis_run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="findings")
    evidence_records: Mapped[list[EvidenceRecord]] = relationship(
        "EvidenceRecord", back_populates="finding", cascade="all, delete-orphan"
    )
