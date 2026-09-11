import time
import json
from typing import Any, Optional
from backend.app.core.config import settings

class InMemoryCache:
    def __init__(self):
        self._store = {}
        self._expiry = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._expiry and time.time() > self._expiry[key]:
            del self._store[key]
            del self._expiry[key]
            return None
        return self._store.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None):
        self._store[key] = value
        if ex:
            self._expiry[key] = time.time() + ex
        elif key in self._expiry:
            del self._expiry[key]

    def delete(self, key: str):
        self._store.pop(key, None)
        self._expiry.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

class CacheManager:
    def __init__(self):
        self.client = None
        self.in_memory = InMemoryCache()
        if settings.USE_REDIS:
            try:
                import redis
                self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self.client.ping()
            except Exception:
                self.client = None

    def get(self, key: str) -> Optional[Any]:
        if self.client:
            try:
                val = self.client.get(key)
                if val:
                    try:
                        return json.loads(val)
                    except Exception:
                        return val
                return None
            except Exception:
                pass
        return self.in_memory.get(key)

    def set(self, key: str, value: Any, expire_seconds: int = 300):
        if self.client:
            try:
                val = json.dumps(value) if not isinstance(value, str) else value
                self.client.set(key, val, ex=expire_seconds)
                return
            except Exception:
                pass
        self.in_memory.set(key, value, ex=expire_seconds)

    def delete(self, key: str):
        if self.client:
            try:
                self.client.delete(key)
            except Exception:
                pass
        self.in_memory.delete(key)

cache = CacheManager()
