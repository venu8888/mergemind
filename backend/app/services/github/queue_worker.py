"""PostgreSQL-Backed Durable Fenced Webhook Queue Worker."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import and_, case, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_delivery import WebhookDelivery

logger = logging.getLogger(__name__)


class WebhookQueueWorker:
    """Manages transactional claiming, heartbeating, completion, and failure of queued jobs."""

    def __init__(
        self,
        worker_id: str | None = None,
        lease_duration_minutes: int = 5,
    ):
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.lease_duration_minutes = lease_duration_minutes

    @staticmethod
    def _is_sqlite(db: AsyncSession) -> bool:
        """Detect whether the current database session is bound to SQLite (for fast unit testing)."""
        bind = db.bind
        if bind is not None and hasattr(bind, "dialect"):
            return bind.dialect.name == "sqlite"
        return False

    def _get_lease_cutoff_clause(self, db: AsyncSession):
        """Returns SQLAlchemy expression for the lease expiration boundary using database time."""
        if self._is_sqlite(db):
            return func.datetime("now", f"-{self.lease_duration_minutes} minutes")
        return func.now() - text(f"INTERVAL '{self.lease_duration_minutes} minutes'")

    async def reap_exhausted_jobs(self, db: AsyncSession) -> int:
        """Atomically transitions exhausted PENDING and crashed final-attempt PROCESSING jobs to DEAD_LETTER.

        Leaves all jobs with active leases untouched.
        """
        lease_cutoff = self._get_lease_cutoff_clause(db)

        stmt = (
            update(WebhookDelivery)
            .where(
                or_(
                    # Case 1: Orphaned exhausted PENDING jobs
                    and_(
                        WebhookDelivery.processing_status == "PENDING",
                        WebhookDelivery.attempts >= WebhookDelivery.max_attempts,
                    ),
                    # Case 2: Abandoned final-attempt PROCESSING jobs whose leases expired
                    and_(
                        WebhookDelivery.processing_status == "PROCESSING",
                        WebhookDelivery.locked_at < lease_cutoff,
                        WebhookDelivery.attempts >= WebhookDelivery.max_attempts,
                    ),
                )
            )
            .values(
                processing_status="DEAD_LETTER",
                locked_at=None,
                locked_by=None,
                lease_token=None,
                last_error=case(
                    (
                        WebhookDelivery.processing_status == "PROCESSING",
                        func.coalesce(
                            WebhookDelivery.last_error,
                            "Lease expired on final attempt (worker crash)",
                        ),
                    ),
                    else_=func.coalesce(
                        WebhookDelivery.last_error,
                        "Max retry attempts exhausted while pending",
                    ),
                ),
                updated_at=func.now(),
            )
        )

        result = await db.execute(stmt)
        await db.commit()
        reaped_count = result.rowcount or 0
        if reaped_count > 0:
            logger.warning(f"Reaped {reaped_count} exhausted queue jobs into DEAD_LETTER state")
        return reaped_count

    async def claim_jobs(
        self,
        db: AsyncSession,
        batch_size: int = 10,
    ) -> list[tuple[WebhookDelivery, str]]:
        """Claims eligible PENDING jobs or reclaims expired PROCESSING jobs with fresh lease tokens.

        Returns:
            A list of tuples: (job: WebhookDelivery, lease_token: str).
        """
        lease_cutoff = self._get_lease_cutoff_clause(db)
        now_expr = func.datetime("now", "+1 minute") if self._is_sqlite(db) else func.now()

        # Step 1: Select IDs of claimable jobs with FOR UPDATE SKIP LOCKED on PostgreSQL
        claimable_stmt = (
            select(WebhookDelivery.id)
            .where(
                and_(
                    or_(
                        and_(
                            WebhookDelivery.processing_status == "PENDING",
                            WebhookDelivery.scheduled_at <= now_expr,
                            or_(
                                WebhookDelivery.locked_at.is_(None),
                                WebhookDelivery.locked_at < lease_cutoff,
                            ),
                        ),
                        and_(
                            WebhookDelivery.processing_status == "PROCESSING",
                            WebhookDelivery.locked_at < lease_cutoff,
                        ),
                    ),
                    WebhookDelivery.attempts < WebhookDelivery.max_attempts,
                )
            )
            .order_by(WebhookDelivery.scheduled_at.asc())
            .limit(batch_size)
        )

        if not self._is_sqlite(db):
            claimable_stmt = claimable_stmt.with_for_update(skip_locked=True)

        result = await db.execute(claimable_stmt)
        candidate_ids = [row[0] for row in result.all()]

        if not candidate_ids:
            return []

        # Step 2: Establish lease ownership with a new lease_token and increment generation
        claimed_jobs: list[tuple[WebhookDelivery, str]] = []

        for job_id in candidate_ids:
            new_lease_token = str(uuid.uuid4())
            update_stmt = (
                update(WebhookDelivery)
                .where(WebhookDelivery.id == job_id)
                .values(
                    processing_status="PROCESSING",
                    locked_at=func.now(),
                    locked_by=self.worker_id,
                    lease_token=new_lease_token,
                    lease_generation=WebhookDelivery.lease_generation + 1,
                    attempts=WebhookDelivery.attempts + 1,
                    updated_at=func.now(),
                )
            )
            await db.execute(update_stmt)

            # Retrieve refreshed job
            job_stmt = select(WebhookDelivery).where(WebhookDelivery.id == job_id)
            job_res = await db.execute(job_stmt)
            job = job_res.scalar_one_or_none()
            if job:
                claimed_jobs.append((job, new_lease_token))

        await db.commit()
        return claimed_jobs

    async def claim_next_job(self, db: AsyncSession) -> WebhookDelivery | None:
        """Convenience method to claim the single next highest-priority job."""
        claimed = await self.claim_jobs(db, batch_size=1)
        if claimed:
            job, lease_token = claimed[0]
            job.lease_token = lease_token
            return job
        return None

    async def heartbeat_lease(
        self,
        job_id: str,
        lease_token: str,
        db: AsyncSession,
    ) -> bool:
        """Renews an active lease if the lease token matches and lease has not expired."""
        lease_cutoff = self._get_lease_cutoff_clause(db)

        stmt = (
            update(WebhookDelivery)
            .where(
                WebhookDelivery.id == job_id,
                WebhookDelivery.lease_token == lease_token,
                WebhookDelivery.processing_status == "PROCESSING",
                WebhookDelivery.locked_at >= lease_cutoff,
            )
            .values(locked_at=func.now(), updated_at=func.now())
        )

        result = await db.execute(stmt)
        await db.commit()
        return (result.rowcount or 0) > 0

    async def complete_job(
        self,
        job_id: str,
        lease_token: str,
        db: AsyncSession,
    ) -> bool:
        """Marks a job COMPLETED, strictly verifying that the lease token and lease window remain valid."""
        lease_cutoff = self._get_lease_cutoff_clause(db)

        stmt = (
            update(WebhookDelivery)
            .where(
                WebhookDelivery.id == job_id,
                WebhookDelivery.lease_token == lease_token,
                WebhookDelivery.processing_status == "PROCESSING",
                WebhookDelivery.locked_at >= lease_cutoff,
            )
            .values(
                processing_status="COMPLETED",
                locked_at=None,
                locked_by=None,
                lease_token=None,
                updated_at=func.now(),
            )
        )

        result = await db.execute(stmt)
        await db.commit()
        success = (result.rowcount or 0) > 0
        if not success:
            logger.warning(
                f"Completion fencing rejected: Job {job_id} lease expired or was revoked"
            )
        return success

    async def fail_job(
        self,
        job_id: str,
        lease_token: str,
        error_message: str,
        db: AsyncSession,
    ) -> bool:
        """Records job failure with exponential backoff or transitions to DEAD_LETTER under fencing."""
        lease_cutoff = self._get_lease_cutoff_clause(db)

        if self._is_sqlite(db):
            backoff_calc = func.datetime("now", "+10 seconds")
        else:
            backoff_calc = func.now() + (
                func.power(2, WebhookDelivery.attempts) * text("INTERVAL '10 seconds'")
            )

        stmt = (
            update(WebhookDelivery)
            .where(
                WebhookDelivery.id == job_id,
                WebhookDelivery.lease_token == lease_token,
                WebhookDelivery.processing_status == "PROCESSING",
                WebhookDelivery.locked_at >= lease_cutoff,
            )
            .values(
                processing_status=case(
                    (WebhookDelivery.attempts >= WebhookDelivery.max_attempts, "DEAD_LETTER"),
                    else_="PENDING",
                ),
                locked_at=None,
                locked_by=None,
                lease_token=None,
                last_error=error_message,
                scheduled_at=case(
                    (
                        WebhookDelivery.attempts >= WebhookDelivery.max_attempts,
                        WebhookDelivery.scheduled_at,
                    ),
                    else_=backoff_calc,
                ),
                updated_at=func.now(),
            )
        )

        result = await db.execute(stmt)
        await db.commit()
        success = (result.rowcount or 0) > 0
        if not success:
            logger.warning(f"Failure fencing rejected: Job {job_id} lease expired or was revoked")
        return success
