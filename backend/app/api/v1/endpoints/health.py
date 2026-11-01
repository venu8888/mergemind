"""Health and Diagnostic Endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, status

from app.core.config import settings
from app.core.database import check_db_connection
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    description="Returns API service status, database connectivity, and runner configuration.",
)
async def get_health() -> HealthResponse:
    db_ok = await check_db_connection()
    overall_status = "healthy" if db_ok else "degraded"

    return HealthResponse(
        status=overall_status,
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database={
            "connected": db_ok,
            "url_driver": settings.DATABASE_URL.split("://")[0],
        },
        sandbox={
            "mode": settings.SANDBOX_TYPE,
            "max_memory_mb": settings.SANDBOX_MAX_MEMORY_MB,
            "timeout_seconds": settings.SANDBOX_TIMEOUT_SECONDS,
            "cpu_quota": settings.SANDBOX_CPU_QUOTA,
        },
        timestamp=datetime.now(UTC).isoformat(),
    )
