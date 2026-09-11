import os
import time
from typing import Dict, Any, List, Optional
import httpx
from backend.app.ai.provider_base import BaseAIProvider, AIProviderResponse

class AnthropicProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(provider_name="anthropic", base_url=base_url or "https://api.anthropic.com/v1")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    async def generate_response(
        self,
        model_name: str,
        prompt: str,
        system_instruction: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        context_history: Optional[List[Dict[str, str]]] = None,
        images: Optional[List[str]] = None
    ) -> AIProviderResponse:
        if not self.api_key:
            raise ValueError("Anthropic API key is not configured")

        start_time = time.time()
        user_content = prompt
        if evidence:
            context_str = "\n\nVERIFIED AIT EVIDENCE:\n" + "\n".join([
                f"- {e.get('name', '')}: {e.get('details', '')}" for e in evidence
            ])
            user_content += context_str

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        messages = [{"role": "user", "content": user_content}]

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json={
                    "model": model_name or "claude-3-5-sonnet-20240620",
                    "system": system_instruction,
                    "max_tokens": 1024,
                    "messages": messages
                }
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000
        content_blocks = data.get("content", [])
        text = "".join([b.get("text", "") for b in content_blocks if b.get("type") == "text"])
        usage = data.get("usage", {})

        return AIProviderResponse(
            content=text,
            input_tokens=usage.get("input_tokens", len(user_content) // 4),
            output_tokens=usage.get("output_tokens", len(text) // 4),
            latency_ms=round(latency, 2),
            model_name=model_name,
            provider_name=self.provider_name,
            raw_headers=dict(resp.headers)
        )

    async def health_check(self, model_name: str) -> bool:
        return bool(self.api_key)
