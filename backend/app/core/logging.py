"""Structured Logging & Sensitive Data Redaction Module.

Configures application-wide log formatting for FastAPI and Celery with automatic
scrubbing of credentials, JWT tokens, API keys, and sensitive authorization headers.
"""

import logging
import re
import sys
from app.core.config import settings

# Regex patterns matching sensitive information
SENSITIVE_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*", re.IGNORECASE), r"\1[REDACTED_JWT]"),
    (re.compile(r"(['\"]?password['\"]?\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE), r"\1[REDACTED_PASSWORD]\2"),
    (re.compile(r"(['\"]?(?:api[_-]?key|secret|token)['\"]?\s*[:=]\s*['\"])[^'\"]+(['\"])", re.IGNORECASE), r"\1[REDACTED_KEY]\2"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), r"[REDACTED_GEMINI_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), r"[REDACTED_OPENAI_KEY]"),
]


class SensitiveDataFilter(logging.Filter):
    """Filters log messages and record arguments, scrubbing passwords and credentials."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.scrub_text(record.msg)

        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self.scrub_text(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self.scrub_text(str(v)) for v in record.args)

        return True

    @staticmethod
    def scrub_text(text: str) -> str:
        """Applies sensitive credential regex replacements."""
        scrubbed = text
        for pattern, replacement in SENSITIVE_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed


def setup_logging():
    """Initializes structured console logging for the application with sensitive data scrubbing."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"))
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Silence noisy third-party loggers
    # Note: uvicorn.access is intentionally suppressed — access logging is
    # handled by AccessLogMiddleware (app/middleware/access_log_middleware.py)
    # which provides richer, colourised output with status labels and latency.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger = logging.getLogger("college_chatbot")
    logger.info("Structured logging initialized at %s level (Sensitive Data Masking active)", logging.getLevelName(log_level))
    return logger


logger = setup_logging()
