"""Webhook event dispatcher executing business logic for claimed queue jobs."""

import json
import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_delivery import WebhookDelivery
from app.services.github.lifecycle import (
    handle_installation_event,
    reconcile_installation_repositories,
)
from app.services.github.pr_sync import sync_pull_request
from app.services.github.queue_worker import WebhookQueueWorker

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Dispatches claimed webhook jobs to domain handlers with lease fencing."""

    def __init__(
        self,
        worker: WebhookQueueWorker,
        client_factory: Callable[..., Any] | None = None,
    ):
        self.worker = worker
        self.client_factory = client_factory

    @staticmethod
    def _parse_payload(delivery: WebhookDelivery) -> dict[str, Any]:
        payload = getattr(delivery, "payload_summary", None) or getattr(delivery, "payload", None)
        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except Exception:
                return {}
        return payload or {}

    async def dispatch_event(
        self,
        delivery: WebhookDelivery,
        db: AsyncSession,
    ) -> Any:
        """Route the webhook event to the appropriate domain service."""
        payload = self._parse_payload(delivery)
        event_type = delivery.event_type

        logger.info(
            f"Dispatching delivery {delivery.delivery_id} (event: {event_type}, action: {delivery.action})"
        )

        if event_type == "installation":
            return await handle_installation_event(payload, db)

        elif event_type == "installation_repositories":
            installation_data = payload.get("installation") or {}
            github_install_id = installation_data.get("id")
            if github_install_id and self.client_factory:
                client = self.client_factory(github_install_id)
                return await reconcile_installation_repositories(
                    github_installation_id=github_install_id,
                    client=client,
                    db=db,
                )
            return None

        elif event_type == "pull_request":
            return await sync_pull_request(payload, db)

        else:
            logger.info(f"Unhandled or passive webhook event: {event_type}")
            return None

    async def process_one(self, db: AsyncSession) -> bool:
        """Claims a single job, dispatches it, and fences completion/failure."""
        job = await self.worker.claim_next_job(db)
        if not job:
            return False

        try:
            await self.dispatch_event(job, db)
            success = await self.worker.complete_job(
                job_id=job.id,
                lease_token=job.lease_token,
                db=db,
            )
            if not success:
                logger.warning(
                    f"Complete fence rejected for job {job.id} (lease expired or reclaimed)"
                )
            return True
        except Exception as exc:
            logger.exception(f"Error processing webhook delivery {job.delivery_id}: {exc}")
            await self.worker.fail_job(
                job_id=job.id,
                lease_token=job.lease_token,
                error_message=str(exc),
                db=db,
            )
            return True
