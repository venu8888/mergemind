"""Pytest Test Configuration and Fixtures."""

import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

# Force testing environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_SYNC_URL"] = "sqlite:///:memory:"

from app.core.database import engine
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
async def setup_test_database():
    """Initializes in-memory test database tables before tests and cleans up after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def async_client():
    """Provides async HTTP client configured against the FastAPI ASGI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
