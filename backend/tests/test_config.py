"""Unit tests for configuration loading and validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.PROJECT_NAME == "MergeMind"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.SANDBOX_TIMEOUT_SECONDS == 60
    assert settings.SANDBOX_MAX_MEMORY_MB == 512
    assert settings.SCORING_POLICY_VERSION == "v1.0"


def test_cors_origin_parser_list_and_string():
    settings_str = Settings(CORS_ORIGINS="http://localhost:3000, https://app.example.com")
    assert "http://localhost:3000" in settings_str.CORS_ORIGINS
    assert "https://app.example.com" in settings_str.CORS_ORIGINS

    settings_list = Settings(CORS_ORIGINS=["http://localhost:4000"])
    assert settings_list.CORS_ORIGINS == ["http://localhost:4000"]


def test_invalid_sandbox_type_rejected():
    with pytest.raises(ValidationError):
        Settings(SANDBOX_TYPE="insecure_host_runner")


def test_sandbox_resource_boundary_validation():
    # Timeout must be between 5 and 300 seconds
    with pytest.raises(ValidationError):
        Settings(SANDBOX_TIMEOUT_SECONDS=1)

    with pytest.raises(ValidationError):
        Settings(SANDBOX_TIMEOUT_SECONDS=600)

    # Memory must be between 64 and 2048 MB
    with pytest.raises(ValidationError):
        Settings(SANDBOX_MAX_MEMORY_MB=32)
