"""Evidence Record Model."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.finding import Finding
    from app.models.test_execution import TestExecution


class EvidenceRecord(Base):
    """Stores cryptographic or raw structured proof backing a finding or test execution."""

    __tablename__ = "evidence_records"

    finding_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("findings.id", ondelete="CASCADE"), nullable=True, index=True
    )
    test_execution_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("test_executions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # EXIT_CODE, STACK_TRACE, AST_NODE, SCAN_LOG
    raw_digest: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 of raw tool output
    structured_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    finding: Mapped[Finding | None] = relationship("Finding", back_populates="evidence_records")
    test_execution: Mapped[TestExecution | None] = relationship(
        "TestExecution", back_populates="evidence_records"
    )
