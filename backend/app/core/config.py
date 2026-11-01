"""MergeMind Core Configuration.

Loads environment variables via Pydantic Settings with strong typing,
sensible defaults, and production security validations.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General App Config
    PROJECT_NAME: str = "MergeMind"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = False
    API_KEY: str = Field(
        default="mergemind-dev-insecure-key",
        description="Pre-shared API key for authenticated API endpoints in local development",
    )

    # CORS Configuration
    CORS_ORIGINS: list[str] | str = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./mergemind.db",
        description="Async SQLAlchemy database connection string",
    )
    DATABASE_SYNC_URL: str = Field(
        default="sqlite:///./mergemind.db",
        description="Sync SQLAlchemy database connection string for migrations",
    )
    DB_ECHO_SQL: bool = False

    # GitHub App Integration Settings
    GITHUB_APP_ID: str = Field(default="", description="GitHub App ID")
    GITHUB_APP_PRIVATE_KEY_PATH: str = Field(default="", description="Path to PEM private key")
    GITHUB_WEBHOOK_SECRET: str = Field(default="", description="HMAC-SHA256 Webhook Secret")

    # Execution Sandbox Settings
    SANDBOX_TYPE: Literal["container", "disabled"] = Field(
        default="container",
        description="Runner mode: container for ephemeral sandbox, disabled to fail-closed",
    )
    SANDBOX_TIMEOUT_SECONDS: int = Field(default=60, ge=5, le=60)
    SANDBOX_MAX_MEMORY_MB: int = Field(default=512, ge=64, le=2048)
    SANDBOX_CPU_QUOTA: float = Field(default=1.0, ge=0.25, le=4.0)

    # Durable Webhook Queue Worker
    ENABLE_IN_PROCESS_WORKER: bool = Field(
        default=False,
        description="Whether to run the durable webhook queue worker loop inside the web process",
    )

    # Quality Gate & Scoring Engine
    SCORING_POLICY_VERSION: str = "v1.0"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: any) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list | str):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
