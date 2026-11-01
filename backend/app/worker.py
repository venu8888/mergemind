"""Standalone durable webhook queue worker runner."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from app.core.database import AsyncSessionLocal
from app.services.github.dispatcher import WebhookDispatcher
from app.services.github.queue_worker import WebhookQueueWorker

logger = logging.getLogger("mergemind.worker")


async def run_worker_loop(
    poll_interval: float = 2.0,
    max_reap_interval: float = 60.0,
    stop_event: asyncio.Event | None = None,
):
    """Run the continuous webhook queue claiming and execution loop."""
    logger.info("Initializing MergeMind durable Webhook Queue Worker...")
    worker = WebhookQueueWorker()
    dispatcher = WebhookDispatcher(worker=worker)
    last_reap = 0.0

    logger.info("Worker loop started with worker_id: %s", worker.worker_id)
    while stop_event is None or not stop_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                processed = await dispatcher.process_one(db)

                # Periodically reap dead letters
                now = asyncio.get_event_loop().time()
                if now - last_reap > max_reap_interval:
                    reaped = await worker.reap_exhausted_jobs(db)
                    if reaped > 0:
                        logger.info("Reaped %d exhausted jobs into DEAD_LETTER", reaped)
                    last_reap = now

            if not processed:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            break
        except Exception as err:
            logger.error("Error in queue worker iteration: %s", err)
            await asyncio.sleep(poll_interval)

    logger.info("Worker loop terminated cleanly.")


def main():
    """Main entrypoint for standalone worker execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    stop_event = asyncio.Event()

    def _handle_signal():
        logger.info("Received termination signal; stopping worker loop...")
        stop_event.set()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(run_worker_loop(stop_event=stop_event))
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
    finally:
        loop.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
