"""Notification and Email Dispatch Service.

Handles multi-channel communication for Phase 6 institutional onboarding workflows,
compliance audits, and administrator invitations with delivery telemetry.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.registration import NotificationLog
from app.core.logging import logger
from app.core.config import settings
from app.services.email_transport import EmailDeliveryError, EmailTransport, SMTPEmailTransport
from urllib.parse import urlencode


class NotificationService:
    """Enterprise notification orchestrator with fallback telemetry and DB audit logging."""

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        email_transport: Optional[EmailTransport] = None,
    ):
        self.session = session
        self.email_transport, self.transport_configuration_error = (
            (email_transport, None) if email_transport is not None else self._configured_transport()
        )

    @staticmethod
    def _configured_transport() -> tuple[Optional[EmailTransport], Optional[str]]:
        if not settings.SMTP_HOST and not settings.SMTP_FROM_EMAIL:
            return None, "Email transport is not configured."
        if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
            return None, "SMTP configuration is incomplete."
        if bool(settings.SMTP_USERNAME) != bool(settings.SMTP_PASSWORD):
            return None, "SMTP authentication configuration is incomplete."
        if settings.ENVIRONMENT.strip().lower() in {"production", "prod"} and not settings.SMTP_STARTTLS:
            return None, "Production SMTP delivery requires STARTTLS."
        return (
            SMTPEmailTransport(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                from_email=str(settings.SMTP_FROM_EMAIL),
                username=settings.SMTP_USERNAME,
                password=(
                    settings.SMTP_PASSWORD.get_secret_value()
                    if settings.SMTP_PASSWORD is not None
                    else None
                ),
                starttls=settings.SMTP_STARTTLS,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            ),
            None,
        )

    async def send_notification(
        self,
        recipient_email: str,
        event_type: str,
        subject: str,
        content: str,
        college_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        audit_content: Optional[str] = None,
    ) -> NotificationLog:
        """Dispatches an institutional notification and logs compliance audit.

        SENT means the configured transport accepted the message. No configured
        transport or a transport failure is recorded as FAILED.
        """
        meta = metadata or {}
        delivery_status = "FAILED"
        error_message: Optional[str] = None

        if self.email_transport is None:
            error_message = self.transport_configuration_error or "Email transport is not configured."
            logger.warning("[NOTIFICATION] Delivery unavailable for event %s", event_type)
        else:
            try:
                await asyncio.wait_for(
                    self.email_transport.send_email(recipient_email, subject, content),
                    timeout=settings.EMAIL_DELIVERY_TIMEOUT_SECONDS,
                )
                delivery_status = "SENT"
                logger.info("[NOTIFICATION] Transport accepted email for event %s", event_type)
            except (EmailDeliveryError, OSError, TimeoutError) as exc:
                error_message = (
                    "Email transport timed out."
                    if isinstance(exc, TimeoutError)
                    else "Email transport failed to accept the message."
                )
                logger.warning("[NOTIFICATION] Delivery failed for event %s", event_type)

        log_entry = NotificationLog(
            id=uuid.uuid4(),
            college_id=college_id,
            recipient_email=recipient_email,
            event_type=event_type,
            subject=subject,
            content=audit_content if audit_content is not None else content,
            delivery_status=delivery_status,
            error_message=error_message,
            metadata_=meta,
            created_at=datetime.now(timezone.utc),
        )

        if self.session:
            self.session.add(log_entry)
            await self.session.flush()

        return log_entry

    # --------------------------------------------------------------------------
    # Specialized Workflow Notification Dispatchers
    # --------------------------------------------------------------------------

    async def notify_registration_submitted(
        self,
        recipient_email: str,
        college_name: str,
        tracking_code: str,
        college_id: Optional[uuid.UUID] = None,
    ) -> NotificationLog:
        """Notifies college representative that their registration has been received."""
        subject = f"CampusAI Application Received: {college_name}"
        content = (
            f"Dear Representative of {college_name},\n\n"
            f"Thank you for applying to onboard {college_name} onto CampusAI.\n"
            f"Your application tracking code is: {tracking_code}\n\n"
            f"Current Status: PENDING SUPER ADMIN VERIFICATION\n"
            f"Our compliance team will review your institutional credentials and official domain.\n\n"
            f"You can track your application status anytime at: http://localhost:3000/registration-status?code={tracking_code}\n\n"
            f"Best regards,\nCampusAI Platform Governance Team"
        )
        return await self.send_notification(
            recipient_email=recipient_email,
            event_type="REGISTRATION_SUBMITTED",
            subject=subject,
            content=content,
            college_id=college_id,
            audit_content=(
                f"Registration received for {college_name}. "
                "The tracking code and status link are intentionally omitted from the audit log."
            ),
            metadata={"college_name": college_name},
        )

    async def notify_additional_info_requested(
        self,
        recipient_email: str,
        college_name: str,
        tracking_code: str,
        prompt: str,
        college_id: Optional[uuid.UUID] = None,
    ) -> NotificationLog:
        """Notifies applicant that Super Admin requested additional compliance details."""
        subject = f"Action Required: Additional Information Requested for {college_name}"
        content = (
            f"Dear Representative of {college_name},\n\n"
            f"The Super Administrator has reviewed your onboarding application ({tracking_code}) and requires additional clarification:\n\n"
            f"Requested Information:\n\"{prompt}\"\n\n"
            f"Please update your submission at: http://localhost:3000/registration-status?code={tracking_code}\n\n"
            f"Best regards,\nCampusAI Platform Governance Team"
        )
        return await self.send_notification(
            recipient_email=recipient_email,
            event_type="ADDITIONAL_INFO_REQUESTED",
            subject=subject,
            content=content,
            college_id=college_id,
            audit_content=(
                f"Additional information requested for {college_name}. "
                "The tracking code and status link are intentionally omitted from the audit log."
            ),
            metadata={"prompt": prompt, "college_name": college_name},
        )

    async def notify_registration_approved(
        self,
        recipient_email: str,
        college_name: str,
        college_id: uuid.UUID,
        admin_login_url: str = "http://localhost:3001/login",
    ) -> NotificationLog:
        """Notifies applicant that their college has been officially approved."""
        subject = f"Congratulations! {college_name} has been Approved on CampusAI"
        content = (
            f"Dear Administrator,\n\n"
            f"We are pleased to inform you that {college_name} has been approved by the Global Super Administrator.\n"
            f"Your institutional tenant space is now active.\n\n"
            f"Next Steps: Begin Onboarding Wizard\n"
            f"Access your College Administrator Workspace at: {admin_login_url}\n\n"
            f"Best regards,\nCampusAI Institutional Team"
        )
        return await self.send_notification(
            recipient_email=recipient_email,
            event_type="REGISTRATION_APPROVED",
            subject=subject,
            content=content,
            college_id=college_id,
            metadata={"college_name": college_name, "college_id": str(college_id)},
        )

    async def notify_registration_rejected(
        self,
        recipient_email: str,
        college_name: str,
        tracking_code: str,
        reason: Optional[str] = None,
        college_id: Optional[uuid.UUID] = None,
    ) -> NotificationLog:
        """Notifies applicant that their application could not be approved."""
        subject = f"Update regarding onboarding application for {college_name}"
        content = (
            f"Dear Representative of {college_name},\n\n"
            f"Thank you for your interest in CampusAI. After reviewing your application ({tracking_code}), "
            f"the compliance team was unable to verify the institutional credentials.\n\n"
            f"Reason provided: {reason or 'Institutional domain or accreditation verification criteria not met.'}\n\n"
            f"For further inquiries, please contact platform support at support@campusai.platform.\n\n"
            f"Best regards,\nCampusAI Platform Governance Team"
        )
        return await self.send_notification(
            recipient_email=recipient_email,
            event_type="REGISTRATION_REJECTED",
            subject=subject,
            content=content,
            college_id=college_id,
            audit_content=(
                f"Registration decision sent for {college_name}. "
                "The tracking code is intentionally omitted from the audit log."
            ),
            metadata={"reason": reason, "college_name": college_name},
        )

    async def notify_admin_invitation(
        self,
        recipient_email: str,
        full_name: str,
        college_name: str,
        invitation_token: str,
        college_id: uuid.UUID,
    ) -> NotificationLog:
        """Sends an administrator invitation link."""
        invite_url = (
            f"{settings.ADMIN_FRONTEND_URL}/accept-invitation?"
            f"{urlencode({'token': invitation_token})}"
        )
        subject = f"Invitation to administer {college_name} on CampusAI"
        content = (
            f"Dear {full_name},\n\n"
            f"You have been designated as an institutional administrator for {college_name} on CampusAI.\n\n"
            f"To accept this role and establish your credentials, please click the secure link below:\n"
            f"{invite_url}\n\n"
            f"This link is valid for 7 days. If you did not expect this invitation, please disregard this email.\n\n"
            f"Best regards,\nCampusAI Security"
        )
        return await self.send_notification(
            recipient_email=recipient_email,
            event_type="COLLEGE_ADMIN_INVITATION",
            subject=subject,
            content=content,
            college_id=college_id,
            audit_content=(
                f"Administrator invitation sent to {recipient_email} for {college_name}. "
                "The invitation link is intentionally omitted from the audit log."
            ),
            metadata={"college_name": college_name},
        )

    async def notify_onboarding_completed(
        self,
        recipient_email: str,
        college_name: str,
        college_id: uuid.UUID,
    ) -> NotificationLog:
        """Notifies the administrator that institutional onboarding is complete."""
        subject = f"Onboarding Complete: {college_name} is Live on CampusAI"
        content = (
            f"Dear Administrator,\n\n"
            f"Congratulations! You have completed all initial onboarding milestones for {college_name}.\n"
            f"Your verified institutional knowledge base and web sources are ready.\n\n"
            f"You can now manage website crawling, document review, and monitor student FAQs at:\n"
            f"http://localhost:3001/college-admin/dashboard\n\n"
            f"Best regards,\nCampusAI Platform Governance Team"
        )
        return await self.send_notification(
            recipient_email=recipient_email,
            event_type="ONBOARDING_COMPLETED",
            subject=subject,
            content=content,
            college_id=college_id,
            metadata={"college_name": college_name, "college_id": str(college_id)},
        )

