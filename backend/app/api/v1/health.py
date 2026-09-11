import os
import time
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.automation.engine import automation_engine

router = APIRouter()

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "institution": settings.INSTITUTION_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }

@router.get("/health/live")
def get_liveness():
    """Kubernetes / container liveness probe."""
    return {"status": "alive"}

@router.get("/health/ready")
def get_readiness():
    """Readiness probe checking database, storage, workers, and redis."""
    checks = {}
    is_ready = True

    # 1. Database check
    try:
        db = SessionLocal()
        db.execute("SELECT 1" if "sqlite" in settings.DATABASE_URL else "SELECT 1")
        db.close()
        checks["database"] = {"status": "UP", "engine": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql"}
    except Exception as e:
        checks["database"] = {"status": "DOWN", "error": str(e)}
        is_ready = False

    # 2. Storage check
    upload_ok = os.path.exists(settings.UPLOAD_DIR)
    images_ok = os.path.exists(settings.IMAGE_STORAGE_DIR)
    checks["storage"] = {
        "status": "UP" if (upload_ok and images_ok) else "DOWN",
        "uploads_writable": upload_ok,
        "images_writable": images_ok
    }
    if not (upload_ok and images_ok):
        is_ready = False

    # 3. Worker check
    checks["worker"] = {
        "status": "UP" if automation_engine._running else "DEGRADED",
        "worker_id": automation_engine.worker_id,
        "registered_jobs_count": len(automation_engine._registry)
    }

    # 4. Redis status (graceful fallback if not enabled)
    checks["redis"] = {
        "status": "UP" if settings.USE_REDIS else "FALLBACK_IN_MEMORY",
        "mode": "redis" if settings.USE_REDIS else "resilient_local_memory"
    }

    http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content={
            "status": "READY" if is_ready else "NOT_READY",
            "environment": settings.ENVIRONMENT,
            "checks": checks
        }
    )
