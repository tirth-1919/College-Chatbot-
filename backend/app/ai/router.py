import os
import re
import time
import uuid
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.ai.provider_base import AIProviderResponse
from backend.app.ai.circuit_breaker import circuit_breaker, FailureType, CircuitState
from backend.app.ai.quota_tracker import quota_tracker
from backend.app.ai.provider_state import (
    provider_state_manager,
    is_quota_error,
    is_permanent_config_error,
    extract_retry_after,
    ProviderRuntimeState,
)
from backend.app.ai.adapters.gemini_adapter import GeminiProvider
from backend.app.ai.adapters.groq_adapter import GroqProvider
from backend.app.ai.adapters.openrouter_adapter import OpenRouterProvider
from backend.app.ai.adapters.openai_adapter import OpenAIProvider
from backend.app.ai.adapters.anthropic_adapter import AnthropicProvider
from backend.app.ai.adapters.ollama_adapter import OllamaProvider
from backend.app.ai.credential_registry import (
    credential_registry,
    credential_runtime,
    classify_failure,
)
from backend.app.models.admin_system import (
    AiProviderConfig,
    AiModelRegistry,
    AiUsageLog,
    AiQuota,
)

class AIRouter:
    def __init__(self):
        self.adapters = {
            "gemini": GeminiProvider(),
            "groq": GroqProvider(),
            "openrouter": OpenRouterProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "ollama": OllamaProvider()
        }

    def _get_adapter(self, provider_name: str, base_url: Optional[str] = None):
        name = (provider_name or "").lower()
        if name in self.adapters:
            return self.adapters[name]
        # Default fallback to OpenAI-compatible interface for custom providers
        return OpenAIProvider(base_url=base_url)

    def _adapter_for(self, provider_name: str, base_url: Optional[str] = None,
                     api_key: Optional[str] = None):
        """Per-attempt adapter instance carrying the specific credential.
        Singleton adapters keep their env-key fallback for back-compat; when a
        registry credential is used we build a fresh instance with that key."""
        name = (provider_name or "").lower()
        if not api_key:
            return self._get_adapter(provider_name, base_url)
        try:
            if name == "gemini":
                return GeminiProvider(api_key=api_key)
            if name == "groq":
                return GroqProvider(api_key=api_key, base_url=base_url)
            if name == "openrouter":
                return OpenRouterProvider(api_key=api_key, base_url=base_url)
            if name == "openai":
                return OpenAIProvider(api_key=api_key, base_url=base_url)
            if name == "anthropic":
                return AnthropicProvider(api_key=api_key, base_url=base_url)
            if name == "ollama":
                return OllamaProvider(base_url=base_url)
        except TypeError:
            pass
        return self._get_adapter(provider_name, base_url)

    def _expand_candidates(self, candidate_models, db) -> List[Dict[str, Any]]:
        """Expand (model, credential) combos in priority order.

        Per provider: credentials by priority first (model chain preserved),
        so provider order and model chains are unchanged — only multiplied by
        the currently-eligible credentials of each provider.
        """
        candidates: List[Dict[str, Any]] = []
        for model in candidate_models:
            provider = model.provider
            creds = credential_registry.get_for_provider(None, provider.provider_name)
            if not creds:
                # No registry credentials: fall back to env-key singleton adapter
                # (legacy behavior, evaluated with a virtual "env" credential id).
                candidates.append({
                    "model": model,
                    "provider": provider,
                    "credential_id": None,
                    "credential_label": None,
                    "api_key": None,
                })
            else:
                for cred in creds:
                    candidates.append({
                        "model": model,
                        "provider": provider,
                        "credential_id": cred["id"],
                        "credential_label": cred["label"] or cred["masked"],
                        "masked": cred["masked"],
                    })
        return candidates

    async def generate_response(
        self,
        prompt: str,
        system_instruction: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        context_history: Optional[List[Dict[str, str]]] = None,
        images: Optional[List[str]] = None,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        is_private_data: bool = False
    ) -> str:
        """
        Multi-AI Provider Router with Capability Matrix, Circuit Breaker,
        Privacy Filtering, Automatic Failover, and Telemetry Logging.
        """
        candidate_models = []
        if db:
            query = (
                db.query(AiModelRegistry)
                .join(AiProviderConfig)
                .filter(
                    AiModelRegistry.is_enabled == True,
                    AiProviderConfig.is_enabled == True
                )
            )

            # 1. Capability filtering (Vision requirement)
            if images:
                query = query.filter(AiModelRegistry.supports_vision == True)

            # 2. Privacy policy filtering
            if is_private_data:
                query = query.filter(AiProviderConfig.is_allowed_for_private_data == True)

            # Sort by priority ascending (1 is highest priority)
            candidate_models = query.order_by(AiModelRegistry.priority.asc()).all()

            # 3. FREE-ONLY policy filtering. Gemini keeps its existing free
            # access, Ollama is local (no cost); Groq/OpenRouter models are
            # eligible only when their recorded free-tier status allows it.
            if getattr(settings, "AI_FREE_ONLY_MODE", True):
                candidate_models = [
                    m for m in candidate_models
                    if m.provider.provider_name.lower() in ("gemini", "ollama")
                    or getattr(m, "free_tier_status", "UNKNOWN") == "FREE_TIER_ELIGIBLE"
                ]

        request_id = str(uuid.uuid4())
        last_error = None
        last_failure_type = None
        attempted_count = 0
        attempted_candidates = set()  # unique provider+model+credential identity
        suppressed_providers = set()  # request-scoped strong failure suppression
        provider_timeout_counts: Dict[str, int] = {}
        previous_model_identifier = None  # failover source for telemetry
        previous_credential_id = None

        candidates = self._expand_candidates(candidate_models, db)

        # Hard cap on attempts, always bounded by the unique candidate list
        max_attempts = int(getattr(settings, "PROVIDER_MAX_ATTEMPTS", 0) or 0)
        if max_attempts <= 0:
            max_attempts = len(candidates)

        free_only = bool(getattr(settings, "AI_FREE_ONLY_MODE", True))

        for candidate in candidates:
            if len(attempted_candidates) >= max_attempts:
                break

            model = candidate["model"]
            provider = candidate["provider"]
            cred_id = candidate["credential_id"]
            cred_label = candidate["credential_label"]
            candidate_key = (
                f"{provider.provider_name}/{model.model_identifier}"
                f"#{cred_id or 'env'}"
            )
            if candidate_key in attempted_candidates:
                continue
            attempted_candidates.add(candidate_key)

            provider_name_l = provider.provider_name.lower()
            if provider_name_l in suppressed_providers:
                continue

            # --- FREE-ONLY gate for registry credentials -------------------
            # FREE_TIER_ELIGIBLE/NOT_APPLICABLE → allowed; PAID and UNKNOWN
            # are never auto-spent under free-only mode (uniform rule for all
            # providers, including admin-classified Gemini credentials).
            if free_only and cred_id:
                cred_row = next(
                    (r for r in credential_registry.get_latest(None) if r["id"] == cred_id),
                    None,
                )
                if cred_row and cred_row["free_tier_status"] not in ("FREE_TIER_ELIGIBLE", "NOT_APPLICABLE"):
                    continue

            # --- LIVE eligibility (latest state, per credential+model) -----
            if cred_id:
                eligible = credential_runtime.is_eligible(provider.provider_name, cred_id, model.model_identifier)
            else:
                eligible = None  # defer to legacy evaluation below

            if eligible is False:
                snap = credential_runtime.snapshot(provider.provider_name, cred_id, model.model_identifier)
                db.add(AiUsageLog(
                    user_id=user_id, conversation_id=conversation_id, request_id=request_id,
                    provider_name=provider.provider_name, model_identifier=model.model_identifier,
                    latency_ms=0, http_status=0, success=False,
                    error_type=snap.get("runtime_state") or "COOLDOWN",
                    fallback_from_model=previous_model_identifier,
                ))
                db.commit()
                continue

            adapter = self._adapter_for(
                provider.provider_name, provider.base_url,
                credential_registry.get_decrypted(None, cred_id) if cred_id else None,
            )

            # 3. Full usability check: enabled, cooldown, circuit breaker.
            # With a registry credential the env-key check is NOT required —
            # the credential itself is the secret. Legacy env-key path unchanged.
            evaluation = provider_state_manager.evaluate_candidate(
                provider_name=provider.provider_name,
                model_identifier=model.model_identifier,
                provider_enabled=provider.is_enabled,
                model_enabled=model.is_enabled,
                api_key_env=provider.api_key_env,
                require_api_key=(not cred_id) and provider.provider_name.lower() != "ollama",
            ) if not cred_id else None

            if cred_id:
                cb_ok = circuit_breaker.can_execute(model.model_identifier)
                if not cb_ok:
                    evaluation = {"usable": False, "runtime_state": ProviderRuntimeState.CIRCUIT_OPEN}
                else:
                    evaluation = {"usable": True}

            if not evaluation["usable"]:
                runtime_state = evaluation["runtime_state"]
                # Log the skip so the admin can see the full decision chain
                db.add(AiUsageLog(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    request_id=request_id,
                    provider_name=provider.provider_name,
                    model_identifier=model.model_identifier,
                    latency_ms=0,
                    http_status=0,
                    success=False,
                    error_type=runtime_state.value if hasattr(runtime_state, "value") else str(runtime_state),
                    failover_occurred=previous_model_identifier is not None,
                    fallback_from_model=previous_model_identifier,
                ))
                db.commit()
                continue

            # Ollama reachability probe (no API key required)
            if provider.provider_name.lower() == "ollama":
                try:
                    reachable = await adapter.health_check(model.model_identifier)
                except Exception:
                    reachable = False
                if not reachable:
                    provider_state_manager.mark_unreachable(
                        provider.provider_name, model.model_identifier,
                        f"Endpoint not reachable: {provider.base_url or adapter.base_url}"
                    )
                    db.add(AiUsageLog(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        request_id=request_id,
                        provider_name=provider.provider_name,
                        model_identifier=model.model_identifier,
                        latency_ms=0,
                        http_status=0,
                        success=False,
                        error_type=ProviderRuntimeState.UNREACHABLE.value,
                        failover_occurred=previous_model_identifier is not None,
                        fallback_from_model=previous_model_identifier,
                    ))
                    db.commit()
                    continue

            attempted_count += 1
            start_time = time.time()

            try:
                resp: AIProviderResponse = await asyncio.wait_for(
                    adapter.generate_response(
                        model_name=model.model_identifier, prompt=prompt,
                        system_instruction=system_instruction, evidence=evidence,
                        context_history=context_history, images=images
                    ),
                    timeout=max(1, int(getattr(settings, "AI_PROVIDER_REQUEST_TIMEOUT_SECONDS", 30)))
                )

                # Success handling
                circuit_breaker.record_success(model.model_identifier)
                provider_state_manager.mark_success(provider.provider_name, model.model_identifier)
                if cred_id:
                    credential_runtime.mark_success(provider.provider_name, cred_id, model.model_identifier)
                model.health_status = "HEALTHY"
                model.consecutive_failures = 0
                model.requests_total += 1
                model.requests_success += 1
                model.last_success_at = datetime.now(timezone.utc)
                if model.avg_latency_ms == 0:
                    model.avg_latency_ms = resp.latency_ms
                else:
                    model.avg_latency_ms = round((model.avg_latency_ms * 0.9) + (resp.latency_ms * 0.1), 2)

                # Quota update
                quota_tracker.update_from_response(db, model.id, resp.raw_headers, resp.total_tokens)

                # Usage logging (shared request_id ties the failover chain together)
                usage_log = AiUsageLog(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    request_id=request_id,
                    provider_name=provider.provider_name,
                    model_identifier=model.model_identifier,
                    input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens,
                    total_tokens=resp.total_tokens,
                    latency_ms=resp.latency_ms,
                    http_status=200,
                    success=True,
                    failover_occurred=attempted_count > 1,
                    fallback_from_model=previous_model_identifier,
                )
                db.add(usage_log)
                db.commit()

                return resp.content

            except Exception as e:
                # Failure & Failover handling
                latency = round((time.time() - start_time) * 1000, 2)
                last_error = e
                status_code = getattr(e, "status_code", 500) if hasattr(e, "status_code") else 500
                failure_type = circuit_breaker.record_failure(model.model_identifier, e, status_code)
                last_failure_type = failure_type.value

                # --- Per-credential live state update (rotation driver) ------
                if cred_id:
                    cred_state = credential_runtime.mark_failure(
                        provider.provider_name, cred_id, model.model_identifier,
                        status_code, str(e),
                    )
                    cred_failure = cred_state.get("failure_type") or classify_failure(status_code, str(e))
                else:
                    cred_failure = None
                cb_state = circuit_breaker.get_state(model.model_identifier)

                model.health_status = cb_state["state"]
                model.consecutive_failures += 1
                model.requests_total += 1
                model.requests_failed += 1
                model.last_error_at = datetime.now(timezone.utc)
                model.last_error_message = str(e)[:500]
                model.cooldown_until = cb_state.get("cooldown_until")

                if failure_type == FailureType.RATE_LIMIT_429:
                    model.rate_limit_429_count += 1

                # Classify the failure for quota-aware state management
                error_message = str(e)
                if is_quota_error(status_code, error_message):
                    retry_after = extract_retry_after(e)
                    provider_state_manager.mark_quota_exhausted(
                        provider.provider_name, model.model_identifier, retry_after
                    )
                    # Gemini's registered models commonly share one Google
                    # project/quota. Suppress it immediately. Other providers
                    # retain model-level rotation because their limits may vary
                    # by model.
                    # Registered credentials represent independently managed
                    # keys/projects. A 429 from Key A must cool Key A and let
                    # Key B rotate immediately; only the legacy shared env-key
                    # path warrants provider-wide Gemini suppression.
                    if provider_name_l == "gemini" and not cred_id:
                        provider_state_manager.mark_provider_cooldown(
                            provider.provider_name, ProviderRuntimeState.QUOTA_EXHAUSTED,
                            retry_after, error_message[:500]
                        )
                        suppressed_providers.add(provider_name_l)
                elif is_permanent_config_error(status_code, error_message) or "not configured" in error_message.lower():
                    provider_state_manager.mark_configuration_error(
                        provider.provider_name, model.model_identifier, error_message[:500]
                    )
                elif failure_type == FailureType.NETWORK_ERROR:
                    provider_state_manager.mark_unreachable(
                        provider.provider_name, model.model_identifier, error_message[:500]
                    )
                else:
                    provider_state_manager.mark_error(
                        provider.provider_name, model.model_identifier,
                        failure_type.value, error_message[:500]
                    )

                if failure_type == FailureType.TIMEOUT and provider_name_l == "gemini":
                    provider_timeout_counts[provider_name_l] = provider_timeout_counts.get(provider_name_l, 0) + 1
                    if provider_timeout_counts[provider_name_l] >= int(getattr(settings, "GEMINI_PROVIDER_TIMEOUT_THRESHOLD", 2)):
                        provider_state_manager.mark_provider_cooldown(
                            provider.provider_name, ProviderRuntimeState.COOLDOWN,
                            error=error_message[:500]
                        )
                        suppressed_providers.add(provider_name_l)

                # Determine failover destination (next candidate) for telemetry
                remaining = [
                    m for m in candidate_models
                    if f"{m.provider.provider_name}/{m.model_identifier}" not in attempted_candidates
                ]
                next_model = remaining[0].model_identifier if remaining else None

                # Log failure telemetry (shared request_id keeps the chain visible)
                usage_log = AiUsageLog(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    request_id=request_id,
                    provider_name=provider.provider_name,
                    model_identifier=model.model_identifier,
                    latency_ms=latency,
                    http_status=status_code,
                    success=False,
                    error_type=failure_type.value,
                    failover_occurred=True,
                    fallback_from_model=next_model,
                )
                # Rotation event for the admin decision chain (credential_id only,
                # NEVER the raw key). The next attempted candidate follows in the
                # same request_id chain.
                if cred_id:
                    usage_log.fallback_from_model = (
                        f"{next_model} [cred={cred_label or cred_id[:8]}]"
                        if next_model else f"ROTATE_CREDENTIAL after {cred_label or cred_id[:8]}"
                    )
                db.add(usage_log)
                db.commit()

                previous_model_identifier = model.model_identifier
                # Continue to next candidate model in priority order!

        # Record the FINAL outcome of the decision chain when nothing succeeded
        if last_error or not candidate_models:
            category = last_failure_type or ("CONFIGURATION_ERROR" if not candidate_models else "PROVIDER_UNAVAILABLE")
            db.add(AiUsageLog(
                user_id=user_id,
                conversation_id=conversation_id,
                request_id=request_id,
                provider_name="FINAL",
                model_identifier="NO_USABLE_PROVIDER" if last_error else "NO_CANDIDATES",
                latency_ms=0,
                http_status=0,
                success=False,
                error_type=category,
                failover_occurred=len(attempted_candidates) > 0,
                fallback_from_model=previous_model_identifier,
            ))
            db.commit()

        # 4. Fallback Synthesizer: When all external models fail or no keys are configured
        prompt_lower = prompt.lower()

        if evidence:
            # Smart fallback: use only the most relevant evidence
            # Prioritize evidence with section titles that match the query
            relevant_evidence = []
            query_keywords = set(prompt_lower.split())

            for item in evidence:
                name = item.get("name", "").lower()
                details = str(item.get("details", "")).lower()
                section = item.get("section") or ""
                section = section.lower()
                source_type = item.get("source_type", "")

                # Calculate relevance score
                score = 0
                for keyword in query_keywords:
                    if len(keyword) > 2:  # Skip short words
                        if keyword in name:
                            score += 3
                        if keyword in section:
                            score += 10  # Section match is highly relevant
                        if keyword in details:
                            score += 1

                # Boost items that have section information and contain committee data
                if section and ("chairman" in details or "committee" in details or "council" in details):
                    score += 5

                # Boost website snapshot evidence over DB entities for committee queries
                if source_type == "website_snapshot":
                    score += 3

                # Penalize items that look like navigation/generic content
                if "children:" in details or ",role:" in details or "submitting" in details:
                    score -= 10

                relevant_evidence.append((score, item))

            # Sort by relevance and take top 1 most relevant
            relevant_evidence.sort(key=lambda x: x[0], reverse=True)
            top_evidence = [item for score, item in relevant_evidence[:1] if score > 0]

            if not top_evidence:
                top_evidence = evidence[:1]  # Fallback to first item

            # Format the answer intelligently
            item = top_evidence[0]
            name = item.get("name", "")
            details = item.get("details", "")
            section = item.get("section", "")

            # If it's a committee section with structured data, format it nicely
            if "chairman" in str(details).lower() and "members" in str(details).lower():
                # This is committee data - format as direct answer
                lines = []
                lines.append(f"Based on verified institutional records from Ahmedabad Institute of Technology:")

                # Extract chairman
                details_str = str(details)
                if "chairman:" in details_str.lower():
                    chairman_match = re.search(r'[Cc]hairman:\s*([^\n]+)', details_str)
                    if chairman_match:
                        chairman = chairman_match.group(1).strip()
                        lines.append(f"\n**Chairman:** {chairman}")

                # Extract convener if present
                if "convener:" in details_str.lower():
                    convener_match = re.search(r'[Cc]onvener:\s*([^\n]+)', details_str)
                    if convener_match:
                        convener = convener_match.group(1).strip()
                        lines.append(f"\n**Convener:** {convener}")

                # Extract members
                if "members:" in details_str.lower():
                    members_match = re.search(r'[Mm]embers:\s*([^\n]+)', details_str)
                    if members_match:
                        members = members_match.group(1).strip()
                        # Split members by comma and format as list
                        member_list = [m.strip() for m in members.split(',')]
                        lines.append(f"\n**Members:**")
                        for i, member in enumerate(member_list, 1):
                            lines.append(f"{i}. {member}")

                # Add source reference
                if section:
                    lines.append(f"\n*Source: Official AIT Website — {section}*")

                return "\n".join(lines)
            else:
                # Generic formatting for other content
                lines = [f"Based on verified institutional records from Ahmedabad Institute of Technology:\n"]
                if isinstance(details, dict):
                    details_str = "\n".join([f"- **{k.replace('_', ' ').title()}**: {v}" for k, v in details.items()])
                else:
                    details_str = str(details)
                lines.append(f"### {name}\n{details_str}\n")
                return "\n".join(lines).strip()

        if any(w in prompt_lower for w in ["who are you", "what can you do", "help"]):
            return (
                "I am the official **Ahmedabad Institute of Technology (AIT) AI Assistant**. "
                "I can help you explore academic courses (BCA, MCA, B.Tech CSE/IT, BBA, MBA), check official fee structures, "
                "understand admission eligibility and ACPC processes, review placement statistics and top recruiters, "
                "lookup faculty information, and view campus photos. How can I help you today?"
            )

        # General questions must not be described as failed institutional retrieval.
        if last_error or not candidate_models:
            category = last_failure_type or ("CONFIGURATION_ERROR" if not candidate_models else "PROVIDER_UNAVAILABLE")
            if category == "SERVER_5XX":
                return (
                    "The AI service is temporarily experiencing high demand. "
                    "This is usually resolved within a few moments. Please try again."
                )
            return (
                "The general-AI provider is currently unavailable "
                f"({category}). Please try again later."
            )

        return (
            "I couldn't verify that specific information from the available official AIT sources. "
            "Please visit https://www.aitindia.in for authoritative institutional information."
        )


ai_router = AIRouter()
