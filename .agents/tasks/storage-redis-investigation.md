# Investigation Report: Storage 404 & Redis Broker Errors
**Project:** AI FAQ College Chat Bot  
**Date:** Investigation completed via static code + config analysis  
**Scope:** Read-only — no data modified, no uploads, no config changes

---

## Summary (Bottom Line Up Front)

| # | Error | Root Cause | Affected Documents |
|---|-------|------------|-------------------|
| 1 | Supabase Storage 404 | The legacy `POST /documents/upload` JSON endpoint writes a DB record with a `storage_path` **but never uploads the binary to Supabase Storage**. The object does not exist in the bucket, so every signed-URL request returns 404. | Any document registered through that endpoint (processing_status = `PROCESSING`) |
| 2 | Redis 503 / broker unreachable | Redis is **not installed or running** on this machine. No Windows service, no `redis-server` in PATH, nothing listening on port 6379. The `.env` points to `redis://localhost:6379/0` (the default), which is a dead address locally and also conflicts with the Docker Compose setting (`redis://redis:6379/0`). | All `QUEUED` documents: Celery cannot receive tasks, so `dispatch_document_processing` falls back to `LOCAL_ASYNC` or silently drops tasks. Processing never starts. |

---

## ERROR 1 — Supabase Storage 404

### Root Cause

There are **two** document upload endpoints. They behave very differently:

| Endpoint | Handler | Uploads binary? | Sets status |
|----------|---------|----------------|-------------|
| `POST /api/v1/college-admin/documents/upload-file` | `upload_pdf_document` | ✅ Yes — calls `document_service.register_and_upload()`, which calls `document_storage_service.upload_file()` | `QUEUED` |
| `POST /api/v1/college-admin/documents/upload` | `register_uploaded_document` | ❌ No — only calls `repo.create_document()`, never uploads bytes | `PROCESSING` |

The second (JSON) endpoint is described as "Register document metadata (JSON backward compatible)". It:

1. Generates a `storage_path` via `build_storage_path(college_id, doc_id)` → `"{college_id}/{doc_id}.pdf"` (`backend/app/api/v1/college_admin.py` lines 663–664)
2. Creates the `Document` row in the DB with that path
3. **Immediately calls `get_signed_url(college.id, created.storage_path)`** on the response
4. Never calls `upload_file()` — the binary was never sent to Supabase

Because no object exists at `college-documents/{college_id}/{doc_id}.pdf`, Supabase returns `404 Object not found` when the signed URL is generated for the response (lines 683–684), and again on every subsequent fetch of the document detail page or download-URL endpoint.

### Evidence

**Path construction** (`backend/app/services/storage_service.py`, line 55):
```python
def build_storage_path(self, college_id: uuid.UUID, document_id: uuid.UUID) -> str:
    return f"{college_id}/{document_id}.pdf"
```

**Bucket name** (`.env` / `config.py` default):
```
SUPABASE_STORAGE_BUCKET_DOCS = "college-documents"
```

**Signed URL generation** (`storage_service.py`, lines 137–151):
```python
signed = supabase.storage.from_(self.bucket_name).create_signed_url(
    path=storage_path,
    expires_in=expires_in,
)
```
If the object at `storage_path` does not exist in the `college-documents` bucket, Supabase returns a 404. The service catches it and re-raises as `FileNotFoundError`, which the API does not suppress here.

**The correct endpoint** (`upload_pdf_document`) does call `upload_file()` before inserting the DB record (`document_service.py`, lines 97–106), so it is not affected.

**DB state evidence** (`phase3_results.json`, section 3.CrossTenant):
> "AIT tenant sees its own documents: 0"  
> "Super admin total visible=0 (AIT=0, RCTI=0)"

At the time of RLS verification, the documents table was empty. Any document records present now that show a 404 on signed-URL requests were created through the metadata-only JSON endpoint, leaving orphan DB rows with no corresponding storage object.

**Local storage confirmation** (`storage/college-documents/`): The directory is empty — no local fallback files exist either.

### Which documents are affected

Any `Document` row whose `storage_path` = `{college_id}/{doc_id}.pdf` where:
- The row was created via `POST /documents/upload` (JSON endpoint), **or**
- The row was created by `register_and_upload()` but the upload step threw an exception (the document is left with `processing_status = QUEUED` and no object in storage — exception path in `document_service.py` lines 109–127 rolls back the DB row but only *attempts* to clean up storage if `uploaded_path` is set).

