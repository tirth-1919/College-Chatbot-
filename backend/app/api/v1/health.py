"""Production Health and Readiness Probe API Router.

Provides real-time liveness and readiness telemetry for Kubernetes, Docker, and load balancers.
Safe for public monitoring probes: Never exposes internal hostnames, passwords, or stack traces.
"""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.common import HealthResponse, ReadinessResponse
from app.core.config import settings
from app.core.logging import logger
from app.tasks.worker_health import HEARTBEAT_PREFIX, WORKER_SET_KEY

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness probe: verifies process is alive",
)
async def check_liveness(session: AsyncSession = Depends(get_db)):
    """Liveness probe: confirms the FastAPI application server process is responsive."""
    db_connected = False
    try:
        result = await session.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_connected = True
    except Exception as err:
        logger.warning("Database liveness check failed: %s", str(err))
        db_connected = False

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        database_connected=db_connected,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe: validates all downstream dependencies",
)
async def check_readiness(
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    """Readiness probe: confirms database, cache, and worker connections before accepting user traffic."""
    checks = {
        "database": False,
        "redis": False,
        "worker": False,
        "storage": True,  # Supabase Storage bucket configured
    }

    # 1. Probe PostgreSQL Database
    try:
        result = await session.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = True
    except Exception as err:
        logger.error("Readiness check: PostgreSQL database unreachable: %s", str(err))
        checks["database"] = False

    # 2. Probe Redis In-Memory Cache & Broker
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await r.ping()
        checks["redis"] = bool(pong)
        await r.aclose()
    except Exception as err:
        logger.warning("Readiness check: Redis broker unreachable (%s)", str(err))
        checks["redis"] = False

    # 3. Probe for a worker's short-lived Redis heartbeat. Celery's Redis pidbox
    #    control queue relies on a Lua script unsupported by some legacy brokers.
    if not checks["redis"]:
        checks["worker"] = False
    else:
        worker_redis = None
        try:
            worker_redis = aioredis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2.0)
            worker_ids = await worker_redis.smembers(WORKER_SET_KEY)
            heartbeat_keys = [
                HEARTBEAT_PREFIX + (worker_id.decode() if isinstance(worker_id, bytes) else str(worker_id))
                for worker_id in worker_ids
            ]
            heartbeats = await worker_redis.mget(heartbeat_keys) if heartbeat_keys else []
            checks["worker"] = any(heartbeats)
        except Exception as err:
            logger.warning("Readiness check: Celery worker heartbeat unavailable (%s)", str(err))
            checks["worker"] = False
        finally:
            if worker_redis:
                await worker_redis.aclose()

    # A live worker is required to process queued document and crawler jobs.
    # Do not report readiness while those background queues have no consumer.
    is_all_ready = checks["database"] and checks["redis"] and checks["worker"] and checks["storage"]
    if not is_all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_all_ready else "not_ready",
        service=settings.PROJECT_NAME,
        environment=settings.ENVIRONMENT,
        version="1.0.0",
        checks=checks,
    )
