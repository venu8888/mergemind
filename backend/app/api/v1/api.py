"""API v1 Central Router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    health_assessment,
    repositories,
    verification,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
api_router.include_router(
    health_assessment.router, prefix="/repositories", tags=["Repository Health"]
)
api_router.include_router(verification.router, prefix="/repositories", tags=["PR Verification"])
