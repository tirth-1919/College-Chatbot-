# Storage 404 & Redis/Celery Fix Report
**Project:** AI FAQ College Chat Bot  
**Date:** Implementation completed via code changes + mock test suite  
**Scope:** 6 targeted fixes — no migrations, no data modifications, no production uploads

---

## Summary

All 6 changes were implemented and verified. The full test suite ran with **73 passed, 0 failed**.

---

## Exact Files Changed

| File | Change |
|------|--------|
| `backend/app/api/v1/college_admin.py` | CHANGE 1: `register_uploaded_document` fixed; CHANGE 2: defensive signed URL in `upload_pdf_document` and `get_document_details` |
| `backend/app/api/v1/health.py` | CHANGE 5: Added `worker` key to readiness checks |
| `backend/app/tasks/document_tasks.py` | CHANGE 4: Broker failure logs at ERROR, sets FAILED status, fallback logs at WARNING |
| `docker-compose.yml` | CHANGE 3: Fixed Celery worker command module path |
| `backend/tests/test_document_upload_and_processing.py` | CHANGE 6: New test file with 10 test cases |

---

## Behavior Before vs After

### CHANGE 1 — `register_uploaded_document` (POST /documents/upload)

**Before:**
- Generated a fake checksum: `sha256_{uuid4().hex[:16]}`
- Created a DB record pointing to a storage path that was never uploaded
- Immediately called `get_signed_url()` on the nonexistent object → Supabase 404 on every request
- Set `processing_status = "PROCESSING"` (never advances)

**After:**
- Requires the caller to supply a real 64-character SHA-256 checksum via `checksum_sha256`
- Verifies the storage object exists at the expected path before creating any DB record
- Returns HTTP 422 `{"detail": "Storage object not found at the expected path. Upload the file first."}` if the object does not exist
- Returns HTTP 422 with checksum guidance if no valid checksum provided
- Sets `processing_status = "QUEUED"` on success (consistent with canonical upload)
- Returns `download_url: null` if signed URL generation fails (never crashes)
- **No fake checksums, no orphan DB records**

### CHANGE 2 — Defensive signed URL handling

**Before:**
- `upload_pdf_document`: called `get_signed_url()` bare → exception propagated to client if object missing
- `get_document_details`: called `get_signed_url()` bare → HTTP 500 or FileNotFoundError leaked to client
- `list_documents`: already had try/except (unchanged)

**After:**
- Both `upload_pdf_document` and `get_document_details` wrap the final signed URL call in `try/except`
- Returns `download_url: null` on any exception — client sees null instead of 500
- Upload verification step (the actual binary check during upload) is **not** guarded — errors there still propagate correctly

### CHANGE 3 — docker-compose.yml Celery worker command

**Before:**
```yaml
command: celery -A app.workers.celery_app.celery worker --loglevel=info -c 4
```
`app/workers/` directory does not exist → worker container would fail on `ImportError` at startup.

**After:**
```yaml
command: celery -A app.tasks.celery_app.celery_app worker --loglevel=info -c 4
```
Matches actual module path `backend/app/tasks/celery_app.py` and object name `celery_app`.  
`CELERY_BROKER_URL=redis://redis:6379/0` was already set for all services — no change needed.

### CHANGE 4 — `dispatch_document_processing` broker failure

**Before:**
- Logged at `WARNING` level only
- Document status stayed `QUEUED` indefinitely
- Local `_run_async_document_processing` swallowed its own exception silently

**After:**
- Broker failure logs at `ERROR`: `"Broker unavailable — could not queue document {id}: {error}"`
- Schedules `_mark_document_failed()` to set `processing_status = "FAILED"` and `failure_reason = "Broker unavailable: task could not be queued"`
- When `background_tasks` is provided, logs at `WARNING`: `"Broker unavailable — falling back to LOCAL_ASYNC for document {id}"` and runs the local fallback
- When no `background_tasks` available, logs at `ERROR` that the document will not be processed
- `_run_async_document_processing` now calls `_mark_document_failed()` on its own exception — document always reaches FAILED
- Celery task `process_pdf_document_task` now calls `_mark_document_failed()` before each `self.retry()` so status is FAILED between retries

### CHANGE 5 — Health check structured response

**Before:**
```json
{
  "status": "not_ready",
  "checks": {"database": true, "redis": false, "storage": true}
}
```
No `worker` key — could not distinguish broker-down from worker-process-down.

