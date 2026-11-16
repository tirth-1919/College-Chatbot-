import asyncio
import logging
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.schemas.registration import CollegeAdminInvitationResponse
from app.services.email_transport import EmailDeliveryError, SMTPEmailTransport
from app.services.notification_service import NotificationService


class MockEmailTransport:
    def __init__(self, error=None):
        self.error = error
        self.messages = []

    async def send_email(self, recipient_email, subject, content):
        self.messages.append((recipient_email, subject, content))
        if self.error is not None:
            raise self.error


@pytest.mark.asyncio
async def test_smtp_transport_success_requires_relay_acceptance():
    transport = SMTPEmailTransport(
        host="smtp.example.test",
        port=587,
        from_email="noreply@example.test",
        username=None,
        password=None,
        starttls=True,
        timeout=1,
    )
    with patch("app.services.email_transport.smtplib.SMTP") as smtp_factory:
        client = smtp_factory.return_value.__enter__.return_value
        client.send_message.return_value = {}
        await transport.send_email("user@example.test", "Subject", "Body")

    client.starttls.assert_called_once()
    client.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_smtp_transport_rejection_is_not_treated_as_acceptance():
    transport = SMTPEmailTransport(
        host="smtp.example.test",
        port=587,
        from_email="noreply@example.test",
        username=None,
        password=None,
        starttls=False,
        timeout=1,
    )
    with patch("app.services.email_transport.smtplib.SMTP") as smtp_factory:
        client = smtp_factory.return_value.__enter__.return_value
        client.send_message.return_value = {"user@example.test": (550, b"rejected")}
        with pytest.raises(EmailDeliveryError):
            await transport.send_email("user@example.test", "Subject", "Body")


@pytest.mark.asyncio
async def test_notification_is_sent_only_after_transport_accepts():
    transport = MockEmailTransport()
    notification = await NotificationService(email_transport=transport).send_notification(
        "user@example.edu",
        "TEST_EVENT",
        "Subject",
        "Message",
    )

    assert notification.delivery_status == "SENT"
    assert transport.messages == [("user@example.edu", "Subject", "Message")]
    assert notification.error_message is None


@pytest.mark.asyncio
async def test_transport_rejection_records_failed_status():
    notification = await NotificationService(
        email_transport=MockEmailTransport(EmailDeliveryError("rejected"))
    ).send_notification("user@example.edu", "TEST_EVENT", "Subject", "Message")

    assert notification.delivery_status == "FAILED"
    assert notification.error_message == "Email transport failed to accept the message."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        (TimeoutError(), "Email transport timed out."),
        (OSError("network unavailable"), "Email transport failed to accept the message."),
    ],
)
async def test_timeout_and_network_failure_record_failed_status(failure, expected_error):
    notification = await NotificationService(
        email_transport=MockEmailTransport(failure)
    ).send_notification("user@example.edu", "TEST_EVENT", "Subject", "Message")

    assert notification.delivery_status == "FAILED"
    assert notification.error_message == expected_error


@pytest.mark.asyncio
async def test_async_transport_timeout_records_failed_status(monkeypatch):
    class SlowTransport:
        async def send_email(self, recipient_email, subject, content):
            self.arguments = (recipient_email, subject, content)
            await asyncio.sleep(1)

    monkeypatch.setattr(settings, "EMAIL_DELIVERY_TIMEOUT_SECONDS", 0.01)
    notification = await NotificationService(
        email_transport=SlowTransport()
    ).send_notification("user@example.edu", "TEST_EVENT", "Subject", "Message")

    assert notification.delivery_status == "FAILED"
    assert notification.error_message == "Email transport timed out."


@pytest.mark.asyncio
async def test_missing_provider_configuration_records_failed_not_simulated(monkeypatch):
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", None)
    monkeypatch.setattr(settings, "SMTP_USERNAME", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)

    notification = await NotificationService().send_notification(
        "user@example.edu", "TEST_EVENT", "Subject", "Message"
    )

    assert notification.delivery_status == "FAILED"
    assert notification.error_message == "Email transport is not configured."


@pytest.mark.asyncio
async def test_invitation_uses_configured_frontend_url_without_logging_token_or_url(
    monkeypatch, caplog
):
    invitation_token = "one-time token/with+reserved?characters"
    frontend_url = "https://admin.example.test"
    monkeypatch.setattr(settings, "ADMIN_FRONTEND_URL", frontend_url)
    caplog.set_level(logging.INFO, logger="college_chatbot")
    transport = MockEmailTransport()
    college_id = uuid.uuid4()

    notification = await NotificationService(email_transport=transport).notify_admin_invitation(
        recipient_email="invitee@example.edu",
        full_name="Invitee",
        college_name="Example College",
        invitation_token=invitation_token,
        college_id=college_id,
    )

    sent_content = transport.messages[0][2]
    assert f"{frontend_url}/accept-invitation?token=one-time+token%2Fwith%2Breserved%3Fcharacters" in sent_content
    assert invitation_token not in notification.content
    assert invitation_token not in caplog.text
    assert frontend_url not in caplog.text
    assert "accept-invitation" not in notification.content
    assert notification.delivery_status == "SENT"


@pytest.mark.asyncio
async def test_invitation_response_schema_never_contains_plaintext_or_hashed_token():
    response = CollegeAdminInvitationResponse(
        id=uuid.uuid4(),
        college_id=uuid.uuid4(),
        email="invitee@example.edu",
        full_name="Invitee",
        role_in_college="ADMIN",
        status="PENDING",
        expires_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    serialized = response.model_dump_json()
    assert "invitation_token" not in serialized
    assert "invitation_token_hash" not in serialized


def test_development_allows_localhost_http_frontend_url():
    config = Settings.model_validate(
        {
            "ENVIRONMENT": "development",
            "ADMIN_FRONTEND_URL": "http://localhost:3001/",
        }
    )
    assert config.ADMIN_FRONTEND_URL == "http://localhost:3001"


@pytest.mark.parametrize(
    "frontend_url",
    [
        "http://localhost:3001",
        "https://localhost:3001",
        "http://admin.example.test",
        "https://admin example.test",
    ],
)
def test_production_rejects_localhost_and_non_https_frontend_urls(frontend_url):
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "ENVIRONMENT": "production",
                "ADMIN_FRONTEND_URL": frontend_url,
            }
        )


def test_production_accepts_public_https_frontend_url():
    config = Settings.model_validate(
        {
            "ENVIRONMENT": "production",
            "ADMIN_FRONTEND_URL": "https://admin.example.test",
        }
    )
    assert config.ADMIN_FRONTEND_URL == "https://admin.example.test"


def test_empty_optional_smtp_configuration_is_treated_as_unconfigured():
    config = Settings.model_validate(
        {
            "SMTP_HOST": "",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
            "SMTP_FROM_EMAIL": "",
        }
    )

    assert config.SMTP_HOST is None
    assert config.SMTP_USERNAME is None
    assert config.SMTP_PASSWORD is None
    assert config.SMTP_FROM_EMAIL is None
