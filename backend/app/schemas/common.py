"""Common API Response and Health Schemas."""

from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standardized top-level API response envelope."""

    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    """System health check payload."""

    status: str = "healthy"
    service: str = "AI FAQ College Chat Bot Backend"
    environment: str
    version: str = "1.0.0"
    database_connected: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReadinessResponse(BaseModel):
    """Detailed production readiness check payload."""

    status: str = "ready"
    service: str = "AI FAQ College Chat Bot Backend"
    environment: str
    version: str = "1.0.0"
    checks: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponse(BaseModel):
    """Standard error response payload."""

    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

