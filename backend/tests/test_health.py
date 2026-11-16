"""Backend Health & FastAPI Startup Unit Tests."""

import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Verify that the root endpoint returns 200 OK with documentation links."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "documentation" in data
        assert "health_check" in data


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify that the health check endpoint returns JSON with database status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database_connected" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_readiness_worker_false_when_no_workers_respond():
    """Celery ping returns {} (empty dict) → worker: false in readiness response."""
    mock_celery = MagicMock()
    # ping() returning an empty dict means no workers replied.
    mock_celery.control.ping.return_value = {}

    with (
        patch("redis.asyncio.from_url") as mock_redis_factory,
        patch("app.api.v1.health.celery_app", mock_celery, create=True),
        patch("app.tasks.celery_app.celery_app", mock_celery),
    ):
        mock_redis_instance = MagicMock()
        mock_redis_instance.ping = pytest.approx  # replaced below
        # Make the async ping return True so redis check passes.
        import asyncio

        async def _fake_ping():
            return True

        async def _fake_aclose():
            return None

        mock_redis_instance.ping = _fake_ping
        mock_redis_instance.aclose = _fake_aclose
        mock_redis_factory.return_value = mock_redis_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")

        data = response.json()
        assert "checks" in data
        # An empty ping response means no live worker → must be false.
        assert data["checks"]["worker"] is False


@pytest.mark.asyncio
async def test_readiness_worker_true_when_worker_responds():
    """Celery ping returns a non-empty dict → worker: true in readiness response."""
    mock_celery = MagicMock()
    # ping() returning a dict with at least one entry means a worker replied.
    mock_celery.control.ping.return_value = {"celery@worker1": {"ok": "pong"}}

    with (
        patch("redis.asyncio.from_url") as mock_redis_factory,
        patch("app.tasks.celery_app.celery_app", mock_celery),
    ):
        import asyncio

        async def _fake_ping():
            return True

        async def _fake_aclose():
            return None

        mock_redis_instance = MagicMock()
        mock_redis_instance.ping = _fake_ping
        mock_redis_instance.aclose = _fake_aclose
        mock_redis_factory.return_value = mock_redis_instance

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")

        data = response.json()
        assert "checks" in data
        # A worker replied → must be true.
        assert data["checks"]["worker"] is True

