import logging
import os
import time
from typing import Dict, Any, List, Optional
import asyncio
from google import genai
from google.genai import types
from google.genai.errors import APIError
from backend.app.ai.provider_base import BaseAIProvider, AIProviderResponse
from backend.app.core.config import settings
logger = logging.getLogger(__name__)

class GeminiQuotaError(Exception):
    # Quota/rate-limit errors are eligible for model failover.

    def __init__(self, model: str, original: Exception):
        super().__init__(f"Gemini quota/rate limit for model {model}")
        self.model = model
        self.original = original
        self.status_code = 429
class GeminiProvider(BaseAIProvider):
    DEFAULT_MODEL = "gemini-3.7-flash"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(provider_name="gemini")
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self._client: Optional[genai.Client] = None
        self._cooldown_until: Dict[str, float] = {}

    @staticmethod
    def _configured_models() -> List[str]:
        configured = getattr(settings, "GEMINI_MODELS", "")
        models = [model.strip() for model in configured.split(",") if model.strip()]
        return list(dict.fromkeys(models)) or [GeminiProvider.DEFAULT_MODEL]

    @staticmethod
    def _is_quota_error(error: Exception) -> bool:
        status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
        text = str(error).upper()
        return status_code == 429 or any(marker in text for marker in (
            "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED", "RATE LIMIT", "RATE_LIMIT", "TOO MANY REQUESTS"
        ))

    def _available_models(self, requested_model: Optional[str]) -> List[str]:
        configured = self._configured_models()
        ordered = [requested_model] if requested_model else []
        ordered.extend(configured)
        now = time.monotonic()
        return [
            model for model in dict.fromkeys(ordered)
            if self._cooldown_until.get(model, 0) <= now
        ]

    def _mark_quota_exhausted(self, model: str) -> None:
        cooldown = max(0, int(getattr(settings, "GEMINI_MODEL_COOLDOWN_SECONDS", 300)))
        self._cooldown_until[model] = time.monotonic() + cooldown
    @staticmethod
    def _raise_provider_error(error: Exception) -> None:
        status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
        if status_code is not None:
            try:
                error.status_code = status_code
            except Exception:
                pass
        raise error
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

        # The router is the single owner of cross-model/provider failover.  Do
        # not rotate the configured chain here: doing so hides attempts from the
        # router and can turn one candidate into ten sequential 60s waits.
        target_model = model_name or self.DEFAULT_MODEL
        if self._cooldown_until.get(target_model, 0) > time.monotonic():
            raise GeminiQuotaError(target_model, RuntimeError("Gemini model is cooling down"))

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

        logger.info("Gemini model attempt: %s", target_model)
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(model=target_model, contents=full_prompt, config=config),
                timeout=max(1, min(
                    int(getattr(settings, "GEMINI_REQUEST_TIMEOUT_SECONDS", 8)),
                    int(getattr(settings, "AI_PROVIDER_INITIAL_TIMEOUT_SECONDS", 8)),
                ))
            )
            logger.info("Gemini model result: SUCCESS (%s)", target_model)
        except Exception as error:
            if not self._is_quota_error(error):
                self._raise_provider_error(error)
            self._mark_quota_exhausted(target_model)
            logger.warning("Gemini model result: QUOTA_EXCEEDED (%s)", target_model)
            raise GeminiQuotaError(target_model, error) from error
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