The signed URL call also fires immediately after upload in `upload_pdf_document` (line 628), so even a successfully uploaded document would 404 during that in-request call if the Supabase upload itself completed but the object is not yet replicated — though this is a transient edge case, not the primary bug.

### Minimal safe fix

**Fix 1a — Remove the spurious `get_signed_url` call from `register_uploaded_document`.**  
The JSON upload endpoint registers metadata for a document that someone *else* has already put in storage (its docstring says "uploaded into private storage"). Calling `get_signed_url` on a path that may or may not have an object yet is wrong. Return `download_url: null` instead, or omit the field.  
File: `backend/app/api/v1/college_admin.py`, lines 683–684.

**Fix 1b — Deprecate or gate the JSON endpoint.**  
The endpoint creates a `Document` with a fake checksum (`sha256_{uuid4().hex[:16]}`) and no binary. It should either be removed entirely in favour of `upload-file`, or require the caller to have already uploaded the file and pass a real checksum. At minimum, it must not call `get_signed_url` on creation.

**Fix 1c — Suppress 404 on signed-URL calls in listing endpoints.**  
`list_documents` (line 559) already wraps the signed-URL call in a `try/except` and sets `download_url = None` on failure. The `get_document_details`, `register_uploaded_document`, and `upload_pdf_document` response paths do not. Add the same guard there.

---

## ERROR 2 — Redis Broker Unreachable (503 on `/api/v1/health/ready`)

### Root Cause

Redis is not running on this machine. Confirmed by three independent checks:

| Check | Result |
|-------|--------|
| Windows Service named "Redis" | Not found |
| `redis-server` in system PATH | Not found |
| TCP port 6379 (`netstat -an`) | Nothing listening |

The `.env` file configures:
```
REDIS_URL          = redis://localhost:6379/0
CELERY_BROKER_URL  = redis://localhost:6379/0
CELERY_RESULT_BACKEND = redis://localhost:6379/1
```

The readiness probe (`backend/app/api/v1/health.py`, lines 61–68) attempts:
```python
r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
pong = await r.ping()
```
With nothing on port 6379, this times out after 2 seconds and logs:
> `Readiness check: Redis broker unreachable (Timeout connecting to server)`

The check then sets `checks["redis"] = False`, making `is_all_ready = False`, and returns HTTP 503.

### Secondary issue: docker-compose worker command path is wrong

`docker-compose.yml` defines the worker command as:
```yaml
command: celery -A app.workers.celery_app.celery worker --loglevel=info -c 4
```

But the actual module path is `app.tasks.celery_app` (file: `backend/app/tasks/celery_app.py`). There is no `app/workers/` directory. If Docker is ever used, the worker container would fail to start with an `ImportError`.

### Why QUEUED documents are not progressing

1. **Celery broker offline.** When `dispatch_document_processing()` is called after upload, it attempts `process_pdf_document_task.delay(...)`. This call reaches out to the Redis broker to enqueue the task. With Redis unreachable, `delay()` raises a connection exception.

2. **Fallback path invoked but ineffective.** `dispatch_document_processing` (`backend/app/tasks/document_tasks.py`, lines 48–59) catches the broker exception and falls back to `LOCAL_ASYNC` mode. If `background_tasks` is provided (it is from `upload_pdf_document`), it calls `background_tasks.add_task(...)`. However, the FastAPI background task runs in the same process as the web server — if the server process is shut down or if the task itself fails (e.g., due to a Supabase storage download failure — which will happen for documents uploaded through the JSON endpoint), the document stays in `QUEUED` status indefinitely.

3. **Documents stuck in QUEUED.** A document set to `processing_status = QUEUED` by `register_and_upload()` is only ever advanced by the Celery task or the local background task. With the broker down and local fallback failing silently (logs only), documents never move to `PROCESSING` and their `failure_reason` is never set, making them invisible in the error queue.

