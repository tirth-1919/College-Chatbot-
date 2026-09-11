import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request

# Default limits per resource: (max_requests, window_seconds)
RESOURCE_LIMITS = {
    "login": (5, 60),               # 5 attempts per minute
    "signup": (3, 60),              # 3 signups per minute
    "password_reset": (3, 3600),    # 3 attempts per hour
    "chat": (30, 60),               # 30 messages per minute
    "file_upload": (10, 60),        # 10 uploads per minute
    "image_upload": (10, 60),       # 10 image uploads per minute
    "voice": (15, 60),              # 15 audio interactions per minute
    "search": (40, 60),             # 40 searches per minute
    "admin_api": (120, 60),         # 120 admin requests per minute
    "website_sync": (2, 3600),      # 2 manual syncs per hour
    "ai_actions": (60, 60)          # 60 AI calls per minute
}

class ResourceRateLimiter:
    """Sliding-window rate limiter per client IP / User ID and resource type."""

    def __init__(self):
        # Key: (resource_name, client_key) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], list] = {}

    def check_rate_limit(self, resource: str, client_key: str) -> Tuple[bool, int, int]:
        """
        Evaluates whether client_key is allowed for the given resource.
        Returns: (is_allowed, remaining_quota, retry_after_seconds)
        """
        max_requests, window_seconds = RESOURCE_LIMITS.get(resource, (60, 60))
        now = time.time()
        bucket_key = (resource, client_key)

        timestamps = self._history.get(bucket_key, [])
        # Prune timestamps outside the current window
        cutoff = now - window_seconds
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = int(window_seconds - (now - oldest)) + 1
            self._history[bucket_key] = valid_timestamps
            return False, 0, max(retry_after, 1)

        # Allow and append
        valid_timestamps.append(now)
        self._history[bucket_key] = valid_timestamps
        remaining = max_requests - len(valid_timestamps)
        return True, remaining, 0

    def enforce(self, resource: str, request: Request, user_id: str = None):
        """FastAPI dependency helper to enforce rate limit or raise 429."""
        client_ip = request.client.host if request.client else "unknown"
        client_key = user_id if user_id else client_ip

        allowed, remaining, retry_after = self.check_rate_limit(resource, client_key)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {resource}. Please retry after {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

rate_limiter = ResourceRateLimiter()
