"""API v1 Central Router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, repositories, webhooks

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["Repositories"])
