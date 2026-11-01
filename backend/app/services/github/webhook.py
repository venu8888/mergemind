"""GitHub Webhook Signature Verification and Ingress Persistence."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_delivery import WebhookDelivery

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    payload_bytes: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """Verifies HMAC-SHA256 signature from GitHub in constant time.

    Args:
        payload_bytes: The raw, unmodified HTTP request body bytes.
        signature_header: The value of the X-Hub-Signature-256 header.
        secret: The pre-shared secret string configured in GitHub App settings.

    Returns:
        True if the signature is valid, False otherwise (fail-closed).
    """
    if not signature_header or not secret:
        return False

    if not signature_header.startswith("sha256="):
        return False

    received_digest = signature_header.removeprefix("sha256=").strip()
    if not received_digest:
        return False

    secret_bytes = secret.encode("utf-8")
    mac = hmac.new(secret_bytes, msg=payload_bytes, digestmod=hashlib.sha256)
    expected_digest = mac.hexdigest()

    return hmac.compare_digest(expected_digest, received_digest)


async def persist_webhook_delivery(
    arg1: Any = None,
    delivery_id: str | None = None,
    event_type: str | None = None,
    action: str | None = None,
    payload: dict[str, Any] | None = None,
    payload_summary: dict[str, Any] | None = None,
    db: AsyncSession | None = None,
    max_attempts: int = 3,
    as_tuple: bool = False,
) -> WebhookDelivery | None | tuple[bool, WebhookDelivery | None]:
    """Atomically persists a webhook delivery record to enforce idempotency.

    Supports flexible calling conventions:
    - persist_webhook_delivery(delivery_id=..., event_type=..., action=..., payload=..., db=db)
    - persist_webhook_delivery(db, delivery_id, event_type, action, payload_summary)

    Returns:
        WebhookDelivery if newly created, or None if duplicate.
        If as_tuple=True: returns (is_duplicate: bool, delivery: WebhookDelivery | None).
    """
    if isinstance(arg1, AsyncSession):
        db = arg1
    elif arg1 is not None and delivery_id is None:
        delivery_id = str(arg1)

    effective_payload = payload if payload is not None else payload_summary

    now = datetime.now(UTC)
    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        event_type=event_type or "unknown",
        action=action,
        payload_summary=effective_payload,
        status="RECEIVED",
        processing_status="PENDING",
        attempts=0,
        max_attempts=max_attempts,
        scheduled_at=now,
        received_at=now,
    )

    if db is None:
        raise ValueError("db AsyncSession must be provided")

    db.add(delivery)
    try:
        await db.commit()
        await db.refresh(delivery)
        return (False, delivery) if as_tuple else delivery
    except IntegrityError:
        await db.rollback()
        logger.info(f"Duplicate webhook delivery ignored: {delivery_id}")
        return (True, None) if as_tuple else None