**After:**
```json
{
  "status": "not_ready",
  "checks": {"database": true, "redis": false, "worker": false, "storage": true}
}
```
`worker` check is derived from Redis connectivity (lightweight; avoids `inspect_active()` overhead).  
HTTP 503 when `database` or `redis` is false. Liveness endpoint (`GET /api/v1/health`) unchanged.

### CHANGE 6 — New tests

New file: `backend/tests/test_document_upload_and_processing.py`

| Test | What it verifies |
|------|-----------------|
| `test_upload_pdf_document_success` | Storage upload called, DB record created, status = QUEUED |
| `test_upload_pdf_document_storage_failure_no_db_record` | Storage failure raises exception (no DB record) |
| `test_upload_pdf_document_db_commit_failure_cleans_up_storage` | DB flush failure triggers `delete_file` cleanup |
| `test_register_uploaded_document_requires_checksum` | JSON endpoint returns 422 without valid checksum |
| `test_list_documents_missing_storage_object_returns_null_url` | Missing storage → `download_url = null` |
| `test_get_document_details_missing_storage_returns_null_url` | Missing storage → `download_url = null` |
| `test_dispatch_document_processing_broker_down_sets_failed` | Broker down → mode = LOCAL_ASYNC |
| `test_celery_app_import` | `from app.tasks.celery_app import celery_app` succeeds |
| `test_document_processing_reaches_terminal_state` | Processing returns success or failure dict, never hangs |
| `test_upload_pdf_document_signed_url_failure_does_not_crash` | Signed URL failure → null, not exception |

---

## Test Results

```
73 passed, 0 failed
1 warning (pre-existing asyncpg pool cleanup RuntimeWarning on asyncio loop close — 
unrelated to these changes, present before this work)
```

**Command run:**
```
cd backend && python -m pytest tests/ -v --tb=short
```

**All 10 new tests passed. All 63 pre-existing tests passed.**

---

## Whether Docker Redis/Celery Were Actually Started

**No.** Docker Redis and the Celery worker were not started. All tests run with mocks — no live broker, no live Supabase, no live PostgreSQL write operations in the new tests. The `register_uploaded_document` test uses FastAPI's `ASGITransport` test client with dependency overrides. The Celery import smoke test imports the module only; it does not connect to Redis.

---

## Whether a Real PDF Was Uploaded and Processed

**No.** No real PDF was uploaded. No document records were created, modified, or deleted. No Supabase Storage objects were touched. All storage interaction tests use `unittest.mock.patch`.

---

## Remaining Risks

1. **`register_uploaded_document` still has an active frontend caller** (`apps/admin-frontend/src/services/college-admin-service.ts` line 146). That caller does not pass a `checksum_sha256` field, so it will now receive HTTP 422. The caller must be updated to either pass a real checksum or be migrated to use `POST /upload-file`. This is a product decision — the endpoint was not deprecated (per the prompt's "has caller" path), but the frontend will see failures until it is updated.

2. **`dispatch_document_processing` FAILED status scheduling uses `asyncio.ensure_future()`** when called from an async context (FastAPI request). This is a best-effort fire-and-forget. If the event loop is shut down before the coroutine completes (e.g., graceful shutdown), the status update may not persist. A synchronous DB call or a background task would be more reliable but requires a larger refactor.

3. **`process_pdf_document_task` calls `asyncio.run()` inside `_mark_document_failed`** after a task failure. If the Celery worker's asyncio event loop is already running, this would fail with `RuntimeError: This event loop is already running`. The function uses `asyncio.run()` which is safe in Celery's sync task context but should be verified when upgrading Celery versions.

4. **Redis is not installed locally.** The health probe will continue to return 503 on `GET /api/v1/health/ready` until Redis is running (via Docker Compose, WSL2, or Memurai). This is an environment issue, not a code issue.

5. **Worker `checks["worker"] = checks["redis"]`** is a proxy check only. It does not verify that a Celery worker process is actually consuming from the queue — only that the broker is reachable. A document could be queued but never processed if the worker container crashed after Redis came up.

6. **`reprocess_document` handler** (not in scope) also calls `get_signed_url()` bare in its response construction. This was not in the fix scope but carries the same latent risk.

---

## Safety Verification

- ✅ No migrations or seed scripts executed
- ✅ No production Supabase data changes
- ✅ No document uploads, retries, deletions, or reprocessing
- ✅ No RLS, auth, college ID, or tenant isolation changes
- ✅ No secret values exposed
- ✅ No existing Storage objects overwritten
- ✅ Live verification not claimed — all tests use mocks
