"""Performance, Latency & Telemetry Automated Test Suite.

Measures:
  - API endpoint response times across repeated iterations (p50, p95, max).
  - Database connection pool checkout and query round-trip latency.
  - Server hardware resource utilization (CPU, RAM) using `psutil`.
  - Enforces configurable SLA thresholds.
"""

import time
import psutil
from typing import List, Dict, Any
from httpx import AsyncClient, ASGITransport
from tests.config import PERFORMANCE_THRESHOLDS, ASYNC_APP_URL
from app.main import app
import asyncpg


async def run_performance_suite() -> List[Dict[str, Any]]:
    """Executes performance benchmark suite."""
    results = []

    # 1. Health Endpoint Latency (10 samples)
    latencies = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(10):
            t0 = time.perf_counter()
            res = await client.get("/api/v1/health")
            dur_ms = (time.perf_counter() - t0) * 1000
            if res.status_code == 200:
                latencies.append(dur_ms)

    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0.0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0

    threshold = PERFORMANCE_THRESHOLDS["health_check_max_ms"]
    passed = p95 < threshold
    results.append({
        "category": "Performance",
        "name": f"API Health Check Latency Benchmark (SLA < {threshold}ms)",
        "target": "GET /api/v1/health",
        "status": "PASS" if passed else "WARN",
        "duration_ms": p95,
        "detail": f"p50: {p50:.1f}ms, p95: {p95:.1f}ms, max: {max_lat:.1f}ms across 10 samples",
    })

    # 2. Database Connection Checkout & Query Latency
    db_conn_str = ASYNC_APP_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    db_latencies = []
    try:
        conn = await asyncpg.connect(db_conn_str)
        for _ in range(5):
            t0 = time.perf_counter()
            await conn.fetchval("SELECT 1")
            dur = (time.perf_counter() - t0) * 1000
            db_latencies.append(dur)
        await conn.close()

        db_latencies.sort()
        db_p50 = db_latencies[len(db_latencies) // 2]
        db_max = max(db_latencies)
        db_thresh = PERFORMANCE_THRESHOLDS["db_query_max_ms"]
        results.append({
            "category": "Performance",
            "name": f"Database Round-Trip Query Benchmark (SLA < {db_thresh}ms)",
            "target": "SELECT 1",
            "status": "PASS" if db_p50 < db_thresh else "WARN",
            "duration_ms": db_p50,
            "detail": f"p50: {db_p50:.1f}ms, max: {db_max:.1f}ms across 5 queries",
        })
    except Exception as e:
        results.append({
            "category": "Performance",
            "name": "Database Round-Trip Query Benchmark",
            "target": "SELECT 1",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": str(e),
        })

    # 3. System Hardware Resource Utilization
    t0 = time.perf_counter()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    dur = (time.perf_counter() - t0) * 1000

    cpu_ok = cpu_percent < PERFORMANCE_THRESHOLDS["cpu_max_percent"]
    ram_ok = ram.percent < PERFORMANCE_THRESHOLDS["ram_max_percent"]
    all_ok = cpu_ok and ram_ok

    results.append({
        "category": "Performance",
        "name": "Host Hardware Resource Telemetry (CPU & RAM Health)",
        "target": "psutil hardware probe",
        "status": "PASS" if all_ok else "WARN",
        "duration_ms": dur,
        "detail": f"CPU Usage: {cpu_percent:.1f}% (limit: {PERFORMANCE_THRESHOLDS['cpu_max_percent']}%), RAM Usage: {ram.percent:.1f}% ({ram.used // (1024*1024)}MB / {ram.total // (1024*1024)}MB)",
    })

    return results

