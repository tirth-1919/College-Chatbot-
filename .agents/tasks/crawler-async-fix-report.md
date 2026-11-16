# Crawler Async Event-Loop Fix — Report

Fixes unsafe `asyncio.run()` event-loop usage in `backend/app/tasks/crawler_tasks.py`
by reusing the existing persistent daemon-thread event-loop runner from
`document_tasks.py` (`run_async`).

## Context

- `document_tasks.py` already ships a working `run_async` implementation: a single
  long-lived event loop started on a background daemon thread
  (`_get_worker_loop` + `asyncio.run_coroutine_threadsafe`), so the SQLAlchemy async
  engine's pooled connections stay bound to a live loop for the lifetime of the
  worker process.
- `crawler_tasks.run_website_crawl_job` called `asyncio.run()` per Celery task,
  the same pattern that stranded pooled connections on closed loops and left jobs
  stuck mid-run in the document pipeline.
- The Windows Celery worker runs with `--pool=solo` and was already running
  successfully; this change brings the crawler task onto the same safe loop.

## Files changed

### 1. `backend/app/tasks/crawler_tasks.py`

- **Added import:** `from app.tasks.document_tasks import run_async`
  (reuses the existing runner — no second event-loop manager is created).
- **`run_website_crawl_job`:** replaced the unsafe
  `result = asyncio.run(crawler_service.execute_crawl_job(...))` with
  `result = run_async(crawler_service.execute_crawl_job(...))`.
  Added an explanatory comment block describing why the persistent loop is used.
- **Preserved behavior (unchanged):**
  - Retry: `self.retry(exc=exc, countdown=30)` with `max_retries=1` — untouched.
  - Task routing / queue name (`app.tasks.crawler_tasks.*` → `crawlers` queue in
    `celery_app.py`) — untouched.
  - Tenant isolation: `job_id`, `college_id`, `source_id` are still parsed and
    forwarded unchanged; `crawler_service.execute_crawl_job` still opens every
    session via `tenant_session(college_id=...)` and performs its own tenant /
    source validation and status transitions (RUNNING → COMPLETED / FAILED via
    `_fail_job`).
  - Database transaction handling: unchanged — all commits/rollbacks remain inside
    `crawler_service` and `tenant_session`.
  - Error handling / status transitions: unchanged. Exceptions from the
    coroutine still propagate to the task body (so retry still fires); service-level
    failures returned as `{"success": False, ...}` are still returned as-is.
- **Not changed:** `dispatch_crawl_job` and its `asyncio.create_task` fallback.
  That helper runs inside an already-running FastAPI event loop (it is called from
  an async route handler in `college_admin.py`), so `asyncio.create_task` operates on
  the correct loop. Replacing it with `run_async` would route work onto the worker's
  daemon loop — a different process — which would be wrong. The only unsafe
  `asyncio.run()` was in the synchronous Celery task body, which is what this fix
  addresses.
- `document_tasks.py` was **not** modified (it is already verified working).

### 2. `backend/tests/test_crawler_tasks_async.py` (new file)

Four mock-based tests (no live Redis / Supabase / DB):

1. `test_crawler_tasks_imports_shared_run_async` — asserts
   `crawler_tasks.run_async is document_tasks.run_async` (same function object, no
   duplicate) and that `crawler_tasks` defines no `_worker_loop` / `_get_worker_loop`.
2. `test_run_website_crawl_job_reuses_persistent_loop_and_runs_coroutine` — runs the
   task twice on the real shared `run_async`; asserts the same loop object is reused
   across both runs (not closed, not recreated), that the coroutine actually runs to
   completion (status-update side effect recorded each time, not silently dropped),
   that tenant IDs pass through unchanged, and that `asyncio.run` is never called
   (guarded to fail loudly on regression).
3. `test_run_website_crawl_job_failure_propagates_and_retries` — a coroutine failure
   propagates to the task body and triggers `self.retry(exc, countdown=30)`; nothing
   is swallowed.
4. `test_run_website_crawl_job_surfaces_service_failure_without_retry` — a
   `{"success": False}` service result is returned as-is (not swallowed, not
   retried), matching the existing terminal-failure handling.

## `run_async` import location

Imported from `app.tasks.document_tasks` (the module that defines and owns the
persistent-loop runner). Verified by `test_crawler_tasks_imports_shared_run_async`:
the imported symbol is the exact same function object as
`document_tasks.run_async`, and no second loop manager exists in `crawler_tasks`.

## Test results

Python: 3.13.14, pytest 8.3.4, pytest-asyncio 1.4.0 (asyncio_mode=auto, `pythonpath=backend`).

| Scope | Command | Result |
|---|---|---|
| New crawler async tests | `pytest backend/tests/test_crawler_tasks_async.py -v` | **4 passed** (0 warnings, exit 0) |
| Document task tests (regression) | `pytest backend/tests/test_document_upload_and_processing.py -v` | **16 passed**, 2 pre-existing warnings |
| Health + crawler SSRF | `pytest backend/tests/test_health.py backend/tests/test_crawler_ssrf_security.py -v` | **9 passed** |
| Full backend suite | `pytest backend/tests -q` | **85 passed, 0 failed**, 2 pre-existing warnings |

- Focused crawler run is clean: `4 passed in 4.52s` with no warnings.
- The 2 warnings in the full/document runs are pre-existing and unrelated to this
  change:
  - `test_register_uploaded_document_requires_checksum`: a Starlette
    `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning.
  - `test_reprocess_document_missing_storage_returns_null_url`: an
    `execute_document_processing` coroutine never awaited by that test's own mocks.
  - (stderr-only) `Connection._cancel was never awaited` from the health tests' async
    DB mocks.
- No failures.

## Remaining risks

- **`dispatch_crawl_job`'s `asyncio.create_task` fallback** (reached only when the
  broker is down and no `background_tasks` is passed). It is a fire-and-forget
  coroutine scheduled on the route handler's loop, which can in principle be dropped
  during loop shutdown. Left unchanged deliberately to preserve existing behavior;
  in the live code path the broker-down branch is taken from an async route that
  passes `background_tasks`, so the `background_tasks.add_task` path is used. A
  future hardening could mirror `document_tasks.dispatch_document_processing` and
  await a status update rather than fire-and-forget, but that is a behavior change
  out of scope for this fix.
- This fix is covered by unit tests with mocks only; it has **not** been verified
  against a live Celery worker / Redis / Supabase in this step (per the safety
  constraints — no live services, no real crawls).
- No git repository is present in the workspace, so no commit was made; the change
  is left as working-tree edits to `crawler_tasks.py` plus the new test file.
