"""Pydantic schemas for System Health and Diagnostics."""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for system health response."""

    status: str = Field(..., json_schema_extra={"example": "healthy"})
    project: str = Field(..., json_schema_extra={"example": "MergeMind"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    database: dict[str, Any] = Field(
        ...,
        json_schema_extra={"example": {"connected": True, "engine": "sqlite"}},
    )
    sandbox: dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "example": {"mode": "container", "max_memory_mb": 512, "timeout_seconds": 60}
        },
    )
    timestamp: str = Field(..., json_schema_extra={"example": "2026-11-01T11:15:00Z"})
