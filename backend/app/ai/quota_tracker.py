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
        quotas = db.query(AiQuota).all()
        results = []
        for q in quotas:
            model = q.model
            results.append({
                "id": q.id,
                "model_identifier": model.model_identifier if model else "Unknown",
                "model_name": model.display_name if model else "Unknown",
                "quota_type": q.quota_type,
                "limit": q.limit_amount,
                "used": q.used_amount,
                "remaining": q.remaining_amount,
                "reset_time": q.reset_time.isoformat() if q.reset_time else None,
                "source": q.source,  # PROVIDER_REPORTED, ESTIMATED, UNKNOWN
                "percentage_used": round((q.used_amount / q.limit_amount) * 100, 1) if q.limit_amount > 0 else 0,
                "last_updated_at": q.last_updated_at.isoformat() if q.last_updated_at else None
            })
        return results

quota_tracker = QuotaTracker()
