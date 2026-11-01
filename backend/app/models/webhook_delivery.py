"""Webhook Delivery Model for Ingestion Deduplication and Audit."""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WebhookDelivery(Base):
    """Stores incoming GitHub webhook delivery identifiers to enforce idempotency and durable queueing."""

    __tablename__ = "webhook_deliveries"

    delivery_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=True)
    payload_summary: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="RECEIVED", nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Durable Fenced Queue Attributes
    processing_status: Mapped[str] = mapped_column(
        String(32), default="PENDING", nullable=False, index=True
    )  # PENDING, PROCESSING, COMPLETED, FAILED, DEAD_LETTER
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    lease_generation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compatibility property
    @property
    def payload(self) -> dict | None:
        return self.payload_summary

    @payload.setter
    def payload(self, value: dict | None) -> None:
        self.payload_summary = value
