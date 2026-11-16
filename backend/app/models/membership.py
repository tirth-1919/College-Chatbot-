"""College Membership SQLAlchemy ORM Model.

Maps College Administrators to their assigned college tenant.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.models.college import College
    from app.models.user import User


class CollegeMembership(Base, UUIDPrimaryKeyMixin):
    """Enforces tenant-user mapping for college administration staff."""

    __tablename__ = "college_memberships"
    __table_args__ = (
        UniqueConstraint("college_id", "user_id", name="uq_college_user"),
    )

    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_in_college: Mapped[str] = mapped_column(
        PG_ENUM("ADMIN", "EDITOR", "VIEWER", name="membership_role", create_type=False),
        default="ADMIN",
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

