"""College Registration, Onboarding Progress & Governance Models.

Represents Phase 6 institutional onboarding workflows, multi-step review stages,
admin invitation lifecycle, and notification compliance logging.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.college import College
    from app.models.user import User


class CollegeRegistration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pending institutional registration application submitted by college representatives."""

    __tablename__ = "college_registrations"

    college_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("colleges.id", ondelete="SET NULL"), nullable=True, index=True
    )
    college_name: Mapped[str] = mapped_column(String(255), nullable=False)
    college_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    official_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_person_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person_email: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accreditation_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supporting_documents: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    status: Mapped[str] = mapped_column(
        PG_ENUM(
            "PENDING",
            "UNDER_REVIEW",
            "APPROVED",
            "REJECTED",
            "ADDITIONAL_INFORMATION_REQUIRED",
            name="registration_status",
            create_type=False,
        ),
        default="PENDING",
        nullable=False,
        index=True,
    )
    tracking_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Initial Designated Admin
    initial_admin_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    initial_admin_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    initial_admin_designation: Mapped[Optional[str]] = mapped_column(
        String(100), default="College Administrator", nullable=True
    )

    # Reviewer & Governance Metadata
    submitted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_info_requested: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    additional_info_submitted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    reviews: Mapped[List["RegistrationReview"]] = relationship(
        "RegistrationReview", back_populates="registration", cascade="all, delete-orphan"
    )


class RegistrationReview(Base, UUIDPrimaryKeyMixin):
    """Audit trail of reviewer decisions, remarks, and state transitions."""

    __tablename__ = "registration_reviews"

    registration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("college_registrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_status: Mapped[str] = mapped_column(
        PG_ENUM(
            "PENDING",
            "UNDER_REVIEW",
            "APPROVED",
            "REJECTED",
            "ADDITIONAL_INFORMATION_REQUIRED",
            name="registration_status",
            create_type=False,
        ),
        nullable=False,
    )
    new_status: Mapped[str] = mapped_column(
        PG_ENUM(
            "PENDING",
            "UNDER_REVIEW",
            "APPROVED",
            "REJECTED",
            "ADDITIONAL_INFORMATION_REQUIRED",
            name="registration_status",
            create_type=False,
        ),
        nullable=False,
    )
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    registration: Mapped["CollegeRegistration"] = relationship(
        "CollegeRegistration", back_populates="reviews"
    )


class CollegeAdminInvitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Hashed one-time invitation token for college membership activation."""

    __tablename__ = "college_admin_invitations"

    college_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_in_college: Mapped[str] = mapped_column(
        PG_ENUM("ADMIN", "EDITOR", "VIEWER", name="membership_role", create_type=False),
        default="ADMIN",
        nullable=False,
    )
    invitation_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        PG_ENUM("PENDING", "ACCEPTED", "EXPIRED", "REVOKED", name="invitation_status", create_type=False),
        default="PENDING",
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CollegeOnboardingProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Multi-step onboarding wizard progression state for College Administrators."""

    __tablename__ = "college_onboarding_progress"

    college_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    current_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    admin_assigned: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    website_configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    documents_uploaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    knowledge_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    step_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationLog(Base, UUIDPrimaryKeyMixin):
    """Audit log for platform email and system notifications."""

    __tablename__ = "notification_logs"

    college_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("colleges.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_status: Mapped[str] = mapped_column(
        PG_ENUM("QUEUED", "SENT", "SIMULATED", "FAILED", name="notification_delivery_status", create_type=False),
        default="QUEUED",
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

