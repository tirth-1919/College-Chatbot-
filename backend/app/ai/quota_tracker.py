from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.admin_system import AiQuota, AiModelRegistry

class QuotaTracker:
    @classmethod
    def update_from_response(
        cls,
        db: Session,
        model_id: str,
        raw_headers: Dict[str, str],
        tokens_consumed: int = 0
    ):
        """
        Extracts quota information from HTTP response headers (e.g. OpenAI x-ratelimit-remaining-tokens,
        Anthropic ratelimit headers), or updates internal accounting estimates.
        """
        quota = db.query(AiQuota).filter(AiQuota.model_id == model_id).first()
        if not quota:
            return

        now = datetime.now(timezone.utc)
        headers_lower = {k.lower(): v for k, v in raw_headers.items()}

        # 1. Provider-reported check
        remaining_header = (
            headers_lower.get("x-ratelimit-remaining-requests") or
            headers_lower.get("anthropic-ratelimit-requests-remaining") or
            headers_lower.get("x-ratelimit-remaining-tokens")
        )
        reset_header = (
            headers_lower.get("x-ratelimit-reset-requests") or
            headers_lower.get("anthropic-ratelimit-requests-reset")
        )

        if remaining_header and remaining_header.isdigit():
            quota.remaining_amount = int(remaining_header)
            quota.source = "PROVIDER_REPORTED"
            quota.used_amount = max(0, quota.limit_amount - quota.remaining_amount)
            if reset_header:
                try:
                    quota.reset_time = now + timedelta(seconds=float(reset_header))
                except Exception:
                    pass
        else:
            # 2. Internal estimation accounting
            quota.used_amount += 1
            quota.remaining_amount = max(0, quota.limit_amount - quota.used_amount)
            quota.source = "ESTIMATED"

        quota.last_updated_at = now
        db.commit()

    @classmethod
    def get_quota_summary(cls, db: Session) -> list:
        """
        Quota telemetry separated into distinct concepts:
          - quota_status: VERIFIED (provider reported) | EXHAUSTED | UNKNOWN
          - usage_label : 'PROVIDER QUOTA' | 'LOCAL ESTIMATE' | 'UNKNOWN'
        Local request counters are NEVER presented as provider quota.
        """
        from backend.app.ai.provider_state import provider_state_manager, QuotaStatus

        quotas = db.query(AiQuota).all()
        results = []
        for q in quotas:
            model = q.model
            source = q.source
            runtime = None
            if model:
                runtime = provider_state_manager.snapshot(
                    model.provider.provider_name if model.provider else "unknown",
                    model.model_identifier,
                )

            if source == "PROVIDER_REPORTED":
                quota_status = QuotaStatus.VERIFIED.value
                usage_label = "PROVIDER QUOTA"
            elif runtime and runtime.get("quota_status") == QuotaStatus.EXHAUSTED.value:
                quota_status = QuotaStatus.EXHAUSTED.value
                usage_label = "LOCAL ESTIMATE"
            elif source in ("ESTIMATED", ""):
                quota_status = QuotaStatus.UNKNOWN.value
                usage_label = "LOCAL ESTIMATE"
            else:
                quota_status = QuotaStatus.UNKNOWN.value
                usage_label = "UNKNOWN"

            results.append({
                "id": q.id,
                "model_identifier": model.model_identifier if model else "Unknown",
                "model_name": model.display_name if model else "Unknown",
                "provider_name": (model.provider.provider_name if model and model.provider else None),
                "quota_type": q.quota_type,
                "quota_status": quota_status,
                "usage_label": usage_label,
                "limit": q.limit_amount if usage_label == "PROVIDER QUOTA" else None,
                "used": q.used_amount,
                "remaining": q.remaining_amount if usage_label == "PROVIDER QUOTA" else None,
                "reset_time": q.reset_time.isoformat() if q.reset_time else None,
                "source": source,  # PROVIDER_REPORTED, ESTIMATED, UNKNOWN
                "runtime_state": runtime.get("runtime_state") if runtime else None,
                "cooldown_active": runtime.get("cooldown_active") if runtime else False,
                "cooldown_until": runtime.get("cooldown_until") if runtime else None,
                "percentage_used": round((q.used_amount / q.limit_amount) * 100, 1) if (q.limit_amount > 0 and usage_label == "PROVIDER QUOTA") else None,
                "last_updated_at": q.last_updated_at.isoformat() if q.last_updated_at else None
            })
        return results

quota_tracker = QuotaTracker()
