from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from enum import Enum

class CircuitState(str, Enum):
    HEALTHY = "HEALTHY"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class FailureType(str, Enum):
    RATE_LIMIT_429 = "RATE_LIMIT_429"
    TIMEOUT = "TIMEOUT"
    SERVER_5XX = "SERVER_5XX"
    AUTH_FAILURE = "AUTH_FAILURE"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        # In-memory circuit state cache: model_id -> dict
        self._states: Dict[str, Dict[str, Any]] = {}

    def get_state(self, model_id: str) -> Dict[str, Any]:
        if model_id not in self._states:
            self._states[model_id] = {
                "state": CircuitState.HEALTHY,
                "consecutive_failures": 0,
                "cooldown_until": None,
                "last_failure_type": None,
                "last_error": None
            }
        
        info = self._states[model_id]
        now = datetime.now(timezone.utc)
        # Check if cooldown expired in OPEN state
        if info["state"] == CircuitState.OPEN and info["cooldown_until"]:
            if now >= info["cooldown_until"]:
                info["state"] = CircuitState.HALF_OPEN
        
        return info

    def can_execute(self, model_id: str) -> bool:
        info = self.get_state(model_id)
        return info["state"] in [CircuitState.HEALTHY, CircuitState.HALF_OPEN]

    def record_success(self, model_id: str):
        info = self.get_state(model_id)
        info["state"] = CircuitState.HEALTHY
        info["consecutive_failures"] = 0
        info["cooldown_until"] = None
        info["last_error"] = None

    def record_failure(self, model_id: str, error: Exception, status_code: Optional[int] = None) -> FailureType:
        info = self.get_state(model_id)
        info["consecutive_failures"] += 1
        now = datetime.now(timezone.utc)

        # Classify error
        err_msg = str(error).lower()
        if status_code == 429 or "429" in err_msg or "quota" in err_msg or "rate limit" in err_msg:
            failure_type = FailureType.RATE_LIMIT_429
            cooldown = 120  # 2 minute cooldown for 429 quota
        elif status_code in [401, 403] or "unauthorized" in err_msg or "invalid api key" in err_msg:
            failure_type = FailureType.AUTH_FAILURE
            cooldown = 300  # 5 min lockout for auth
        elif "timeout" in err_msg:
            failure_type = FailureType.TIMEOUT
            cooldown = 30
        elif (status_code and status_code >= 500) or "500" in err_msg or "503" in err_msg:
            failure_type = FailureType.SERVER_5XX
            cooldown = 45
        else:
            failure_type = FailureType.NETWORK_ERROR
            cooldown = 30

        info["last_failure_type"] = failure_type
        info["last_error"] = str(error)

        if failure_type in [FailureType.RATE_LIMIT_429, FailureType.AUTH_FAILURE] or info["consecutive_failures"] >= self.failure_threshold:
            info["state"] = CircuitState.OPEN
            info["cooldown_until"] = now + timedelta(seconds=cooldown)
        
        return failure_type

circuit_breaker = CircuitBreaker()
