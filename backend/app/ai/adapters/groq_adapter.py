"""
Groq provider adapter (OpenAI-compatible chat completions API).

Follows the existing provider adapter pattern (BaseAIProvider):
    generate_response(model_name, prompt, system_instruction, ...) -> AIProviderResponse
    health_check(model_name) -> bool

Groq does not expose authoritative per-model pricing/quota metadata through its
/models endpoint, so free-tier status for Groq models is UNKNOWN unless the
operator records it. We never claim unlimited free usage and we never spend
money automatically — Groq usage is governed by the account's own plan.
"""
import os
import time
from typing import Dict, Any, List, Optional
import httpx
from backend.app.ai.provider_base import BaseAIProvider, AIProviderResponse
from backend.app.core.config import settings


class GroqProvider(BaseAIProvider):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(provider_name="groq", base_url=base_url or "https://api.groq.com/openai/v1")
        self.api_key = api_key or settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")

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
            raise ValueError("Groq API key is not configured")

        start_time = time.time()
        messages = [{"role": "system", "content": system_instruction}]

        if context_history:
            for m in context_history[-6:]:
                role = "assistant" if m.get("sender") == "assistant" else "user"
                messages.append({"role": role, "content": m.get("content", "")})

        user_content = prompt
        if evidence:
            context_str = "\n\nVERIFIED AIT EVIDENCE:\n" + "\n".join([
                f"- {e.get('name', '')}: {e.get('details', '')}" for e in evidence
            ])
            user_content += context_str

        messages.append({"role": "user", "content": user_content})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model_name or "openai/gpt-oss-20b",
                    "messages": messages,
                    "temperature": 0.2
                }
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return AIProviderResponse(
            content=content,
            input_tokens=usage.get("prompt_tokens", len(user_content) // 4),
            output_tokens=usage.get("completion_tokens", len(content) // 4),
            latency_ms=round(latency, 2),
            model_name=model_name,
            provider_name=self.provider_name,
            raw_headers=dict(resp.headers)
        )

    async def health_check(self, model_name: str) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                return res.status_code == 200
        except Exception:
            return False
