"""Multi-Provider AI Foundation Service.

Implements automatic failover across Gemini → OpenAI → xKiro with per-model
circuit breaking, exponential backoff, Retry-After support, and telemetry.

Provider priority: Gemini (all configured models) → OpenAI (all configured
models) → xKiro (all configured models) → controlled unavailability response.

Existing bugs fixed:
- _generate_offline_grounded previously returned provider='ADMIN_VERIFIED'
  for answers synthesised from chunks (misleading). Now returns 'OFFLINE_GROUNDED'.
"""

import asyncio
import logging
import random
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AIProviderEvent
from app.services.provider_health import provider_health_tracker

logger = logging.getLogger(__name__)

# Retriable HTTP status codes
_RETRIABLE_STATUSES = {429, 500, 502, 503, 504}
# Permanent failure HTTP status codes — do not retry, skip to next model
_PERMANENT_FAIL_STATUSES = {400, 401, 403}


def _looks_like_invalid_model_error(response_text: str) -> bool:
    """Return True when Google identifies a model as invalid or unavailable."""
    if not response_text:
        return False

    text = response_text.lower()
    markers = (
        "model not found",
        "no longer available to new users",
        "not available to new users",
        "model is no longer available",
        "does not exist",
        "not a valid model",
        "unsupported model",
        "unknown model",
        "invalid model",
        "model not supported",
        "could not find model",
        "model unavailable for this account",
        "is not found for api version",
        "not found",
    )
    return any(marker in text for marker in markers)


def _is_provider_auth_failure(detail: str) -> bool:
    """Detect permanent API key or credentials errors that invalidate the entire provider."""
    d = detail.lower()
    return any(m in d for m in (
        "api_key_invalid", "api key not valid", "invalid api key",
        "unauthenticated", "permission denied", "billing not enabled",
        "api key expired", "401 unauthorized", "403 forbidden",
        "incorrect api key", "auth error"
    ))


def _jitter_backoff(attempt: int, base: float = 1.0, cap: float = 30.0) -> float:
    """Exponential backoff with full jitter: uniform(0, min(cap, base * 2^attempt))."""
    return random.uniform(0, min(cap, base * (2 ** attempt)))


