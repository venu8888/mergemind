"""Test Execution Model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.evidence_record import EvidenceRecord


class TestExecution(Base):
    """Represents the execution outcome of an isolated test suite."""

    __tablename__ = "test_executions"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    framework: Mapped[str] = mapped_column(String(50), default="PYTEST", nullable=False)
    total_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exit_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stdout_sample: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr_sample: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="SUCCESS", nullable=False
    )  # SUCCESS, FAILED, SKIPPED_SANDBOX_UNAVAILABLE

    # Relationships
    analysis_run: Mapped[AnalysisRun] = relationship(
        "AnalysisRun", back_populates="test_executions"
    )
    evidence_records: Mapped[list[EvidenceRecord]] = relationship(
        "EvidenceRecord", back_populates="test_execution", cascade="all, delete-orphan"
    )
