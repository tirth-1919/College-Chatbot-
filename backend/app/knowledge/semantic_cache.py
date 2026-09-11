import hashlib
import time
from typing import Optional, Dict, Any
from backend.app.core.config import settings

class SemanticCache:
    def __init__(self):
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self.redis_client = None
        if settings.USE_REDIS:
            try:
                import redis
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception:
                self.redis_client = None

    def _make_key(self, query: str, context_hash: str = "") -> str:
        clean = query.strip().lower()
        h = hashlib.sha256(f"{clean}:{context_hash}".encode("utf-8")).hexdigest()
        return f"ait:cache:{h}"

    def get(self, query: str, context_hash: str = "") -> Optional[str]:
        key = self._make_key(query, context_hash)
        if self.redis_client:
            try:
                val = self.redis_client.get(key)
                if val:
                    return val
            except Exception:
                pass

        item = self._memory_cache.get(key)
        if item:
            if time.time() < item["expires_at"]:
                return item["value"]
            else:
                del self._memory_cache[key]
        return None

    def set(self, query: str, value: str, context_hash: str = "", ttl_seconds: int = 3600):
        key = self._make_key(query, context_hash)
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl_seconds, value)
                return
            except Exception:
                pass

        self._memory_cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl_seconds
        }

    def invalidate_all(self):
        """Invalidates entire semantic cache when authoritative knowledge changes."""
        self._memory_cache.clear()
        if self.redis_client:
            try:
                keys = self.redis_client.keys("ait:cache:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception:
                pass

semantic_cache = SemanticCache()
