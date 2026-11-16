# FIX 4 Review — Processing Failure Reliability (asyncio loop safety) — Pass 2

## Evidence sources
- `backend/app/tasks/document_tasks.py` — read directly (no git history)
- `backend/tests/test_document_upload_and_processing.py` — read directly
- `backend/app/api/v1/college_admin.py` — caller verification
- `backend/app/tasks/celery_app.py` — worker pool configuration
- Prior review: `.agents/tasks/followup-fixes/fix4-review.json` (CHANGES_REQUESTED, blocker F1)
- Recorded test results: 73 passed on initial run; prior review noted prior tests did not cover the async-caller path

---

## Prior blocker — F1 disposition

F1 (previous pass): `_run_mark_failed_sync` called `loop.run_until_complete()` on the already-running FastAPI event loop, unconditionally raising `RuntimeError` and silently dropping the FAILED status update.

**Current code — F1 is resolved.** The `loop.run_until_complete()` branch no longer exists. The fix took the alternative approach recommended by the prior review:

1. `dispatch_document_processing` is now declared `async def` (line 110).
2. In the broker-failure path it directly `await`s `_mark_document_failed(document_id, college_id, reason)` (lines 143–150).
3. Both callers in `college_admin.py` (lines 622 and 880) use `await dispatch_document_processing(...)`.
4. `_run_mark_failed_sync` now only calls `asyncio.run(_mark_document_failed(...))` — the safe path for the Celery synchronous task context (prefork workers, no running event loop).

No `get_running_loop`, no `run_until_complete`, no `ensure_future` anywhere in the file.

---

## Requirement-by-requirement findings

### Req 1 — `asyncio.ensure_future()` removed
PASS. The string `ensure_future` does not appear as executable code anywhere in `document_tasks.py`. The only reference is a comment at lines 140–142 documenting its intentional removal.

### Req 2 — Guard pattern for `_mark_document_failed`
The requirement specifies the guard: `try: loop = asyncio.get_running_loop() except RuntimeError: loop = None` with `loop.run_until_complete()` if running, `asyncio.run()` if not.

The implementation takes the alternative approach: `dispatch_document_processing` is `async` and awaits `_mark_document_failed` directly, so the guard is not needed in the dispatch path. `_run_mark_failed_sync` is only called from the synchronous Celery task (`process_pdf_document_task`, a sync function run by a prefork worker with no running event loop), where `asyncio.run()` is safe and correct. The prior review explicitly recommended this alternative. The intent of the requirement — no unsafe event-loop nesting — is fully satisfied. The specific guard form in the requirement is not needed and would itself have been the broken code that prior review flagged.

PASS (by alternative implementation achieving the same safety guarantee).

### Req 3 — Retry behavior preserved
PASS. `process_pdf_document_task` retains `max_retries=2` and `raise self.retry(exc=exc, countdown=15)` (lines 36 decorator, 74). No change to retry semantics.

### Req 4 — Tenant isolation preserved
PASS. `_mark_document_failed` uses `tenant_session(college_id=college_id)` and fetches the document with `session.get(Document, document_id)` — the same `college_id` and `document_id` received as arguments. No cross-tenant query or hardcoded college ID introduced. Test 11a and 11d both assert `col_id == college_id` explicitly.

### Req 5 — Exhausted retries → FAILED with `failure_reason`
PASS. `_mark_document_failed` sets `doc.processing_status = "FAILED"` and `doc.failure_reason = reason` before every `self.retry()` call. When retries are exhausted, Celery re-raises `MaxRetriesExceededError`; the last call to `_run_mark_failed_sync` before that point has already written the reason. Test 11c confirms this path.

### Req 6 — Tests

| Test | Covers | Assessment |
|------|--------|------------|
| `test_dispatch_broker_failure_sets_failed_synchronously` (11a) | broker failure → FAILED set before dispatch returns, correct IDs | PASS |
| `test_celery_task_sets_failed_before_retry` (11b) | retry path → `_run_mark_failed_sync` called with correct IDs and "Task execution error" reason | PASS. Patch layering is correct: `_run_mark_failed_sync` patched independently of `asyncio.run`. |
| `test_celery_task_exhausted_retries_ends_in_failed` (11c) | `MaxRetriesExceededError` → `_run_mark_failed_sync` called, failure_reason non-empty | PASS |
| `test_dispatch_broker_failure_from_async_context_sets_failed` (11d) | **FastAPI async-caller path** (loop is running) → `_mark_document_failed` awaited, tenant isolation asserted | PASS. This is the previously missing test; it calls `dispatch_document_processing` from an `@pytest.mark.asyncio` function and asserts the loop is running before dispatch. |

All four tests cover the requirements. The previously missing async-context test (11d) is present and structurally correct.

---

## Summary

The prior F1 blocker is resolved. `loop.run_until_complete()` is gone; `dispatch_document_processing` is async and directly awaits the status update; `_run_mark_failed_sync` is only used from the Celery sync context where `asyncio.run()` is safe. All six requirements are met. No new blockers found.
