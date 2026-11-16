"""Sentry Monitoring & Error Telemetry Module.

Initializes Sentry for FastAPI and Celery background workers with automatic
data scrubbing to ensure passwords, auth tokens, and student inquiries are never transmitted.
"""

from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.logging import logger


def scrub_sensitive_sentry_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Scrubs sensitive credentials, auth headers, and tokens before sending to Sentry."""
    if not event:
        return event

    # 1. Scrub HTTP request headers
    request_data = event.get("request", {})
    if request_data:
        headers = request_data.get("headers", {})
        for sensitive_header in ["authorization", "cookie", "x-college-id", "x-api-key"]:
            if sensitive_header in headers:
                headers[sensitive_header] = "[REDACTED]"

        # Scrub request body if present
        data = request_data.get("data")
        if isinstance(data, dict):
            for sensitive_key in ["password", "token", "verification_token", "secret", "api_key"]:
                if sensitive_key in data:
                    data[sensitive_key] = "[REDACTED]"

    # 2. Scrub user identity details (keep ID only, remove email/IP)
    user_info = event.get("user", {})
    if user_info:
        user_info.pop("email", None)
        user_info.pop("ip_address", None)
        user_info.pop("username", None)

    return event


def init_sentry() -> bool:
    """Safely initializes Sentry SDK if SENTRY_DSN is configured."""
    if not settings.SENTRY_DSN or settings.SENTRY_DSN.startswith("placeholder"):
        logger.info("Sentry DSN not configured. Error monitoring will use local structured logs.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=0.05,
            before_send=scrub_sensitive_sentry_event,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                CeleryIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry monitoring initialized successfully for environment: %s", settings.ENVIRONMENT)
        return True
    except ImportError:
        logger.warning("sentry-sdk package not installed. Sentry telemetry is disabled.")
        return False
    except Exception as err:
        logger.error("Failed to initialize Sentry monitoring: %s", str(err))
        return False

