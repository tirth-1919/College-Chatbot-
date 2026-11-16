"""Live HTTP Access Log Middleware.

Prints a colorized, one-line access log entry for every request — similar to
Uvicorn's built-in access log but richer:

    [BACKEND] 09:12:34  POST  /api/v1/auth/login          200  12.4 ms  127.0.0.1
    [BACKEND] 09:12:35  GET   /api/v1/colleges             401   3.1 ms  127.0.0.1
    [BACKEND] 09:12:36  GET   /api/v1/health               200   1.0 ms  127.0.0.1

Status-code colour key:
  2xx  → green   (success)
  3xx  → cyan    (redirect)
  4xx  → yellow  (client error)  401/403 → bold yellow
  5xx  → red     (server error)

Skipped paths (health/docs noise) are configurable via SKIP_PATHS.
"""

import time
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# ── ANSI colour codes ─────────────────────────────────────────────────────────
_R   = "\x1b[0m"       # reset
_B   = "\x1b[1m"       # bold
_DIM = "\x1b[2m"       # dim

_GREEN   = "\x1b[32m"
_CYAN    = "\x1b[36m"
_YELLOW  = "\x1b[33m"
_RED     = "\x1b[31m"
_MAGENTA = "\x1b[35m"
_BLUE    = "\x1b[34m"
_WHITE   = "\x1b[37m"

# Method colours
_METHOD_COLORS: dict[str, str] = {
    "GET":     _GREEN,
    "POST":    _BLUE,
    "PUT":     _CYAN,
    "PATCH":   _MAGENTA,
    "DELETE":  _RED,
    "OPTIONS": _DIM,
    "HEAD":    _DIM,
}

# Paths to skip (spammy health / asset / docs requests)
SKIP_PATHS: set[str] = {
    "/health",
    "/favicon.ico",
    "/openapi.json",
    "/docs",
    "/redoc",
}


def _status_color(code: int) -> str:
    if 200 <= code < 300:
        return _GREEN
    if 300 <= code < 400:
        return _CYAN
    if code in (401, 403):
        return _B + _YELLOW   # bold for auth failures — easy to spot
    if 400 <= code < 500:
        return _YELLOW
    if code >= 500:
        return _B + _RED
    return _WHITE


def _status_label(code: int) -> str:
    """Human-readable label appended after the numeric status code."""
    labels: dict[int, str] = {
        200: "OK",
        201: "CREATED",
        204: "NO CONTENT",
        301: "MOVED",
        302: "FOUND",
        304: "NOT MODIFIED",
        307: "REDIRECT",
        400: "BAD REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT FOUND",
        405: "METHOD NOT ALLOWED",
        409: "CONFLICT",
        413: "PAYLOAD TOO LARGE",
        422: "UNPROCESSABLE",
        429: "RATE LIMITED",
        500: "SERVER ERROR",
        502: "BAD GATEWAY",
        503: "UNAVAILABLE",
        504: "TIMEOUT",
    }
    return labels.get(code, "")


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "-"


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Prints a colourised one-line HTTP access log for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip noisy paths
        if path in SKIP_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        method    = request.method
        query     = f"?{request.url.query}" if request.url.query else ""
        full_path = path + query
        ip        = _client_ip(request)

        t0       = time.perf_counter()
        response = await call_next(request)
        ms       = (time.perf_counter() - t0) * 1000

        code        = response.status_code
        sc          = _status_color(code)
        mc          = _METHOD_COLORS.get(method, _WHITE)
        label       = _status_label(code)
        label_str   = f" {_DIM}{label}{_R}" if label else ""
        req_id      = getattr(request.state, "correlation_id", "")
        req_id_str  = f"  {_DIM}#{req_id[:8]}{_R}" if req_id else ""

        # Latency colour: green < 200 ms, yellow < 1 s, red ≥ 1 s
        if ms < 200:
            ms_color = _GREEN
        elif ms < 1000:
            ms_color = _YELLOW
        else:
            ms_color = _RED

        now = datetime.now(timezone.utc).strftime("%H:%M:%S")

        line = (
            f"{_DIM}[BACKEND]{_R} "
            f"{_DIM}{now}{_R}  "
            f"{mc}{_B}{method:<7}{_R}  "
            f"{full_path:<55}  "
            f"{sc}{_B}{code}{_R}{label_str}  "
            f"{ms_color}{ms:>7.1f} ms{_R}  "
            f"{_DIM}{ip}{_R}"
            f"{req_id_str}"
        )
        print(line, flush=True)  # noqa: T201 — intentional console output

        return response