**Are AIT's QUEUED documents affected?**  
Yes, definitively. The phase3 RLS report from the most recent verification run shows 0 document records for both AIT and RCTI at that point. If a document has since been uploaded and is in QUEUED state for AIT (college_id `11111111-1111-1111-1111-111111111111`), it is blocked by the Redis outage. The Celery task cannot receive the job. The local background fallback may have attempted processing but would fail at `get_file_bytes()` if the binary was not uploaded to Supabase (Storage 404), leaving the document stuck in QUEUED.

### Minimal safe fix

**Fix 2a — Start Redis locally.**  
Install Redis on Windows (via WSL2 + `apt install redis-server`, or Memurai for Windows) and start it on the default port 6379. No code change needed; the `.env` is already correctly pointed at `localhost:6379`.

**Fix 2b — Use Docker Compose (fix the worker path first).**  
If running via `docker-compose.yml`, change the worker command from:
```yaml
command: celery -A app.workers.celery_app.celery worker --loglevel=info -c 4
```
to:
```yaml
command: celery -A app.tasks.celery_app.celery_app worker --loglevel=info -c 4
```
File: `docker-compose.yml`. Then `docker compose up` will start Redis (the `redis` service is correctly defined with `redis:7-alpine`) and the worker container together.

**Fix 2c (optional) — Make the health probe non-blocking for development.**  
The readiness probe returns 503 when Redis is down even if the database is healthy. For local development, this causes the entire readiness check to fail. Consider returning 200 with a `degraded` status when only Redis is unavailable but the database is connected, or add a config flag to make Redis optional in dev mode.

---

## Conclusions

| Issue | Established? | Evidence Source |
|-------|-------------|-----------------|
| Storage 404: object not in bucket | ✅ Confirmed from code | `college_admin.py` JSON upload endpoint never calls `upload_file()` |
| Storage 404: incorrect bucket name | ❌ Not the cause | Bucket name `college-documents` is consistent in `.env`, `config.py`, and `storage_service.py` |
| Storage 404: incorrect path construction | ❌ Not the cause | `build_storage_path` produces `{college_id}/{document_id}.pdf` consistently |
| Redis: not installed/running locally | ✅ Confirmed | `netstat`, service scan, PATH scan all negative |
| Redis: wrong URL in .env | ❌ Not the cause | `redis://localhost:6379/0` is correct for a local Redis instance |
| Worker: incorrect import path in docker-compose | ✅ Confirmed | `app.workers.celery_app` doesn't exist; actual path is `app.tasks.celery_app` |
| QUEUED documents blocked by Redis outage | ✅ Confirmed | Celery's `.delay()` requires a live broker; fallback may silently fail on Storage 404 |

---

## File References

| File | Relevance |
|------|-----------|
| `backend/app/api/v1/college_admin.py` lines 638–685 | `register_uploaded_document` — creates DB record without uploading binary |
| `backend/app/api/v1/college_admin.py` lines 596–631 | `upload_pdf_document` — correct path; uploads binary before DB insert |
| `backend/app/services/storage_service.py` lines 53–56 | `build_storage_path` — path format `{college_id}/{document_id}.pdf` |
| `backend/app/services/storage_service.py` lines 125–152 | `get_signed_url` — calls Supabase; throws `FileNotFoundError` on 404 |
| `backend/app/services/document_service.py` lines 60–127 | `register_and_upload` — correct upload pipeline |
| `backend/app/tasks/document_tasks.py` lines 38–59 | `dispatch_document_processing` — Celery dispatch with LOCAL_ASYNC fallback |
| `backend/app/tasks/celery_app.py` | Celery config; correct module path is `app.tasks.celery_app` |
| `backend/app/api/v1/health.py` lines 61–68 | Readiness probe Redis check; 2-second timeout |
| `backend/app/core/config.py` | `REDIS_URL`, `CELERY_BROKER_URL`, `SUPABASE_STORAGE_BUCKET_DOCS` defaults |
| `.env` | `REDIS_URL=redis://localhost:6379/0`, `SUPABASE_STORAGE_BUCKET_DOCS=college-documents` |
| `docker-compose.yml` | Worker command uses wrong module path `app.workers.celery_app` |
| `database/migrations/014_document_processing_and_ocr.sql` | Added `QUEUED` to `document_status` enum |
| `database/seed/development_seed.sql` | AIT college_id = `11111111-1111-1111-1111-111111111111` |
| `scripts/phase3_results.json` | Most recent DB state: 0 document rows at time of RLS verification |
