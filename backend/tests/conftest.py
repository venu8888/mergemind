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
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_mergemind.db"
os.environ["DATABASE_SYNC_URL"] = "sqlite:///./test_mergemind.db"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-webhook-secret-key-12345"

from app.core.config import settings

settings.GITHUB_WEBHOOK_SECRET = "test-webhook-secret-key-12345"
settings.API_KEY = "test-api-key-12345"

from app.core.database import engine
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
async def setup_test_database():
    """Initializes test database tables once and truncates rows between tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Removes temporary test sqlite database file upon test session start and completion."""
    for db_file in [Path("./test_mergemind.db"), Path("backend/test_mergemind.db")]:
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception:
                pass
    yield
    try:
        engine.sync_engine.dispose()
    except Exception:
        pass
    for db_file in [Path("./test_mergemind.db"), Path("backend/test_mergemind.db")]:
        if db_file.exists():
            try:
                db_file.unlink()
            except Exception:
                pass


@pytest.fixture
async def async_client():
    """Provides async HTTP client configured against the FastAPI ASGI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
