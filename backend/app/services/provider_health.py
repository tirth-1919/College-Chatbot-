"""In-memory per-model circuit breaker and health tracker.

Thread-safe using asyncio.Lock. Resets after AI_COOLDOWN_SECONDS.
No DB writes: telemetry goes to ai_provider_events via AIProviderService.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelHealth:
    provider: str
    model: str
    consecutive_failures: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_retries: int = 0
    fallback_events: int = 0
    last_failure_at: float = 0.0
    last_success_at: float = 0.0
    last_error_category: Optional[str] = None
    total_latency_ms: int = 0
    request_count: int = 0
    is_cooling_down: bool = False

    def average_latency_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count

    def status(self) -> str:
        if self.is_cooling_down:
            return "down"
        if self.consecutive_failures >= 1:
            return "degraded"
        return "healthy"


class ProviderHealthTracker:
    """Tracks per-model health and implements a simple in-memory circuit breaker."""

    def __init__(self):
        self._health: Dict[str, ModelHealth] = {}

    def _key(self, provider: str, model: str) -> str:
        return f"{provider}::{model}"

    async def get_or_create(self, provider: str, model: str) -> ModelHealth:
        k = self._key(provider, model)
        if k not in self._health:
            self._health[k] = ModelHealth(provider=provider, model=model)
        return self._health[k]

    async def record_success(self, provider: str, model: str, latency_ms: int) -> None:
        k = self._key(provider, model)
        h = self._health.setdefault(k, ModelHealth(provider=provider, model=model))
        h.consecutive_failures = 0
        h.total_successes += 1
        h.total_latency_ms += latency_ms
        h.request_count += 1
        h.last_success_at = time.time()
        h.is_cooling_down = False

    async def record_failure(
        self, provider: str, model: str, error_category: str, permanent: bool = False
    ) -> None:
        k = self._key(provider, model)
        h = self._health.setdefault(k, ModelHealth(provider=provider, model=model))
        h.consecutive_failures += 1
        h.total_failures += 1
        h.last_failure_at = time.time()
        h.last_error_category = error_category
        if permanent or h.consecutive_failures >= settings.AI_CIRCUIT_BREAKER_THRESHOLD:
            h.is_cooling_down = True

    async def is_available(self, provider: str, model: str) -> bool:
        k = self._key(provider, model)
        if k not in self._health:
            return True
        h = self._health[k]
        if not h.is_cooling_down:
            return True
        # Auto-recovery after cooldown period
        elapsed = time.time() - h.last_failure_at
        if elapsed >= settings.AI_COOLDOWN_SECONDS:
            h.is_cooling_down = False
            h.consecutive_failures = 0
            logger.info("Model %s::%s recovered from cooldown after %ss", provider, model, round(elapsed, 1))
            return True
        return False

    async def record_retry(self, provider: str, model: str) -> None:
        k = self._key(provider, model)
        h = self._health.setdefault(k, ModelHealth(provider=provider, model=model))
        h.total_retries += 1

    async def record_fallback_event(self, provider: str, model: str) -> None:
        k = self._key(provider, model)
        h = self._health.setdefault(k, ModelHealth(provider=provider, model=model))
        h.fallback_events += 1

    async def get_all_health(self) -> Dict[str, ModelHealth]:
        return dict(self._health)

    async def get_model_health(self, provider: str, model: str) -> Optional[ModelHealth]:
        return self._health.get(self._key(provider, model))


# Module-level singleton shared across the application process
provider_health_tracker = ProviderHealthTracker()
