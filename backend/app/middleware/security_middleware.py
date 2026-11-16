"""Security, Request Hardening & Correlation ID Middleware Module.

Enforces OWASP recommended security headers, protects against oversized payload attacks (DoS),
and injects consistent X-Request-ID correlation tracking across all request cycles.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger

# Maximum allowed body sizes in bytes
MAX_JSON_BODY_BYTES = 2 * 1024 * 1024       # 2 Megabytes for standard JSON / query payloads
MAX_UPLOAD_BODY_BYTES = 55 * 1024 * 1024     # 55 Megabytes for document / PDF upload endpoints


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects industry-standard HTTP security headers into every HTTP response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 1. Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Defend against clickjacking (Deny framing)
        response.headers["X-Frame-Options"] = "DENY"

        # 3. Cross-Site Scripting (XSS) filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Strict Transport Security (HSTS) - Enforce HTTPS in production
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # 5. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 6. Restrict browser feature access
        response.headers["Permissions-Policy"] = "camera=(), geolocation=(), payment=()"

        return response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Injects or propagates a unique correlation ID (X-Request-ID) for end-to-end tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Request-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store on request state for access in route handlers and logging
        request.state.correlation_id = correlation_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Attach to response headers
        response.headers["X-Request-ID"] = correlation_id
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces strict body size thresholds to prevent buffer overflow and memory exhaustion DoS."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length_header = request.headers.get("content-length")

        if content_length_header:
            try:
                content_length = int(content_length_header)
                path = request.url.path

                # Allow larger limit for file upload endpoints
                is_upload = "/documents" in path or "/upload" in path
                limit = MAX_UPLOAD_BODY_BYTES if is_upload else MAX_JSON_BODY_BYTES

                if content_length > limit:
                    logger.warning(
                        "Payload Too Large rejected on %s: %d bytes (limit: %d bytes)",
                        path,
                        content_length,
                        limit,
                    )
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "success": False,
                            "error_code": "PAYLOAD_TOO_LARGE",
                            "message": f"Request body exceeds maximum permissible size limit of {limit // (1024 * 1024)} MB.",
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)

