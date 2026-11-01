"""Tests for health check endpoints."""

from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints import health as health_module


@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MergeMind"
    assert "version" in data
    assert data["health_url"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_healthz_endpoint(async_client):
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_api_v1_health_endpoint_healthy(async_client):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["project"] == "MergeMind"
    assert data["database"]["connected"] is True
    assert data["sandbox"]["mode"] in ["container", "disabled"]
    assert data["sandbox"]["timeout_seconds"] == 60


@pytest.mark.asyncio
async def test_api_v1_health_endpoint_degraded_on_db_failure(async_client, monkeypatch):
    """Verifies that health check reports 'degraded' when database check returns False."""
    monkeypatch.setattr(health_module, "check_db_connection", AsyncMock(return_value=False))

    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"]["connected"] is False
