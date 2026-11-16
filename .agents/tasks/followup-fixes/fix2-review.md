# FIX 2 Review — Real Celery Worker Availability Check
**File:** `backend/app/api/v1/health.py`, `backend/tests/test_health.py`
**Review pass:** First pass

---

## Evidence Summary

No git history is available. Review is based on direct file inspection of the current state of `health.py` and `test_health.py`, the coder's self-recorded result in `.agents/tasks/followup-fixes/fix2-review.json` (75 passed, 0 failed), and the prior implementation report in `.agents/tasks/storage-redis-fix-report.md`.

---

## Requirement-by-Requirement Analysis

### Req 1 — `checks["worker"]` is NOT `checks["redis"]` (proxy removed)

**PASS.**  
`health.py` lines 72–98: `checks["worker"]` is set by an independent branch. When Redis passes, it performs `celery_app.control.ping(timeout=1.0)` via executor and sets `checks["worker"] = bool(ping_response)`. The old proxy assignment `checks["worker"] = checks["redis"]` noted as Remaining Risk #5 in the prior report is gone.

### Req 2 — Worker check uses `celery_app.control.ping(timeout=1.0)` with ≤2s total timeout

**PASS.**  
`health.py` lines 86–97:
```python
from app.tasks.celery_app import celery_app
loop = asyncio.get_event_loop()
ping_response = await asyncio.wait_for(
    loop.run_in_executor(
        None,
        lambda: celery_app.control.ping(timeout=1.0),
    ),
    timeout=2.0,
)
```
Celery-side timeout is 1.0 s; hard cap via `asyncio.wait_for` is 2.0 s. Both are within the ≤2 s requirement.

### Req 3 — Redis unreachable → Celery ping skipped, `worker` is `false`

**PASS.**  
`health.py` lines 72–74:
```python
if not checks["redis"]:
    checks["worker"] = False
else:
    # ... ping ...
```
When Redis is down, the entire Celery branch is skipped and `worker` is set to `False` directly.

### Req 4 — Check runs in a thread or with `asyncio.wait_for` — not blocking the event loop

**PASS.**  
`loop.run_in_executor(None, lambda: celery_app.control.ping(timeout=1.0))` offloads the synchronous `control.ping` call to the default thread pool. The result is awaited via `asyncio.wait_for`, so the event loop remains unblocked during the ping.

One minor observation: `asyncio.get_event_loop()` is deprecated inside async functions from Python 3.10 onward; `asyncio.get_running_loop()` is the correct call. In practice, within an async context under uvicorn, `get_event_loop()` returns the running loop, so behavior is identical. The tests pass and no incorrect behavior results. This is a code-style issue, not a correctness blocker.

### Req 5 — Tests: empty ping `{}` → `worker: false`; populated ping → `worker: true`

**PASS for `worker: false` test.**  
`test_readiness_worker_false_when_no_workers_respond` (test_health.py lines 32–62): patches both `"app.api.v1.health.celery_app"` (with `create=True`) and `"app.tasks.celery_app.celery_app"`. Mock's `control.ping.return_value = {}`. Asserts `data["checks"]["worker"] is False`. `bool({})` is `False`. Correct.

**PASS for `worker: true` test.**  
`test_readiness_worker_true_when_worker_responds` (test_health.py lines 65–99): patches `"app.tasks.celery_app.celery_app"` only. Mock's `control.ping.return_value = {"celery@worker1": {"ok": "pong"}}`. Because `health.py` performs a **deferred local import** (`from app.tasks.celery_app import celery_app` inside the function body), the patch on the module attribute is picked up at call time — the mock is used correctly. `bool({"celery@worker1": ...})` is `True`. Asserts `data["checks"]["worker"] is True`. Correct.

Both tests are recorded as passing in the coder's evidence (75 passed, 0 failed).

### Req 6 — Liveness endpoint (`GET /health`) is unchanged

**PASS.**  
`health.py` lines 18–38: `check_liveness` is unmodified. It returns `HealthResponse` with only `database_connected` — no `worker` key. The readiness endpoint at `GET /health/ready` is what was changed. `test_health_endpoint` (test_health.py line 22) continues to test the liveness endpoint and passes.

---

## Blockers

None.

---

## Verdict

APPROVED — all six requirements are satisfied. The proxy check is replaced by a real `control.ping(timeout=1.0)` call in a thread executor, Redis-down short-circuits correctly, the event loop is not blocked, both required tests exist and pass, and the liveness endpoint is unchanged.
