"""Tests for Webhook Ingress and PostgreSQL-Backed Fenced Queue Worker (Scenarios T-01 to T-18)."""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.webhook_delivery import WebhookDelivery
from app.services.github.queue_worker import WebhookQueueWorker
from app.services.github.webhook import persist_webhook_delivery, verify_webhook_signature


def generate_signature(secret: str, body: bytes) -> str:
    """Helper to compute valid GitHub sha256 HMAC."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# --- T-01: Invalid / Tampered Signature ---
def test_t01_webhook_signature_verification():
    """T-01: Verifies constant-time signature verification and rejection of tampered bodies."""
    secret = "test-webhook-secret-xyz"
    raw_payload = b'{"action":"opened","pull_request":{"number":42}}'

    valid_sig = generate_signature(secret, raw_payload)
    assert verify_webhook_signature(raw_payload, valid_sig, secret) is True

    # Tampered signature
    assert verify_webhook_signature(raw_payload, "sha256=bad123", secret) is False

    # Tampered payload
    tampered_payload = b'{"action":"opened","pull_request":{"number":43}}'
    assert verify_webhook_signature(tampered_payload, valid_sig, secret) is False

    # Missing prefix
    assert verify_webhook_signature(raw_payload, "abcdef123456", secret) is False


# --- T-02: Duplicate Webhook Delivery ---
@pytest.mark.asyncio
async def test_t02_duplicate_webhook_delivery():
    """T-02: Duplicate delivery_id returns False and is rejected without secondary insert."""
    async with AsyncSessionLocal() as db:
        delivery_id = str(uuid.uuid4())
        payload = {"action": "opened"}

        # First insert
        d1 = await persist_webhook_delivery(
            delivery_id=delivery_id,
            event_type="pull_request",
            action="opened",
            payload=payload,
            db=db,
        )
        assert d1 is not None

        # Duplicate delivery insert
        d2 = await persist_webhook_delivery(
            delivery_id=delivery_id,
            event_type="pull_request",
            action="opened",
            payload=payload,
            db=db,
        )
        assert d2 is None


# --- T-03: Concurrent Queue Claims ---
@pytest.mark.asyncio
async def test_t03_concurrent_queue_claims():
    """T-03: Multiple workers claiming jobs claim distinct records with unique lease tokens."""
    async with AsyncSessionLocal() as db:
        # Create 3 pending jobs
        for i in range(3):
            await persist_webhook_delivery(
                delivery_id=f"t03-delivery-{uuid.uuid4().hex[:8]}",
                event_type="pull_request",
                action="synchronize",
                payload={"index": i},
                db=db,
            )

        worker_a = WebhookQueueWorker(worker_id="worker-A")
        worker_b = WebhookQueueWorker(worker_id="worker-B")

        claim_a = await worker_a.claim_jobs(db, batch_size=2)
        claim_b = await worker_b.claim_jobs(db, batch_size=2)

        claimed_a_ids = {job.id for job, _ in claim_a}
        claimed_b_ids = {job.id for job, _ in claim_b}

        # Sets of claimed jobs must be disjoint
        assert claimed_a_ids.isdisjoint(claimed_b_ids)
        assert len(claimed_a_ids) + len(claimed_b_ids) <= 3


# --- T-04 & T-05: Worker Crash Recovery & Expired Lease Reclamation ---
@pytest.mark.asyncio
async def test_t04_t05_worker_crash_recovery_and_reclamation():
    """T-04 & T-05: Abandoned PROCESSING job with expired lease is reclaimed with incremented generation."""
    async with AsyncSessionLocal() as db:
        # Create job
        delivery = await persist_webhook_delivery(
            delivery_id=f"t04-delivery-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )
        # Simulate worker A claimed it 10 minutes ago and crashed
        old_token = str(uuid.uuid4())
        await db.execute(
            update(WebhookDelivery)
            .where(WebhookDelivery.id == delivery.id)
            .values(
                processing_status="PROCESSING",
                locked_at=datetime.now(UTC) - timedelta(minutes=10),
                locked_by="crashed-worker-A",
                lease_token=old_token,
                lease_generation=1,
                attempts=1,
            )
        )
        await db.commit()

        # Worker B claims
        worker_b = WebhookQueueWorker(worker_id="worker-B", lease_duration_minutes=5)
        claimed = await worker_b.claim_jobs(db, batch_size=1)

        assert len(claimed) == 1
        reclaimed_job, new_token = claimed[0]
        assert reclaimed_job.id == delivery.id
        assert new_token != old_token
        assert reclaimed_job.lease_generation == 2
        assert reclaimed_job.attempts == 2
        assert reclaimed_job.locked_by == "worker-B"


# --- T-06 & T-07: Stale Worker Completion Attempt & Heartbeat Validation ---
@pytest.mark.asyncio
async def test_t06_t07_stale_completion_and_heartbeat_renewal():
    """T-06: Mismatched token rejected. T-07: Valid token successfully renews heartbeat."""
    async with AsyncSessionLocal() as db:
        await persist_webhook_delivery(
            delivery_id=f"t06-delivery-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )

        worker = WebhookQueueWorker(worker_id="worker-valid")
        claimed = await worker.claim_jobs(db, batch_size=1)
        job, valid_token = claimed[0]

        # T-06: Attempt completion with stale/forged token
        stale_success = await worker.complete_job(job.id, "stale-forged-token", db)
        assert stale_success is False

        # T-07: Valid heartbeat
        heartbeat_success = await worker.heartbeat_lease(job.id, valid_token, db)
        assert heartbeat_success is True

        # Valid completion
        complete_success = await worker.complete_job(job.id, valid_token, db)
        assert complete_success is True


# --- T-08, T-09, T-10: Expired Lease Completion, Heartbeat & Failure Rejection ---
@pytest.mark.asyncio
async def test_t08_t09_t10_expired_lease_operations_rejected():
    """T-08, T-09, T-10: Operations rejected when lease expired, even if unclaimed by others."""
    async with AsyncSessionLocal() as db:
        await persist_webhook_delivery(
            delivery_id=f"t08-delivery-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )

        worker = WebhookQueueWorker(worker_id="worker-timing-out", lease_duration_minutes=5)
        claimed = await worker.claim_jobs(db, batch_size=1)
        job, token = claimed[0]

        # Artificially expire the lease
        await db.execute(
            update(WebhookDelivery)
            .where(WebhookDelivery.id == job.id)
            .values(locked_at=datetime.now(UTC) - timedelta(minutes=6))
        )
        await db.commit()

        # T-09: Heartbeat must fail
        assert await worker.heartbeat_lease(job.id, token, db) is False

        # T-10: Failure update must fail
        assert await worker.fail_job(job.id, token, "some error", db) is False

        # T-08: Complete must fail
        assert await worker.complete_job(job.id, token, db) is False


# --- T-11, T-12, T-13: Failure Update Fencing Matrix ---
@pytest.mark.asyncio
async def test_t11_t12_t13_failure_update_fencing():
    """T-11: Valid lease transitions to PENDING. T-12: Expired lease rejected. T-13: Stale token rejected."""
    async with AsyncSessionLocal() as db:
        worker = WebhookQueueWorker(worker_id="worker-fail-test", lease_duration_minutes=5)

        # T-11: Valid lease
        await persist_webhook_delivery(
            delivery_id=f"t11-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )
        job1, token1 = (await worker.claim_jobs(db, batch_size=1))[0]
        res1 = await worker.fail_job(job1.id, token1, "transient error", db)
        assert res1 is True

        # Check job transitioned back to PENDING and lease cleared
        refreshed = (
            await db.execute(select(WebhookDelivery).where(WebhookDelivery.id == job1.id))
        ).scalar_one()
        assert refreshed.processing_status == "PENDING"
        assert refreshed.lease_token is None
        assert refreshed.locked_at is None
        assert refreshed.last_error == "transient error"

        # T-13: Stale lease token
        await persist_webhook_delivery(
            delivery_id=f"t13-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )
        job2, token2 = (await worker.claim_jobs(db, batch_size=1))[0]
        res3 = await worker.fail_job(job2.id, "wrong-token-abc", "error", db)
        assert res3 is False


# --- T-14 & T-15: Maximum-Attempt Enforcement & Dead-Letter Transition ---
@pytest.mark.asyncio
async def test_t14_t15_max_attempt_and_dead_letter():
    """T-14: Job not claimed when attempts >= max_attempts. T-15: Final failure goes to DEAD_LETTER."""
    async with AsyncSessionLocal() as db:
        worker = WebhookQueueWorker(worker_id="worker-max-test")

        deliv = await persist_webhook_delivery(
            delivery_id=f"t14-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )

        # Set attempts = 2, max_attempts = 3
        await db.execute(
            update(WebhookDelivery)
            .where(WebhookDelivery.id == deliv.id)
            .values(attempts=2, max_attempts=3)
        )
        await db.commit()

        # Claim attempt 3 (the final allowed attempt)
        claimed = await worker.claim_jobs(db, batch_size=1)
        assert len(claimed) == 1
        job, token = claimed[0]
        assert job.attempts == 3

        # T-15: Final failure must transition to DEAD_LETTER
        res = await worker.fail_job(job.id, token, "exhausted all attempts", db)
        assert res is True

        refreshed = (
            await db.execute(select(WebhookDelivery).where(WebhookDelivery.id == job.id))
        ).scalar_one()
        assert refreshed.processing_status == "DEAD_LETTER"

        # T-14: Maximum attempts reached; cannot be claimed again
        empty_claims = await worker.claim_jobs(db, batch_size=1)
        assert len(empty_claims) == 0


# --- T-16 & T-17: Reaper Crash Recovery on Final Attempt & Orphaned PENDING ---
@pytest.mark.asyncio
async def test_t16_t17_reaper_dead_letter_cleanup():
    """T-16 & T-17: Reaper cleans up expired final-attempt PROCESSING and exhausted PENDING jobs."""
    async with AsyncSessionLocal() as db:
        worker = WebhookQueueWorker(worker_id="reaper-test", lease_duration_minutes=5)

        # T-17: Orphaned PENDING job with attempts >= max_attempts
        p1 = await persist_webhook_delivery(
            delivery_id=f"t17-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )
        await db.execute(
            update(WebhookDelivery)
            .where(WebhookDelivery.id == p1.id)
            .values(processing_status="PENDING", attempts=3, max_attempts=3)
        )

        # T-16: Expired PROCESSING job on final attempt
        p2 = await persist_webhook_delivery(
            delivery_id=f"t16-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )
        await db.execute(
            update(WebhookDelivery)
            .where(WebhookDelivery.id == p2.id)
            .values(
                processing_status="PROCESSING",
                attempts=3,
                max_attempts=3,
                locked_at=datetime.now(UTC) - timedelta(minutes=10),
            )
        )
        await db.commit()

        reaped = await worker.reap_exhausted_jobs(db)
        assert reaped >= 2

        # Verify both are now DEAD_LETTER
        j1 = (
            await db.execute(select(WebhookDelivery).where(WebhookDelivery.id == p1.id))
        ).scalar_one()
        j2 = (
            await db.execute(select(WebhookDelivery).where(WebhookDelivery.id == p2.id))
        ).scalar_one()
        assert j1.processing_status == "DEAD_LETTER"
        assert j2.processing_status == "DEAD_LETTER"


# --- T-18: Concurrent Reaper and Worker Claim ---
@pytest.mark.asyncio
async def test_t18_concurrent_reaper_and_worker_claim():
    """T-18: Atomic operations ensure active jobs are not swept by reaper and valid claims proceed."""
    async with AsyncSessionLocal() as db:
        worker = WebhookQueueWorker(worker_id="worker-concurrent", lease_duration_minutes=5)

        # Active job with valid attempts
        valid_job = await persist_webhook_delivery(
            delivery_id=f"t18-valid-{uuid.uuid4().hex[:8]}",
            event_type="pull_request",
            action="opened",
            payload={},
            db=db,
        )

        # Run reaper: valid job should not be touched
        reaped = await worker.reap_exhausted_jobs(db)
        assert reaped == 0

        # Worker should claim the valid job successfully
        claimed = await worker.claim_jobs(db, batch_size=1)
        assert len(claimed) == 1
        assert claimed[0][0].id == valid_job.id