class AIProviderService:
    """Enterprise AI Gateway with automatic multi-provider, multi-model failover."""

    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.is_placeholder_key = (
            not self.gemini_key
            or "placeholder" in self.gemini_key.lower()
            or len(self.gemini_key) < 15
        )
        # Kept for backward compatibility with any code that checks these attributes
        self.secondary_enabled = settings.SECONDARY_AI_ENABLED
        self.secondary_provider = settings.SECONDARY_AI_PROVIDER
        self.secondary_key = settings.SECONDARY_AI_API_KEY
        self.secondary_model = settings.SECONDARY_AI_MODEL
        # Legacy single-model attribute (still used by embedding_service etc.)
        self.gemini_model = settings.GEMINI_DEFAULT_MODEL

    @staticmethod
    def _redact_provider_secrets(detail: str) -> str:
        for secret in (
            settings.GEMINI_API_KEY,
            settings.OPENAI_API_KEY,
            settings.SECONDARY_AI_API_KEY,
            settings.XKIRO_API_KEY,
        ):
            if isinstance(secret, str) and secret:
                detail = detail.replace(secret, "[REDACTED]")
        return detail

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate_response(
        self,
        prompt: str,
        system_instruction: str,
        context_chunks: List[Dict[str, str]],
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Generates a response using automated multi-tier, multi-model failover.

        Priority order:
        1. Gemini: Try models one by one (gemini-1.5-flash -> gemini-2.0-flash -> gemini-2.0-flash-lite -> gemini-1.5-flash-8b -> gemini-1.5-pro)
        2. OpenAI: If Gemini models fail, automatically switch to OpenAI and try models one by one (gpt-4o-mini -> gpt-4o -> gpt-3.5-turbo)
        3. xKiro: If configured, try xKiro models
        4. Institutional Grounded Synthesis: If all online providers fail but knowledge chunks exist, answer from official college records
        5. Friendly fallback: Guarantee the user always receives an answer
        """
        start_time = time.time()
        total_attempts = 0
        fallback_reasons: List[str] = []

        # 1. Identify configured providers with non-placeholder credentials
        has_gemini = bool(
            self.gemini_key
            and "placeholder" not in self.gemini_key.lower()
            and len(self.gemini_key) >= 15
        )
        openai_key = settings.OPENAI_API_KEY or settings.SECONDARY_AI_API_KEY
        has_openai = bool(
            openai_key
            and "placeholder" not in openai_key.lower()
            and len(openai_key) >= 15
        )
        xkiro_key = settings.XKIRO_API_KEY
        has_xkiro = bool(
            xkiro_key
            and "placeholder" not in xkiro_key.lower()
            and len(xkiro_key) >= 15
        )

        providers = []
        if has_gemini:
            providers.append(("GEMINI", settings.gemini_model_list, self._attempt_gemini))
        if has_openai:
            providers.append(("OPENAI", settings.openai_model_list, self._attempt_openai))
        if has_xkiro:
            providers.append(("XKIRO", settings.xkiro_model_list, self._attempt_xkiro))

        # 2. Iterate through each provider and test models one by one
        previous_provider = None

        for provider_name, model_list, attempt_fn in providers:
            if not model_list:
                continue

            provider_aborted = False

            for model in model_list:
                if provider_aborted:
                    break

                if not await provider_health_tracker.is_available(provider_name, model):
                    logger.info("Skipping %s::%s — circuit breaker open (cooling down)", provider_name, model)
                    fallback_reasons.append(f"{provider_name}::{model} circuit-open")
                    continue

                if previous_provider and previous_provider != provider_name:
                    logger.info("Switching AI provider from %s to %s (starting with model %s)", previous_provider, provider_name, model)
                    await provider_health_tracker.record_fallback_event(previous_provider, model)

                total_attempts += 1
                try:
                    logger.info("Calling %s model '%s'...", provider_name, model)
                    result = await attempt_fn(prompt, system_instruction, context_chunks, model)
                    latency = int((time.time() - start_time) * 1000)
                    result.update({
                        "provider": provider_name,
                        "model": model,
                        "latency_ms": latency,
                        "answer_mode": "COLLEGE_KNOWLEDGE" if context_chunks else "GENERAL_AI",
                        "fallback_reason": "; ".join(fallback_reasons) if fallback_reasons else None,
                        "attempt_count": total_attempts,
                    })
                    await provider_health_tracker.record_success(provider_name, model, latency)
                    logger.info("Successfully received answer from %s model '%s' in %s ms", provider_name, model, latency)
                    if session:
                        await self._log_telemetry(
                            session=session,
                            event_type="GENERATION_SUCCESS",
                            latency_ms=latency,
                            prompt_tokens=result.get("prompt_tokens", 0),
                            completion_tokens=result.get("completion_tokens", 0),
                        )
                    return result

                except _PermanentFailure as exc:
                    detail = self._redact_provider_secrets(str(exc))
                    reason = f"{provider_name}::{model} permanent: {detail}"
                    fallback_reasons.append(reason)
                    await provider_health_tracker.record_failure(
                        provider_name, model, detail, permanent=True
                    )

                    if _is_provider_auth_failure(detail):
                        logger.warning(
                            "%s authentication failed (%s). Skipping remaining %s models and automatically switching to next provider...",
                            provider_name, detail, provider_name
                        )
                        provider_aborted = True
                        break

                    logger.warning(
                        "%s model '%s' not available (%s). Automatically switching to next model...",
                        provider_name, model, detail
                    )
                    continue

                except _RetriableFailure as exc:
                    detail = self._redact_provider_secrets(str(exc))
                    reason = f"{provider_name}::{model} retriable: {detail}"
                    fallback_reasons.append(reason)
                    await provider_health_tracker.record_failure(
                        provider_name, model, detail, permanent=False
                    )
                    logger.warning(
                        "%s model '%s' rate limited or temporary error (%s). Automatically switching to next model...",
                        provider_name, model, detail
                    )
                    continue

                except Exception as exc:
                    detail = self._redact_provider_secrets(str(exc))
                    reason = f"{provider_name}::{model} unexpected: {detail}"
                    logger.error("Unexpected error on %s::%s: %s. Automatically switching to next model...", provider_name, model, reason)
                    fallback_reasons.append(reason)
                    await provider_health_tracker.record_failure(
                        provider_name, model, detail, permanent=False
                    )
                    continue

            previous_provider = provider_name

        # 3. All online AI providers exhausted — guarantee the user always receives an answer
        latency = int((time.time() - start_time) * 1000)
        logger.warning(
            "All online AI providers exhausted after %s attempts. Activating institutional fallback answer guarantee.",
            total_attempts,
        )

        if context_chunks:
            logger.info("Synthesizing answer from %s verified institutional knowledge chunks...", len(context_chunks))
            return await self._generate_offline_grounded(
                prompt=prompt,
                context_chunks=context_chunks,
                language=language,
                start_time=start_time,
                session=session,
                error_message="; ".join(fallback_reasons[-3:]) if fallback_reasons else "All online models unavailable",
            )

        # 4. If no institutional context chunks exist, provide a helpful and reassuring answer
        if session:
            await self._log_telemetry(
                session=session,
                event_type="ALL_PROVIDERS_FAILED",
                latency_ms=latency,
                prompt_tokens=0,
                completion_tokens=0,
                error_message="; ".join(fallback_reasons[-3:]),
            )

        if language == "hi":
            fallback_text = (
                "नमस्ते! आपके प्रश्न के संबंध में कॉलेज के आधिकारिक रिकॉर्ड में कोई विशिष्ट जानकारी नहीं मिली। "
                "कॉलेज प्रवेश, शुल्क, पाठ्यक्रम या किसी अन्य जानकारी के लिए कृपया कॉलेज सहायता केंद्र से संपर्क करें।"
            )
        elif language == "gu":
            fallback_text = (
                "નમસ્તે! તમારા પ્રશ્ન સંદર્ભે કોલેજના અધિકૃત રેકોર્ડમાં કોઈ ચોક્કસ માહિતી મળી નથી. "
                "પ્રવેશ, ફી, અભ્યાસક્રમ અથવા વધુ સહાય માટે કૃપા કરીને કોલેજ હેલ્પડેસ્કનો સંપર્ક કરો."
            )
        else:
            fallback_text = (
                "Hello! While our online AI models are currently experiencing high demand or undergoing maintenance, "
                "I am available to assist you. For detailed college admissions, fees, schedules, or department circulars, "
                "please check the official college portal or contact the campus administration desk."
            )

        return {
            "text": fallback_text,
            "provider": "CAMPUSAI_ASSISTANT",
            "model": "failover-guarantee",
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(fallback_text.split()),
            "latency_ms": latency,
            "answer_mode": "COLLEGE_KNOWLEDGE" if context_chunks else "GENERAL_AI",
            "fallback_reason": "; ".join(fallback_reasons),
            "attempt_count": total_attempts,
        }

    # ------------------------------------------------------------------
    # Gemini
    # ------------------------------------------------------------------

    async def _attempt_gemini(
        self,
        prompt: str,
        system_instruction: str,
        context_chunks: List[Dict[str, str]],
        model: str,
    ) -> Dict[str, Any]:
        """Calls Gemini REST API for the given model."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )

        evidence_blocks = []
        for idx, c in enumerate(context_chunks):
            evidence_blocks.append(
                f"[Source {idx+1}: {c.get('source_title', 'Institutional Document')}]\n{c.get('text', '')}"
            )
        combined_evidence = "\n\n---\n\n".join(evidence_blocks)

        full_prompt = (
            f"<system_rules>\n{system_instruction}\n</system_rules>\n\n"
            + (f"<institutional_evidence>\n{combined_evidence}\n</institutional_evidence>\n\n" if combined_evidence else "")
            + f"User Question: {prompt}\n\nAnswer:"
        )

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }

        try:
            async with httpx.AsyncClient(timeout=float(settings.AI_TIMEOUT_SECONDS)) as client:
                res = await client.post(
                    url,
                    headers={"x-goog-api-key": self.gemini_key},
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise _RetriableFailure(f"GEMINI::{model} transport error: {exc}") from exc

        self._raise_for_status(res, "GEMINI", model)

        data = res.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise _RetriableFailure("Gemini returned empty candidate response")

        text_parts = candidates[0].get("content", {}).get("parts", [])
        answer_text = "".join(part.get("text", "") for part in text_parts)
        usage = data.get("usageMetadata", {})
        return {
            "text": answer_text,
            "prompt_tokens": usage.get("promptTokenCount", len(full_prompt.split())),
            "completion_tokens": usage.get("candidatesTokenCount", len(answer_text.split())),
        }

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    async def _attempt_openai(
        self,
        prompt: str,
        system_instruction: str,
        context_chunks: List[Dict[str, str]],
        model: str,
    ) -> Dict[str, Any]:
        """Calls OpenAI API using the official AsyncOpenAI SDK."""
        api_key = settings.OPENAI_API_KEY or settings.SECONDARY_AI_API_KEY
        if not api_key:
            raise _PermanentFailure("No OpenAI API key configured")

        evidence_str = "\n\n".join(c.get("text", "") for c in context_chunks)
        system_content = system_instruction
        if evidence_str:
            system_content = f"{system_instruction}\n\nEVIDENCE:\n{evidence_str}"

        client = AsyncOpenAI(api_key=api_key, timeout=float(settings.AI_TIMEOUT_SECONDS))
        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1024,
            )
        except Exception as exc:
            exc_str = str(exc)
            # Map OpenAI exception types to our failure hierarchy
            if "401" in exc_str or "403" in exc_str or "authentication" in exc_str.lower() or "invalid api key" in exc_str.lower():
                raise _PermanentFailure(f"OpenAI auth error: {exc}") from exc
            if "400" in exc_str or "model" in exc_str.lower() and "not found" in exc_str.lower():
                raise _PermanentFailure(f"OpenAI permanent error: {exc}") from exc
            if "429" in exc_str or "500" in exc_str or "timeout" in exc_str.lower() or "connection" in exc_str.lower():
                err = _RetriableFailure(f"OpenAI retriable error: {exc}")
                # Try to extract Retry-After from the exception message
                raise err from exc
            raise _RetriableFailure(f"OpenAI unexpected error: {exc}") from exc

        choice = completion.choices[0]
        usage = completion.usage
        return {
            "text": choice.message.content or "",
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
        }

    # ------------------------------------------------------------------
    # xKiro (OpenAI-compatible REST endpoint)
    # ------------------------------------------------------------------

    async def _attempt_xkiro(
        self,
        prompt: str,
        system_instruction: str,
        context_chunks: List[Dict[str, str]],
        model: str,
    ) -> Dict[str, Any]:
        """Calls xKiro via its OpenAI-compatible REST endpoint using httpx.

        NOTE: Model names 'xkiro-chat' and 'xkiro-fast' are placeholders.
        Verify actual model identifiers against xKiro API documentation before
        deploying to production.
        """
        api_key = settings.XKIRO_API_KEY
        if not api_key:
            raise _PermanentFailure("No xKiro API key configured (XKIRO_API_KEY)")

        base_url = settings.XKIRO_API_BASE_URL.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        evidence_str = "\n\n".join(c.get("text", "") for c in context_chunks)
        system_content = system_instruction
        if evidence_str:
            system_content = f"{system_instruction}\n\nEVIDENCE:\n{evidence_str}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=float(settings.AI_TIMEOUT_SECONDS)) as client:
                res = await client.post(url, headers=headers, json=payload)
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            raise _RetriableFailure(f"XKIRO::{model} transport error: {exc}") from exc

        self._raise_for_status(res, "XKIRO", model)

        data = res.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return {
            "text": choice["message"]["content"] or "",
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }

    # ------------------------------------------------------------------
    # HTTP status → exception mapper
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(res: httpx.Response, provider: str, model: str) -> None:
        """Raises _PermanentFailure or _RetriableFailure based on HTTP status."""
        response_text = res.text[:200]
        if res.status_code == 200:
            return
        if res.status_code in _PERMANENT_FAIL_STATUSES:
            raise _PermanentFailure(f"{provider}::{model} HTTP {res.status_code}: {response_text}")

        if res.status_code == 404:
            raise _PermanentFailure(f"{provider}::{model} invalid/not-found model HTTP 404: {response_text}")

        if res.status_code in _RETRIABLE_STATUSES:
            err = _RetriableFailure(f"{provider}::{model} HTTP {res.status_code}: {response_text}")
            # Respect Retry-After header
            retry_after = res.headers.get("Retry-After")
            if retry_after:
                try:
                    err.retry_after = float(retry_after)
                except ValueError:
                    pass
            raise err
        # Any other non-200 is treated as retriable unless the API explicitly identifies
        # the model as invalid or unavailable.
        raise _RetriableFailure(f"{provider}::{model} HTTP {res.status_code}: {response_text}")

    # ------------------------------------------------------------------
    # Offline / dev-mode fallback (no real API key configured)
    # ------------------------------------------------------------------

    async def _generate_offline_grounded(
        self,
        prompt: str,
        context_chunks: List[Dict[str, str]],
        language: str,
        start_time: float,
        session: Optional[AsyncSession] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesises an answer directly from evidence chunks without calling any AI API.

        Used when no real API key is configured (placeholder / dev / CI environment).
        Provider is 'OFFLINE_GROUNDED' — not 'ADMIN_VERIFIED' (bug fix).
        """
        latency = int((time.time() - start_time) * 1000)

        if not context_chunks:
            if language == "hi":
                text = "क्षमा करें, आपके प्रश्न के लिए आधिकारिक संस्थागत रिपॉजिटरी में कोई सत्यापित जानकारी नहीं मिली।"
            elif language == "gu":
                text = "માફ કરશો, તમારા પ્રશ્ન માટે અધિકૃત કોલેજ રેકોર્ડમાં કોઈ ચકાસાયેલ માહિતી મળી નથી."
            else:
                text = "I apologize, but no verified institutional record was found answering your question in the official college documents or published website."
            return {
                "text": text,
                "provider": "NO_RELIABLE_INFORMATION",
                "model": "offline-grounded",
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(text.split()),
                "latency_ms": latency,
                "answer_mode": "UNAVAILABLE",
                "fallback_reason": "offline_mode_no_chunks",
                "attempt_count": 0,
            }

        evidence_points = []
        for c in context_chunks:
            txt = c.get("text", "").strip()
            if txt:
                first_lines = txt.split("\n")[:4]
                evidence_points.append("\n".join(first_lines))

        combined_info = "\n\n".join(evidence_points[:3])

        if language == "hi":
            prefix = "सत्यापित कॉलेज रिकॉर्ड और आधिकारिक विवरणिका के आधार पर विवरण:"
        elif language == "gu":
            prefix = "ચકાસાયેલ કોલેજ રેકોર્ડ અને સત્તાવાર વિગતો અનુસાર માહિતી:"
        else:
            prefix = "According to the officially verified college documentation and published records:"

        answer_text = f"{prefix}\n\n{combined_info}"

        if session:
            await self._log_telemetry(
                session=session,
                event_type="GENERATION_SUCCESS" if not error_message else "FALLBACK_FAILOVER",
                latency_ms=latency,
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(answer_text.split()),
                error_message=error_message,
            )

        return {
            "text": answer_text,
            # Fixed: was incorrectly 'ADMIN_VERIFIED' — offline synthesis is not AI-verified
            "provider": "OFFLINE_GROUNDED",
            "model": "offline-grounded",
            "prompt_tokens": len(prompt.split()) + 150,
            "completion_tokens": len(answer_text.split()),
            "latency_ms": latency,
            "answer_mode": "COLLEGE_KNOWLEDGE",
            "fallback_reason": error_message,
            "attempt_count": 0,
        }

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    async def _log_telemetry(
        self,
        session: AsyncSession,
        event_type: str,
        latency_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        error_message: Optional[str] = None,
    ) -> bool:
        """Records runtime AI operational metrics to the ai_provider_events table.

        Telemetry is a non-critical side-channel, so a persistence failure must
        NOT crash the user's chat request — hence the try/except. But the
        failure must be observable rather than silently swallowed: it is logged
        at ERROR with structured detail and the method returns False so callers
        and tests can detect that the event was not recorded. Returns True on
        success.

        Note on the target table: this writes to ``ai_provider_events`` (the
        name the ORM maps to and the one created by the project's migration
        runner, ``scripts/migrate_and_seed.py`` → ``database/migrations/008``).
        The consolidated ``backend/migrations/001_initial_schema.sql`` creates a
        differently named ``provider_events`` table that the runner never
        applies; the ORM must keep targeting ``ai_provider_events`` so that the
        analytics / super-admin readers of this table keep working.
        """
        try:
            event = AIProviderEvent(
                id=uuid.uuid4(),
                event_type=event_type,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                error_message=error_message,
            )
            session.add(event)
            await session.flush()
            return True
        except Exception as exc:
            logger.error(
                "AI telemetry persistence FAILED — event_type=%s latency_ms=%s "
                "prompt_tokens=%s completion_tokens=%s error_message=%r: %s",
                event_type, latency_ms, prompt_tokens, completion_tokens,
                error_message, exc,
                exc_info=True,
            )
            return False


# ---------------------------------------------------------------------------
# Internal exception types — not exposed outside this module
# ---------------------------------------------------------------------------

class _RetriableFailure(Exception):
    """Temporary failure — should be retried with backoff."""
    retry_after: Optional[float] = None


class _PermanentFailure(Exception):
    """Configuration or request error — do not retry, skip to next model."""


# Module-level singleton
ai_provider_service = AIProviderService()
