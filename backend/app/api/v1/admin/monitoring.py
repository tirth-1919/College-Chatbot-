import asyncio
import json
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_db, SessionLocal
from backend.app.core.config import settings
from backend.app.models.admin_system import AiModelRegistry, AiUsageLog, KnowledgeConflict
from backend.app.models.knowledge import KnowledgeGap
from backend.app.models.user import UserSession
from backend.app.ai.circuit_breaker import circuit_breaker

router = APIRouter(prefix="/monitoring", tags=["Admin Live Monitoring"])

async def event_generator(request: Request):
    """
    Server-Sent Events generator yielding real-time telemetry pulses.
    """
    while True:
        if await request.is_disconnected():
            break

        db = SessionLocal()
        try:
            active_sessions = db.query(UserSession).filter(UserSession.is_revoked == False).count()
            unresolved_gaps = db.query(KnowledgeGap).filter(KnowledgeGap.resolved == False).count()
            unresolved_conflicts = db.query(KnowledgeConflict).filter(KnowledgeConflict.resolution_status == "UNRESOLVED").count()

            models = db.query(AiModelRegistry).filter(AiModelRegistry.is_enabled == True).all()
            cb_open_count = sum(1 for m in models if circuit_breaker.get_state(m.model_identifier)["state"] == "OPEN")

            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_sessions": active_sessions,
                "unresolved_gaps": unresolved_gaps,
                "unresolved_conflicts": unresolved_conflicts,
                "circuit_open_models": cb_open_count,
                "redis_status": "ONLINE" if settings.USE_REDIS else "IN_MEMORY_FALLBACK",
                "database_status": "ONLINE",
                "worker_status": "IDLE",
                "status": "HEALTHY" if cb_open_count == 0 else "DEGRADED"
            }

            yield f"data: {json.dumps(payload)}\n\n"
        finally:
            db.close()

        await asyncio.sleep(3)

@router.get("/live-stream")
async def live_monitoring_stream(request: Request):
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
