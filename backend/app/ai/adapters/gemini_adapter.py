import os
import time
from typing import Dict, Any, List, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend.app.ai.provider_base import BaseAIProvider, AIProviderResponse
from backend.app.core.config import settings

class GeminiProvider(BaseAIProvider):
    DEFAULT_MODEL = "gemini-3.6-flash"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(provider_name="gemini")
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise ValueError("Gemini API key is not configured")
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

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
            raise ValueError("Gemini API key is not configured")

        client = self._get_client()

        # Migrate obsolete model identifiers to verified working model
        target_model = model_name or self.DEFAULT_MODEL
        if "1.5" in target_model:
            target_model = self.DEFAULT_MODEL

        start_time = time.time()

        context_parts = []
        if evidence:
            evidence_str = "VERIFIED AIT EVIDENCE:\n" + "\n".join([
                f"- {e.get('name', '')}: {e.get('details', '')}" for e in evidence
            ])
            context_parts.append(evidence_str)

        if context_history:
            history_lines = []
            for msg in context_history[-6:]:
                sender = msg.get("sender", "user").title()
                content = msg.get("content", "")
                if content:
                    history_lines.append(f"{sender}: {content}")
            if history_lines:
                context_parts.append("CONVERSATION CONTEXT:\n" + "\n".join(history_lines))

        full_prompt = prompt
        if context_parts:
            full_prompt = f"{prompt}\n\n" + "\n\n".join(context_parts)

        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        try:
            response = await client.aio.models.generate_content(
                model=target_model,
                contents=full_prompt,
                config=config
            )
        except APIError as e:
            # Preserve status_code for circuit breaker tracking without leaking keys
            status_code = getattr(e, "code", None) or getattr(e, "status_code", 500)
            e.status_code = status_code
            raise e
        except Exception as e:
            raise e

        latency = (time.time() - start_time) * 1000
        text = response.text if hasattr(response, "text") and response.text is not None else ""

        # Extract tokens from usage_metadata when available, otherwise estimate
        input_tokens = len(full_prompt) // 4
        output_tokens = len(text) // 4
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            p_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
            c_tokens = getattr(response.usage_metadata, "candidates_token_count", None)
            if p_tokens is not None:
                input_tokens = p_tokens
            if c_tokens is not None:
                output_tokens = c_tokens

        return AIProviderResponse(
            content=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=round(latency, 2),
            model_name=target_model,
            provider_name=self.provider_name
        )

    async def health_check(self, model_name: Optional[str] = None) -> bool:
        if not self.api_key:
            return False
        try:
            client = self._get_client()
            target_model = model_name or self.DEFAULT_MODEL
            if "1.5" in target_model:
                target_model = self.DEFAULT_MODEL
            res = await client.aio.models.generate_content(
                model=target_model,
                contents="ping"
            )
            return bool(res and hasattr(res, "text") and res.text)
        except Exception:
            return False
