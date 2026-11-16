"""Database Declarative Base and Common Mixins.

Defines SQLAlchemy 2.0 DeclarativeBase, UUIDPrimaryKeyMixin, and TimestampMixin.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Returns current UTC timestamp with timezone awareness."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 ORM models."""
    pass


class UUIDPrimaryKeyMixin:
    """Mixin that injects a UUID v4 primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique primary key identifier (UUID v4)",
    )


class TimestampMixin:
    """Mixin that injects created_at and updated_at UTC timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="Record creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        doc="Record last updated timestamp (UTC)",
    )

