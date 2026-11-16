"""In-Memory Sliding Window Rate Limiting Engine.

Defends sensitive authentication, chat, and support endpoints against brute force,
credential stuffing, denial of service (DoS), and resource abuse.
"""

import time
from collections import defaultdict
from typing import Callable, Dict, List
from fastapi import HTTPException, Request, status
from app.core.logging import logger


class InMemoryRateLimiter:
    """Sliding-window rate limiter tracking requests per IP per action bucket."""

    def __init__(self):
        # Maps bucket_key -> list of Unix timestamps
        self._records: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_key: str, max_requests: int, window_seconds: int = 60) -> bool:
        """Determines if a request from client_key should be allowed under sliding window."""
        now = time.time()
        cutoff = now - window_seconds

        # Prune timestamps older than window
        timestamps = self._records[client_key]
        self._records[client_key] = [ts for ts in timestamps if ts > cutoff]

        if len(self._records[client_key]) >= max_requests:
            return False

        self._records[client_key].append(now)
        return True

    def reset(self):
        """Clears all stored rate limit records (useful for test isolation)."""
        self._records.clear()


# Global singleton instance
rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting trusted proxy X-Forwarded-For headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in list is original client
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def rate_limit(max_requests: int = 60, window_seconds: int = 60) -> Callable:
    """FastAPI dependency factory enforcing rate limits on specific routes."""

    async def dependency(request: Request):
        client_ip = get_client_ip(request)
        route_path = request.url.path
        bucket_key = f"{client_ip}:{route_path}"

        allowed = rate_limiter.is_allowed(bucket_key, max_requests, window_seconds)
        if not allowed:
            logger.warning("Rate limit exceeded for IP %s on %s (limit: %d/%ds)", client_ip, route_path, max_requests, window_seconds)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests allowed per {window_seconds} seconds. Please wait before retrying.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency

