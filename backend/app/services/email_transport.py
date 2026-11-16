"""Email transport interface and SMTP implementation."""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional, Protocol


class EmailDeliveryError(Exception):
    """Raised when an email transport cannot confirm message acceptance."""


class EmailTransport(Protocol):
    """Transport contract: return only after the provider accepts the message."""

    async def send_email(self, recipient_email: str, subject: str, content: str) -> None:
        """Sends one message or raises EmailDeliveryError."""


class SMTPEmailTransport:
    """SMTP transport that treats relay acceptance as successful dispatch."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        from_email: str,
        username: Optional[str],
        password: Optional[str],
        starttls: bool,
        timeout: float,
    ):
        self.host = host
        self.port = port
        self.from_email = from_email
        self.username = username
        self.password = password
        self.starttls = starttls
        self.timeout = timeout

    async def send_email(self, recipient_email: str, subject: str, content: str) -> None:
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    self._send_sync,
                    recipient_email,
                    subject,
                    content,
                ),
                timeout=self.timeout,
            )
        except (OSError, smtplib.SMTPException, TimeoutError) as exc:
            raise EmailDeliveryError("SMTP transport failed to accept the message.") from exc

    def _send_sync(self, recipient_email: str, subject: str, content: str) -> None:
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.set_content(content)

        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as client:
            client.ehlo()
            if self.starttls:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if self.username is not None and self.password is not None:
                client.login(self.username, self.password)
            refused_recipients = client.send_message(message)
            if refused_recipients:
                raise EmailDeliveryError("SMTP relay rejected the recipient.")
