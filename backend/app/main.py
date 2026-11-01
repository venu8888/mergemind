"""MergeMind Backend Application Entrypoint."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import check_db_connection
from app.worker import run_worker_loop

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mergemind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown procedures."""
    logger.info(
        f"Initializing {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]"
    )
    db_ok = await check_db_connection()
    if db_ok:
        logger.info("Database connection successfully established.")
    else:
        logger.warning("Database connection failed or not yet reachable.")

    # Start in-process queue worker if explicitly enabled
    worker_task = None
    worker_stop = asyncio.Event()
    if settings.ENABLE_IN_PROCESS_WORKER:
        logger.info("Starting in-process background webhook queue worker...")
        worker_task = asyncio.create_task(
            run_worker_loop(poll_interval=2.0, stop_event=worker_stop)
        )

    yield

    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    if worker_task:
        logger.info("Stopping in-process queue worker task...")
        worker_stop.set()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MergeMind: Intelligent Repository Health, Pull Request Verification and Automated Remediation Platform",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/healthz", tags=["Health"], summary="Liveness Probe")
async def healthz():
    """Liveness probe for orchestrators and container health monitoring."""
    return {"status": "ok"}


@app.get("/", tags=["Root"], summary="Root Endpoint")
async def root():
    """Welcome endpoint providing service metadata."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_PREFIX}/docs",
        "health_url": f"{settings.API_V1_PREFIX}/health",
    }
