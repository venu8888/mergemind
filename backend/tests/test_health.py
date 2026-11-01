"""Tests for health check endpoints."""

import pytest


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
async def test_api_v1_health_endpoint(async_client):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["project"] == "MergeMind"
    assert data["database"]["connected"] is True
    assert data["sandbox"]["mode"] in ["container", "disabled"]
    assert data["sandbox"]["timeout_seconds"] == 60
