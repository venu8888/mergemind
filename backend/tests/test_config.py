"""Unit tests for configuration loading and validation."""

from app.core.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.PROJECT_NAME == "MergeMind"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.SANDBOX_TIMEOUT_SECONDS == 60
    assert settings.SANDBOX_MAX_MEMORY_MB == 512
    assert settings.SCORING_POLICY_VERSION == "v1.0"


def test_cors_origin_parser():
    settings = Settings(CORS_ORIGINS="http://localhost:3000, https://app.example.com")
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "https://app.example.com" in settings.CORS_ORIGINS
