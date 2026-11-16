"""College Registration, Onboarding & Invitations Repository."""

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, update, desc, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.college import College
from app.models.user import User
from app.models.audit import AuditLog
from app.models.registration import (
    CollegeRegistration,
    RegistrationReview,
    CollegeAdminInvitation,
    CollegeOnboardingProgress,
    NotificationLog,
)
from app.repositories.user_repository import UserRepository
from app.security.password import hash_password
from app.database.session import set_rls_context
from app.services.notification_service import NotificationService
from app.core.logging import logger


class RegistrationRepository:
    """Handles persistence, workflow state machines, and transactional approvals."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repository = UserRepository(session)
        self.notifications = NotificationService(session)

    # --------------------------------------------------------------------------
    # 1. Registration Intake & Status Checking
    # --------------------------------------------------------------------------

    async def get_by_id(self, registration_id: uuid.UUID) -> Optional[CollegeRegistration]:
        """Fetches a single registration record by UUID."""
        stmt = select(CollegeRegistration).where(CollegeRegistration.id == registration_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_tracking_code(self, code: str) -> Optional[CollegeRegistration]:
        """Looks up the public status view with an opaque tracking code."""
        result = await self.session.execute(
            text("SELECT public.get_public_registration_status(:tracking_code)"),
            {"tracking_code": code.strip()},
        )
        row = result.scalar_one_or_none()
        return SimpleNamespace(**row) if row else None

    async def find_by_query(self, query_str: str) -> Optional[CollegeRegistration]:
        """Searches registrations for an already-authorized administrative workflow."""
        clean = query_str.strip().lower()
        stmt = select(CollegeRegistration).where(
            or_(
                CollegeRegistration.tracking_code.ilike(clean),
                CollegeRegistration.slug == clean,
                CollegeRegistration.official_domain == clean,
                CollegeRegistration.contact_email.ilike(clean),
                CollegeRegistration.initial_admin_email.ilike(clean),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[CollegeRegistration]:
        """Finds registration by slug."""
        stmt = select(CollegeRegistration).where(CollegeRegistration.slug == slug.strip().lower())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_domain(self, domain: str) -> Optional[CollegeRegistration]:
        """Finds registration by official domain."""
        stmt = select(CollegeRegistration).where(CollegeRegistration.official_domain == domain.strip().lower())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_registrations(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CollegeRegistration]:
        """Lists registrations with optional status filtering."""
        stmt = select(CollegeRegistration).order_by(desc(CollegeRegistration.created_at))
        if status and status.upper() != "ALL":
            stmt = stmt.where(CollegeRegistration.status == status.upper())
        stmt = stmt.limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_reviews_for_registration(
        self, registration_id: uuid.UUID
    ) -> List[RegistrationReview]:
        """Fetches all review audit trail records for a registration."""
        stmt = (
            select(RegistrationReview)
            .where(RegistrationReview.registration_id == registration_id)
            .order_by(desc(RegistrationReview.created_at))
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_registration(
        self,
        college_name: str,
        slug: str,
        official_domain: str,
        official_email: str,
        contact_person_name: str,
        contact_person_email: str,
        college_code: Optional[str] = None,
        contact_phone: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: str = "India",
        description: Optional[str] = None,
        accreditation_details: Optional[str] = None,
        website_url: Optional[str] = None,
        logo_url: Optional[str] = None,
        supporting_documents: Optional[List[Dict[str, Any]]] = None,
        initial_admin_name: Optional[str] = None,
        initial_admin_email: Optional[str] = None,
        initial_admin_designation: str = "College Administrator",
        submitted_by_user_id: Optional[uuid.UUID] = None,
    ) -> CollegeRegistration:
        """Creates a pending application through the narrow database intake function."""
        clean_slug = slug.strip().lower()
        clean_domain = official_domain.strip().lower()
        payload = {
            "college_name": college_name.strip(),
            "college_code": college_code.strip() if college_code else None,
            "slug": clean_slug,
            "official_domain": clean_domain,
            "official_email": official_email.strip().lower(),
            "contact_phone": contact_phone.strip() if contact_phone else None,
            "contact_person_name": contact_person_name.strip(),
            "contact_person_email": contact_person_email.strip().lower(),
            "address": address.strip() if address else None,
            "city": city.strip() if city else None,
            "state": state.strip() if state else None,
            "country": country.strip() if country else "India",
            "description": description.strip() if description else None,
            "accreditation_details": accreditation_details.strip() if accreditation_details else None,
            "website_url": website_url.strip() if website_url else None,
            "logo_url": logo_url.strip() if logo_url else None,
            "supporting_documents": supporting_documents or [],
            "initial_admin_name": initial_admin_name.strip() if initial_admin_name else contact_person_name.strip(),
            "initial_admin_email": initial_admin_email.strip().lower() if initial_admin_email else contact_person_email.strip().lower(),
            "initial_admin_designation": initial_admin_designation,
        }
        result = await self.session.execute(
            text(
                "SELECT registration_id, college_id, tracking_code, created_at "
                "FROM public.submit_public_college_registration(CAST(:payload AS jsonb))"
            ),
            {"payload": json.dumps(payload)},
        )
        row = result.mappings().one()
        now = row["created_at"]
        reg = SimpleNamespace(
            id=row["registration_id"],
            college_id=row["college_id"],
            tracking_code=row["tracking_code"],
            status="PENDING",
            college_name=payload["college_name"],
            college_code=payload["college_code"],
            slug=clean_slug,
            official_domain=clean_domain,
            contact_email=payload["official_email"],
            contact_phone=payload["contact_phone"],
            contact_person_name=payload["contact_person_name"],
            contact_person_email=payload["contact_person_email"],
            address=payload["address"],
            city=payload["city"],
            state=payload["state"],
            country=payload["country"],
            description=payload["description"],
            accreditation_details=payload["accreditation_details"],
            website_url=payload["website_url"],
            logo_url=payload["logo_url"],
            supporting_documents=payload["supporting_documents"],
            initial_admin_name=payload["initial_admin_name"],
            initial_admin_email=payload["initial_admin_email"],
            initial_admin_designation=payload["initial_admin_designation"],
            created_at=now,
            updated_at=now,
        )

        # Notification dispatch
        await self.notifications.notify_registration_submitted(
            recipient_email=reg.contact_person_email,
            college_name=reg.college_name,
            tracking_code=reg.tracking_code,
            college_id=reg.college_id,
        )

        return reg

    # --------------------------------------------------------------------------
    # 2. Super Admin Decision Actions
    # --------------------------------------------------------------------------

    async def request_additional_information(
        self,
        registration_id: uuid.UUID,
        reviewer_admin_id: uuid.UUID,
        prompt: str,
        comments: Optional[str] = None,
    ) -> Optional[CollegeRegistration]:
        """Transitions registration to ADDITIONAL_INFORMATION_REQUIRED."""
        reg = await self.get_by_id(registration_id)
        if not reg:
            return None

        prev_status = reg.status
        reg.status = "ADDITIONAL_INFORMATION_REQUIRED"
        reg.additional_info_requested = prompt
        reg.reviewed_by_admin_id = reviewer_admin_id
        reg.reviewed_at = datetime.utcnow()
        reg.review_comments = comments or prompt
        reg.updated_at = datetime.utcnow()

        review = RegistrationReview(
            id=uuid.uuid4(),
            registration_id=reg.id,
            reviewer_user_id=reviewer_admin_id,
            previous_status=prev_status,
            new_status="ADDITIONAL_INFORMATION_REQUIRED",
            comments=f"Requested info: {prompt}. Remarks: {comments or 'None'}",
            action_type="REQUEST_INFO",
            created_at=datetime.utcnow(),
        )
        self.session.add(review)
        await self.session.flush()

        # Notify applicant
        await self.notifications.notify_additional_info_requested(
            recipient_email=reg.contact_person_email,
            college_name=reg.college_name,
            tracking_code=reg.tracking_code,
            prompt=prompt,
        )

        return reg

    async def submit_additional_information(
        self,
        tracking_code: str,
        response_text: str,
        additional_docs: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[CollegeRegistration]:
        """Applicant responds to information request; transitions status back to UNDER_REVIEW."""
        result = await self.session.execute(
            text(
                "SELECT public.submit_public_registration_information("
                ":tracking_code, :response, CAST(:documents AS jsonb))"
            ),
            {
                "tracking_code": tracking_code.strip(),
                "response": response_text,
                "documents": json.dumps(additional_docs or []),
            },
        )
        row = result.scalar_one_or_none()
        return SimpleNamespace(**row) if row else None

    async def reject_registration(
        self,
        registration_id: uuid.UUID,
        reviewer_admin_id: uuid.UUID,
        reason: Optional[str] = None,
    ) -> Optional[CollegeRegistration]:
        """Rejects the registration application."""
        reg = await self.get_by_id(registration_id)
        if not reg:
            return None

        prev_status = reg.status
        reg.status = "REJECTED"
        reg.reviewed_by_admin_id = reviewer_admin_id
        reg.reviewed_at = datetime.utcnow()
        reg.review_comments = reason or "Verification criteria could not be satisfied."
        reg.updated_at = datetime.utcnow()

        review = RegistrationReview(
            id=uuid.uuid4(),
            registration_id=reg.id,
            reviewer_user_id=reviewer_admin_id,
            previous_status=prev_status,
            new_status="REJECTED",
            comments=f"Application rejected. Reason: {reason or 'Not specified'}",
            action_type="REJECTED",
            created_at=datetime.utcnow(),
        )
        self.session.add(review)
        await self.session.flush()

        # Notify applicant
        await self.notifications.notify_registration_rejected(
            recipient_email=reg.contact_person_email,
            college_name=reg.college_name,
            tracking_code=reg.tracking_code,
            reason=reason,
        )

        return reg

    # --------------------------------------------------------------------------
    # 3. Transactional College Creation & Approval
    # --------------------------------------------------------------------------

    async def approve_registration_transactional(
        self,
        registration_id: uuid.UUID,
        reviewer_admin_id: uuid.UUID,
        comments: Optional[str] = None,
    ) -> Tuple[Optional[CollegeRegistration], Optional[College]]:
        """Approves a college and sends an invitation instead of activating an admin."""
        result = await self.session.execute(
            select(CollegeRegistration)
            .where(CollegeRegistration.id == registration_id)
            .with_for_update()
        )
        reg = result.scalar_one_or_none()
        if not reg:
            return None, None

        if reg.status == "APPROVED" and reg.college_id:
            existing_college = await self.session.get(College, reg.college_id)
            if existing_college:
                return reg, existing_college

        prev_status = reg.status
        now = datetime.now(timezone.utc)
        college = await self.session.get(College, reg.college_id) if reg.college_id else None
        if college is None:
            college = College(
                id=uuid.uuid4(),
                name=reg.college_name,
                slug=reg.slug,
                official_domain=reg.official_domain,
                logo_url=reg.logo_url,
                contact_email=reg.contact_email,
                contact_phone=reg.contact_phone,
                status="PENDING",
                is_active=False,
                created_at=now,
                updated_at=now,
            )
            self.session.add(college)
            await self.session.flush()

        college.status = "APPROVED"
        college.is_active = True
        college.updated_at = now
        reg.status = "APPROVED"
        reg.college_id = college.id
        reg.reviewed_by_admin_id = reviewer_admin_id
        reg.reviewed_at = now
        reg.review_comments = comments or "Application verified and approved."
        reg.updated_at = now

        review = RegistrationReview(
            id=uuid.uuid4(),
            registration_id=reg.id,
            reviewer_user_id=reviewer_admin_id,
            previous_status=prev_status,
            new_status="APPROVED",
            comments=f"Approved tenant. Assigned college UUID: {college.id}. Remarks: {comments or 'Approved'}",
            action_type="APPROVED",
            created_at=now,
        )
        self.session.add(review)

        if reg.initial_admin_email:
            await self.create_invitation(
                college_id=college.id,
                invited_by_user_id=reviewer_admin_id,
                email=reg.initial_admin_email,
                full_name=reg.initial_admin_name or "College Administrator",
                role_in_college="ADMIN",
            )

        onboarding = CollegeOnboardingProgress(
            id=uuid.uuid4(),
            college_id=college.id,
            current_step=1,
            is_approved=True,
            admin_assigned=False,
            profile_completed=False,
            website_configured=False,
            documents_uploaded=False,
            knowledge_ready=False,
            is_completed=False,
            step_data={
                "college_name": reg.college_name,
                "domain": reg.official_domain,
                "city": reg.city,
                "state": reg.state,
                "website_url": reg.website_url,
            },
            created_at=now,
            updated_at=now,
        )
        self.session.add(onboarding)

        audit_log = AuditLog(
            id=uuid.uuid4(),
            college_id=college.id,
            actor_user_id=reviewer_admin_id,
            action_type="COLLEGE_APPROVED",
            target_entity="colleges",
            target_id=college.id,
            payload_diff={
                "registration_id": str(reg.id),
                "college_name": reg.college_name,
                "slug": reg.slug,
                "admin_email": reg.initial_admin_email,
            },
            created_at=now,
        )
        self.session.add(audit_log)

        await self.session.flush()

        target_email = reg.initial_admin_email or reg.contact_person_email
        await self.notifications.notify_registration_approved(
            recipient_email=target_email,
            college_name=reg.college_name,
            college_id=college.id,
        )

        return reg, college

    # --------------------------------------------------------------------------
    # 4. College Admin Invitations
    # --------------------------------------------------------------------------

    async def create_invitation(
        self,
        college_id: uuid.UUID,
        invited_by_user_id: uuid.UUID,
        email: str,
        full_name: str,
        role_in_college: str = "ADMIN",
        expires_in_days: int = 7,
    ) -> CollegeAdminInvitation:
        """Issues a cryptographically secure administrator invitation token."""
        if role_in_college not in {"ADMIN", "EDITOR", "VIEWER"}:
            raise ValueError("Unsupported college invitation role.")
        clean_email = email.strip().lower()
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        college = await self.session.get(College, college_id)
        if not college or college.status != "APPROVED" or not college.is_active:
            raise ValueError("Administrator invitations require an approved, active college.")

        invite = CollegeAdminInvitation(
            id=uuid.uuid4(),
            college_id=college_id,
            invited_by_user_id=invited_by_user_id,
            email=clean_email,
            full_name=full_name.strip(),
            role_in_college=role_in_college,
            invitation_token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            status="PENDING",
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(invite)
        await self.session.flush()

        # Fetch college name for notification
        stmt_c = select(College.name).where(College.id == college_id)
        res_c = await self.session.execute(stmt_c)
        college_name = res_c.scalar() or "College Institution"

        await self.notifications.notify_admin_invitation(
            recipient_email=clean_email,
            full_name=full_name.strip(),
            college_name=college_name,
            invitation_token=token,
            college_id=college_id,
        )

        return invite

    async def get_invitation_by_token(self, token: str) -> Optional[CollegeAdminInvitation]:
        """Resolves an invitation without returning its stored token hash."""
        result = await self.session.execute(
            text(
                "SELECT * FROM public.lookup_college_invitation_by_token(:token)"
            ),
            {"token": token.strip()},
        )
        row = result.mappings().first()
        return SimpleNamespace(**row) if row else None

    async def list_invitations(
        self, college_id: Optional[uuid.UUID] = None
    ) -> List[CollegeAdminInvitation]:
        """Lists invitations for a specific college or all."""
        stmt = select(CollegeAdminInvitation).order_by(desc(CollegeAdminInvitation.created_at))
        if college_id:
            stmt = stmt.where(CollegeAdminInvitation.college_id == college_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def revoke_invitation(self, invitation_id: uuid.UUID) -> bool:
        """Revokes a pending invitation."""
        stmt = select(CollegeAdminInvitation).where(CollegeAdminInvitation.id == invitation_id)
        res = await self.session.execute(stmt)
        invite = res.scalar_one_or_none()
        if not invite or invite.status != "PENDING":
            return False

        invite.status = "REVOKED"
        invite.updated_at = datetime.utcnow()
        await self.session.flush()
        return True

    async def resend_invitation(self, invitation_id: uuid.UUID) -> Optional[CollegeAdminInvitation]:
        """Rotates the bearer token before resending so plaintext is never stored."""
        stmt = select(CollegeAdminInvitation).where(CollegeAdminInvitation.id == invitation_id)
        res = await self.session.execute(stmt)
        invite = res.scalar_one_or_none()
        if not invite or invite.status != "PENDING":
            return None

        token = secrets.token_urlsafe(32)
        invite.invitation_token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        invite.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        invite.updated_at = datetime.utcnow()

        stmt_c = select(College.name).where(College.id == invite.college_id)
        res_c = await self.session.execute(stmt_c)
        college_name = res_c.scalar() or "College Institution"

        await self.notifications.notify_admin_invitation(
            recipient_email=invite.email,
            full_name=invite.full_name,
            college_name=college_name,
            invitation_token=token,
            college_id=invite.college_id,
        )
        await self.session.flush()
        return invite

    async def accept_invitation(
        self,
        token: str,
        full_name: str,
        password: Optional[str],
        authenticated_user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[bool, str, Optional[User], Optional[uuid.UUID], bool]:
        """Atomically accepts an invitation and lets the database enforce its lifecycle."""
        result = await self.session.execute(
            text(
                "SELECT * FROM public.accept_college_admin_invitation("
                ":token, :full_name, :password_hash, :authenticated_user_id)"
            ),
            {
                "token": token.strip(),
                "full_name": full_name.strip(),
                "password_hash": (
                    hash_password(password)
                    if authenticated_user_id is None and password is not None
                    else None
                ),
                "authenticated_user_id": authenticated_user_id,
            },
        )
        accepted = result.mappings().one_or_none()
        if not accepted:
            return False, "Invitation could not be accepted.", None, None, False

        await set_rls_context(
            self.session,
            college_id=accepted["accepted_college_id"],
            user_id=accepted["accepted_user_id"],
            is_super_admin=False,
        )
        user = await self.user_repository.get_by_id(accepted["accepted_user_id"])
        if not user:
            raise RuntimeError("Accepted invitation did not produce an accessible user account.")
        await self.session.refresh(user)
        return (
            True,
            "Invitation accepted successfully.",
            user,
            accepted["accepted_college_id"],
            accepted["is_existing_user"],
        )

    # --------------------------------------------------------------------------
    # 5. Onboarding Progress Tracking
    # --------------------------------------------------------------------------

    async def get_or_create_onboarding_progress(
        self, college_id: uuid.UUID
    ) -> CollegeOnboardingProgress:
        """Resolves or initializes onboarding tracking state for an institution."""
        stmt = select(CollegeOnboardingProgress).where(
            CollegeOnboardingProgress.college_id == college_id
        )
        res = await self.session.execute(stmt)
        progress = res.scalar_one_or_none()

        if not progress:
            progress = CollegeOnboardingProgress(
                id=uuid.uuid4(),
                college_id=college_id,
                current_step=1,
                is_approved=True,
                admin_assigned=True,
                profile_completed=False,
                website_configured=False,
                documents_uploaded=False,
                knowledge_ready=False,
                is_completed=False,
                step_data={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.session.add(progress)
            await self.session.flush()

        return progress

    async def update_onboarding_progress(
        self,
        college_id: uuid.UUID,
        current_step: Optional[int] = None,
        profile_completed: Optional[bool] = None,
        website_configured: Optional[bool] = None,
        documents_uploaded: Optional[bool] = None,
        knowledge_ready: Optional[bool] = None,
        step_data: Optional[Dict[str, Any]] = None,
    ) -> CollegeOnboardingProgress:
        """Updates progress milestones and custom step data."""
        progress = await self.get_or_create_onboarding_progress(college_id)

        if current_step is not None:
            progress.current_step = current_step
        if profile_completed is not None:
            progress.profile_completed = profile_completed
        if website_configured is not None:
            progress.website_configured = website_configured
        if documents_uploaded is not None:
            progress.documents_uploaded = documents_uploaded
        if knowledge_ready is not None:
            progress.knowledge_ready = knowledge_ready
        if step_data is not None:
            current_data = dict(progress.step_data or {})
            current_data.update(step_data)
            progress.step_data = current_data

        progress.updated_at = datetime.utcnow()
        await self.session.flush()
        return progress

    async def complete_onboarding(
        self, college_id: uuid.UUID, admin_email: Optional[str] = None
    ) -> CollegeOnboardingProgress:
        """Marks institutional onboarding as completed."""
        progress = await self.get_or_create_onboarding_progress(college_id)
        progress.is_completed = True
        progress.current_step = 6
        progress.completed_at = datetime.utcnow()
        progress.updated_at = datetime.utcnow()
        await self.session.flush()

        # Fetch college details for notification
        stmt_c = select(College).where(College.id == college_id)
        res_c = await self.session.execute(stmt_c)
        college = res_c.scalar_one_or_none()

        if college:
            recipient = admin_email or college.contact_email
            await self.notifications.notify_onboarding_completed(
                recipient_email=recipient,
                college_name=college.name,
                college_id=college_id,
            )

        return progress

