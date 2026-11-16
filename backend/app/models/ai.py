"""AI Foundation Provider SQLAlchemy ORM Models.

Entities for managing primary/fallback LLM providers and operational telemetry.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, utc_now


class AIProviderConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Configuration settings for LLM providers (Google Gemini, OpenAI, Groq)."""

    __tablename__ = "ai_provider_configs"
    __table_args__ = (
        UniqueConstraint("provider_name", "model_name", name="uq_provider_model"),
    )

    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)

    # Relationships
    events: Mapped[List["AIProviderEvent"]] = relationship(
        "AIProviderEvent", back_populates="config", cascade="all, delete-orphan"
    )


class AIProviderEvent(Base, UUIDPrimaryKeyMixin):
    """Runtime telemetry tracking tokens, latency, timeouts, and fallback failovers."""

    __tablename__ = "ai_provider_events"

    config_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_provider_configs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    config: Mapped[Optional["AIProviderConfig"]] = relationship("AIProviderConfig", back_populates="events")

