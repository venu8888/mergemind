"""Webhook event dispatcher executing business logic for claimed queue jobs."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository
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
            "Dispatching delivery %s (event: %s, action: %s)",
            delivery.delivery_id,
            event_type,
            delivery.action,
        )

        if event_type == "installation":
            return await handle_installation_event(payload, db)

        elif event_type == "installation_repositories":
            installation_data = payload.get("installation") or {}
            github_install_id = installation_data.get("id")
            client = None
            if self.client_factory and github_install_id:
                client = self.client_factory(github_install_id)
            elif github_install_id:
                from app.services.github.auth import get_github_client_for_installation

                try:
                    client = await get_github_client_for_installation(github_install_id)
                except Exception as exc:
                    logger.warning("Could not instantiate installation client: %s", exc)

            if github_install_id and client:
                return await reconcile_installation_repositories(
                    github_installation_id=github_install_id,
                    client=client,
                    db=db,
                )
            return None

        elif event_type == "pull_request":
            pr_res, analysis_run = await sync_pull_request(payload, db)

            # Post-Merge Health Reassessment Invariant:
            # Detect genuine merged PRs and trigger fresh repository health assessment.
            action = payload.get("action")
            pr_data = payload.get("pull_request") or {}
            is_merged = pr_data.get("merged") is True or (
                action == "closed" and pr_data.get("merged") is True
            )

            if is_merged:
                repo_data = payload.get("repository", {})
                repo_github_id = repo_data.get("id")
                repo = (
                    await db.execute(
                        select(Repository).where(Repository.github_repo_id == repo_github_id)
                    )
                ).scalar_one_or_none()

                if repo:
                    logger.info(
                        "Detected genuine merged PR #%s on %s; triggering fresh repository health assessment",
                        pr_data.get("number"),
                        repo.full_name,
                    )
                    try:
                        from app.services.health.service import RepositoryHealthService

                        health_service = RepositoryHealthService()
                        base_branch = pr_data.get("base", {}).get("ref", "main")
                        merge_commit_sha = pr_data.get("merge_commit_sha") or pr_data.get(
                            "head", {}
                        ).get("sha", "")

                        await health_service.assess_repository(
                            repository_id=repo.id,
                            source_dir="",
                            commit_sha=merge_commit_sha,
                            branch_name=base_branch,
                            db=db,
                        )
                    except Exception as exc:
                        logger.warning("Could not execute post-merge health assessment: %s", exc)

            return pr_res

        elif event_type == "workflow_job":
            job_data = payload.get("workflow_job") or {}
            action = payload.get("action")
            conclusion = job_data.get("conclusion")

            # Only process completed failure events
            if action == "completed" and conclusion == "failure":
                job_id = job_data.get("id")
                run_id = job_data.get("run_id")
                job_name = job_data.get("name", "test")
                workflow_name = job_data.get("workflow_name", "CI Pipeline")
                commit_sha = job_data.get("head_sha", "")
                branch = job_data.get("head_branch", "main")
                repo_data = payload.get("repository", {})
                repo_github_id = repo_data.get("id")
                repo_full_name = repo_data.get("full_name")

                repo = (
                    await db.execute(
                        select(Repository).where(Repository.github_repo_id == repo_github_id)
                    )
                ).scalar_one_or_none()
                if not repo and repo_github_id:
                    repo = Repository(
                        github_repo_id=repo_github_id,
                        full_name=repo_full_name or "unknown",
                        is_active=True,
                    )
                    db.add(repo)
                    await db.flush()

                if repo:
                    client = None
                    installation_data = payload.get("installation") or {}
                    github_install_id = installation_data.get("id")
                    if self.client_factory and github_install_id:
                        client = self.client_factory(github_install_id)
                    elif github_install_id:
                        from app.services.github.auth import get_github_client_for_installation

                        try:
                            client = await get_github_client_for_installation(github_install_id)
                        except Exception as e:
                            logger.warning("Could not get installation client: %s", e)

                    raw_logs = ""
                    if client and repo_full_name and job_id:
                        try:
                            raw_logs = await client.get_job_logs(repo_full_name, job_id)
                        except Exception as exc:
                            logger.warning("Failed to fetch logs for job %s: %s", job_id, exc)

                    if not raw_logs:
                        failed_steps = [
                            s.get("name")
                            for s in job_data.get("steps", [])
                            if s.get("conclusion") == "failure"
                        ]
                        raw_logs = (
                            f"FAILED: Job '{job_name}' failed in workflow '{workflow_name}' "
                            f"on steps: {failed_steps}"
                        )

                    from app.services.ci_intelligence.service import CIFailureService

                    ci_service = CIFailureService()
                    return await ci_service.ingest_failure(
                        db=db,
                        repository_id=repo.id,
                        workflow_run_id=run_id or 0,
                        workflow_name=workflow_name,
                        job_name=job_name,
                        job_id=job_id,
                        commit_sha=commit_sha,
                        branch=branch,
                        raw_logs=raw_logs,
                    )
            return None

        elif event_type == "workflow_run":
            wf_data = payload.get("workflow_run") or {}
            action = payload.get("action")
            conclusion = wf_data.get("conclusion")
            logger.info(
                "Observed workflow_run %s event: action=%s conclusion=%s",
                wf_data.get("id"),
                action,
                conclusion,
            )
            return None

        else:
            logger.info("Unhandled or passive webhook event: %s", event_type)
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
                    "Complete fence rejected for job %s (lease expired or reclaimed)", job.id
                )
            return True
        except Exception as exc:
            logger.exception("Error processing webhook delivery %s: %s", job.delivery_id, exc)
            await self.worker.fail_job(
                job_id=job.id,
                lease_token=job.lease_token,
                error_message=str(exc),
                db=db,
            )
            return True
