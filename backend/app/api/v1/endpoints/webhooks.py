"""GitHub Webhook Ingress Endpoint."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.github.webhook import persist_webhook_delivery, verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/github",
    summary="GitHub Webhook Ingress",
    description="Authenticates incoming GitHub events via HMAC-SHA256 and enqueues them for durable processing.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def github_webhook_ingress(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
    x_github_delivery: str | None = Header(default=None, alias="X-GitHub-Delivery"),
    x_github_event: str | None = Header(default=None, alias="X-GitHub-Event"),
) -> Response:
    """Ingests raw GitHub webhooks with constant-time HMAC verification and atomic deduplication."""
    # 1. Validate required headers
    if not x_hub_signature_256:
        logger.warning("Rejected webhook request: Missing X-Hub-Signature-256 header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing cryptographic signature header",
        )

    if not x_github_delivery:
        logger.warning("Rejected webhook request: Missing X-GitHub-Delivery header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-GitHub-Delivery header",
        )

    event_type = x_github_event or "unknown"

    # 2. Extract raw bytes BEFORE parsing to avoid whitespace/key mutations
    raw_body = await request.body()

    # 3. Constant-time HMAC-SHA256 verification (Fail Closed)
    is_valid = verify_webhook_signature(
        payload_bytes=raw_body,
        signature_header=x_hub_signature_256,
        secret=settings.GITHUB_WEBHOOK_SECRET,
    )
    if not is_valid:
        logger.warning(
            f"Rejected unauthorized webhook delivery {x_github_delivery}: Signature mismatch"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cryptographic HMAC signature",
        )

    # 4. Handle GitHub Ping event immediately
    if event_type == "ping":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ok",
                "message": "MergeMind webhook ingress verified and operational",
                "delivery_id": x_github_delivery,
            },
        )

    # 5. Parse JSON payload summary
    try:
        payload_dict: dict[str, Any] = json.loads(raw_body.decode("utf-8"))
    except Exception:
        payload_dict = {}

    action = payload_dict.get("action")

    # 6. Atomic deduplication and queueing
    is_duplicate, delivery = await persist_webhook_delivery(
        db=db,
        delivery_id=x_github_delivery,
        event_type=event_type,
        action=action,
        payload_summary=payload_dict,
        as_tuple=True,
    )

    if is_duplicate:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "already_processed",
                "delivery_id": x_github_delivery,
            },
        )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "delivery_id": x_github_delivery,
            "event": event_type,
            "action": action,
        },
    )
