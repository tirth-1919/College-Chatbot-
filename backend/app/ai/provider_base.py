from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator

class AIProviderResponse:
    def __init__(
        self,
        content: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        model_name: str = "",
        provider_name: str = "",
        raw_headers: Optional[Dict[str, str]] = None
    ):
        self.content = content
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens
        self.latency_ms = latency_ms
        self.model_name = model_name
        self.provider_name = provider_name
        self.raw_headers = raw_headers or {}

class BaseAIProvider(ABC):
    def __init__(self, provider_name: str, base_url: Optional[str] = None):
        self.provider_name = provider_name
        self.base_url = base_url

    @abstractmethod
    async def generate_response(
        self,
        model_name: str,
        prompt: str,
        system_instruction: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        context_history: Optional[List[Dict[str, str]]] = None,
        images: Optional[List[str]] = None
    ) -> AIProviderResponse:
        """Executes generation against provider API."""
        pass

    @abstractmethod
    async def health_check(self, model_name: str) -> bool:
        """Probes provider availability."""
        pass
