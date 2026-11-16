"""Tenant Context Resolution Middleware.

Intercepts requests and extracts tenant information from headers or JWT tokens.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import logger


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware that injects tenant context into request.state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        college_id_header = request.headers.get("X-College-ID")
        if college_id_header:
            request.state.college_id = college_id_header
            logger.debug("Request scoped to tenant: %s", college_id_header)
        else:
            request.state.college_id = None

        response = await call_next(request)
        return response

