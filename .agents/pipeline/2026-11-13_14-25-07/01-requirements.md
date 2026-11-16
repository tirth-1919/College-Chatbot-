# Requirements Document: Fix PDF Storage 404 and Redis/Celery Processing

**Project:** AI FAQ College Chat Bot  
**Date:** 2026-11-13  
**Type:** Bug Fix / Configuration Correction  
**Scope:** Code defects in document upload endpoints and Celery/Redis configuration

---

## Summary

Fix two confirmed code/configuration problems that prevent PDF document processing:

1. **Supabase Storage 404 Error**: The metadata-only JSON endpoint (`POST /api/v1/college-admin/documents/upload`) creates database records with generated `storage_path` values but never uploads the binary to Supabase Storage, then immediately attempts to generate signed URLs for non-existent objects, causing 404 errors.

2. **Redis/Celery Configuration Error**: Redis is not running locally (`redis://localhost:6379/0` unreachable), and `docker-compose.yml` contains an incorrect Celery module path (`app.workers.celery_app` instead of `app.tasks.celery_app.celery_app`), preventing document processing tasks from being queued or executed.

These fixes restore reliable PDF upload, storage, and background processing while preserving tenant isolation, RLS policies, and existing safe upload sequences.

---

## Functional Requirements

### FR-1: Metadata-Only Upload Endpoint Fix

**FR-1.1** The `POST /api/v1/college-admin/documents/upload` endpoint (handler: `register_uploaded_document`) must not create database records that reference non-existent Supabase Storage objects.

**FR-1.2** The endpoint must not call `get_signed_url()` on the creation response path (lines 683-684 in `college_admin.py`). Return `download_url: null` instead.

**FR-1.3** Choose one of three safe resolution paths:
- **Option A (Preferred if no callers exist)**: Deprecate the endpoint. Return HTTP 410 Gone with a message directing callers to use `/upload-file` instead. Do not create any database record.
- **Option B (If backward compatibility is required)**: Require the caller to supply a real `checksum` (not a generated fake like `sha256_{uuid4().hex[:16]}`). Verify that an object with the specified `storage_path` actually exists in Supabase Storage before creating the database record. Return HTTP 422 Unprocessable Entity with a clear error message if the object does not exist or if the checksum is a generated fake pattern.
- **Option C (Minimum viable fix)**: Remove only the `get_signed_url()` call from the response construction. Return `download_url: null`. Log a WARNING that the endpoint creates unverified metadata records. This does not prevent orphan DB records but stops the 404 crash.

**FR-1.4** The binary upload endpoint `POST /api/v1/college-admin/documents/upload-file` (handler: `upload_pdf_document`) must remain unchanged. Its safe upload sequence (auth → college_id resolution → PDF validation → binary upload → confirm upload success → DB insert → cleanup on DB failure) must be preserved.

**FR-1.5** A generated `storage_path` must never be treated as proof that a file exists in storage.

**Assumption**: The investigation report does not identify any active callers of the metadata-only endpoint. This requirement assumes Option A (deprecation) is the safest default unless the design phase identifies backward compatibility requirements.

---

### FR-2: Signed URL Error Handling

**FR-2.1** The `get_document_details` endpoint must not crash when `get_signed_url()` raises `FileNotFoundError` for a missing storage object. Wrap the signed URL call in a `try/except` block and return `download_url: null` on failure.

**FR-2.2** The `upload_pdf_document` endpoint response construction (after successful DB commit) must not crash when `get_signed_url()` raises `FileNotFoundError`. Wrap the signed URL call in a `try/except` block and return `download_url: null` on failure. Do not suppress exceptions during the upload verification itself — only during response building.

**FR-2.3** The `list_documents` endpoint already handles signed URL exceptions correctly (lines 559-564 in `college_admin.py`). This pattern must be replicated in FR-2.1 and FR-2.2.

**FR-2.4** The exception handling must log the failure at WARNING level with the document ID and storage path for diagnostic purposes.

---

### FR-3: Docker Compose Celery Worker Path

**FR-3.1** The `docker-compose.yml` worker service command must be corrected from:
```yaml
command: celery -A app.workers.celery_app.celery worker --loglevel=info -c 4
```
to:
```yaml
command: celery -A app.tasks.celery_app.celery_app worker --loglevel=info -c 4
```

**FR-3.2** The corrected module path must match the actual Celery application object location: `backend/app/tasks/celery_app.py` exports `celery_app`.

**FR-3.3** The Redis service URL in `docker-compose.yml` environment overrides (`redis://redis:6379/0`) must remain distinct from the `.env` file's local development URL (`redis://localhost:6379/0`). Do not merge these configurations.

---

### FR-4: Redis Connection Failure Handling

**FR-4.1** When `dispatch_document_processing()` in `backend/app/tasks/document_tasks.py` cannot reach the Redis broker, it must not silently discard the task.

**FR-4.2** The function must:
1. Log the broker connection error at ERROR level (not WARNING).
2. Update the document's `processing_status` to `FAILED`.
3. Set the document's `failure_reason` field to a descriptive message (e.g., `"Broker unavailable: task could not be queued"`).
4. Use the document repository or service for the status update with proper tenant isolation.

**FR-4.3** If the `LOCAL_ASYNC` background fallback is kept (lines 58-68 in `document_tasks.py`), it must:
1. Log at WARNING level indicating it is a fallback mode.
2. Handle its own exceptions and set document status to FAILED with a `failure_reason` on any exception.
3. Not silently leave documents in QUEUED status indefinitely.

**FR-4.4** The Celery task body (`process_pdf_document_task`) must handle exceptions and set document status to FAILED with a reason. Verify that the existing `execute_document_processing` method in `document_service.py` already does this (lines 168-182) and confirm it is called by the Celery task.

---

### FR-5: Health Check Improvements

**FR-5.1** The `/api/v1/health/ready` endpoint must distinguish between database health and broker/worker health in its response body.

**FR-5.2** The response must use a structured JSON format:
```json
{
  "status": "ready" | "degraded" | "not_ready",
  "service": "College ChatBot API",
  "environment": "development",
  "version": "1.0.0",
  "checks": {
    "database": true | false,
    "redis": true | false,
    "worker": true | false,
    "document_processing": true | false
  }
}
```

**FR-5.3** The endpoint must return HTTP 503 when Redis is unreachable (existing behavior preserved), but the response body must clearly indicate which component is unhealthy.

**FR-5.4** A degraded state (database healthy but Redis unhealthy) must be distinguishable from a fully unhealthy state (both unhealthy).

**FR-5.5** The existing schema `ReadinessResponse` in `backend/app/schemas/common.py` must be updated if it does not support the `checks` dictionary structure.

**Assumption**: The health check currently has a flat `checks` dictionary but may need to add `worker` and `document_processing` keys if they don't exist. The design phase will confirm the current schema structure.

---

### FR-6: Test Coverage

**FR-6.1** Add or update tests for the binary upload endpoint (`upload_pdf_document`):
- **Test 6.1.1**: Upload succeeds → storage upload service is called, DB record is created, `processing_status` is set to `QUEUED`, signed URL is returned or null on transient failure.
- **Test 6.1.2**: Storage upload fails → no DB record is created (transaction rolled back).
- **Test 6.1.3**: DB commit fails after successful storage upload → the newly uploaded storage object is deleted (cleanup executed).

**FR-6.2** Add or update tests for the metadata-only endpoint (`register_uploaded_document`) after the fix:
- **Test 6.2.1**: If deprecated (Option A): endpoint returns HTTP 410, no DB record is created.
- **Test 6.2.2**: If kept with verification (Option B): supplying a fake/generated checksum or a non-existent storage path returns HTTP 422, no DB record is created.
- **Test 6.2.3**: If minimal fix (Option C): endpoint creates DB record, returns `download_url: null`, logs WARNING.

**FR-6.3** Add or update tests for signed URL error handling:
- **Test 6.3.1**: `list_documents` with a document referencing a missing storage object → `download_url: null` for that document, no exception raised.
- **Test 6.3.2**: `get_document_details` with a document referencing a missing storage object → `download_url: null`, no exception raised.

**FR-6.4** Add or update tests for Redis/broker unavailability:
- **Test 6.4.1**: `dispatch_document_processing` with broker unreachable → document status set to FAILED, `failure_reason` set, error logged at ERROR level.
- **Test 6.4.2**: If LOCAL_ASYNC fallback is kept and it fails → document status set to FAILED, `failure_reason` set.

**FR-6.5** Add smoke test for Celery worker import:
- **Test 6.5.1**: `from app.tasks.celery_app import celery_app` succeeds (import-level test to catch incorrect module paths).

**FR-6.6** Add or update integration test for document processing pipeline:
- **Test 6.6.1**: A document with `processing_status = QUEUED` dispatched to a mocked Celery task reaches either `PROCESSING → PENDING_REVIEW` or `PROCESSING → FAILED` (never stays in QUEUED indefinitely after dispatch). Mock the Celery task execution and Supabase Storage calls.

**FR-6.7** Tests must use mocks for Supabase Storage and Redis connections. Do not require live credentials in automated unit tests.

**FR-6.8** Tests must follow the existing pytest conventions in `backend/tests/` (e.g., `test_health.py` uses `@pytest.mark.asyncio` and `AsyncClient` with `ASGITransport`).

---

## Non-Functional Requirements

### NFR-1: Safety and Backward Compatibility

**NFR-1.1** Do not run database migrations or seed scripts as part of this fix.

**NFR-1.2** Do not modify production Supabase data.

**NFR-1.3** Do not delete, retry, reprocess, or re-upload existing documents in the database or storage.

**NFR-1.4** Do not modify college IDs, RLS policies, tenant isolation logic, authentication, or user memberships.

**NFR-1.5** Do not change existing AIT (`11111111-1111-1111-1111-111111111111`) or RCTI seed records.

**NFR-1.6** Do not expose `.env` values, API keys, passwords, JWTs, or Supabase service-role secrets in code, logs, or test output.

**NFR-1.7** Do not overwrite existing Supabase Storage objects.

**NFR-1.8** Preserve the existing safe upload sequence in `upload_pdf_document` and `register_and_upload` unchanged: auth → tenant resolution → validation → upload → confirm → DB insert → cleanup on failure.

---

### NFR-2: Logging and Observability

**NFR-2.1** All error conditions (broker unreachable, signed URL failure, upload failure) must be logged with sufficient context (document ID, college ID, storage path, error message) to diagnose production issues without accessing live credentials.

**NFR-2.2** Log levels must be appropriate:
- ERROR: Broker unavailable and task cannot be queued, document processing fails, upload cleanup fails.
- WARNING: Signed URL generation fails for response construction, LOCAL_ASYNC fallback is used, metadata-only endpoint creates unverified record (Option C only).
- INFO: Successful task dispatch, successful processing, duplicate detected.

---

### NFR-3: Testability

**NFR-3.1** All changes must be unit-testable with mocked external dependencies (Supabase, Redis).

**NFR-3.2** Tests must run in CI without requiring live Supabase or Redis instances.

**NFR-3.3** Integration tests that verify the full upload-to-processing pipeline must use mocked Celery tasks and storage calls, not live background workers.

---

## Acceptance Criteria

**AC-1: Metadata-Only Endpoint**
1. The `POST /api/v1/college-admin/documents/upload` endpoint no longer crashes with a 404 error when attempting to generate a signed URL on creation.
2. The endpoint either returns HTTP 410 (deprecated), HTTP 422 (unverified), or successfully creates a record with `download_url: null` depending on the chosen fix option.
3. No database record is created if the chosen fix is deprecation (Option A) or verification failure (Option B).

**AC-2: Signed URL Error Handling**
4. The `get_document_details` endpoint returns a 200 response with `download_url: null` for a document whose storage object does not exist, instead of crashing with an unhandled exception.
5. The `upload_pdf_document` endpoint returns a 201 response with `download_url: null` if the signed URL generation fails during response construction (transient edge case), instead of crashing.
6. The `list_documents` endpoint continues to handle signed URL failures correctly (no regression).

**AC-3: Docker Compose Worker**
7. Running `docker compose up` starts the Celery worker container without an `ImportError`.
8. The worker container logs show successful connection to the Redis broker at `redis://redis:6379/0`.
9. The worker imports the correct Celery application object from `app.tasks.celery_app.celery_app`.

**AC-4: Redis Unavailable Handling**
10. When Redis is not running and `dispatch_document_processing()` is called, the document's `processing_status` is set to `FAILED` and `failure_reason` is set to a descriptive message.
11. An ERROR-level log entry is written indicating the broker is unavailable and the task could not be queued.
12. Documents do not remain stuck in QUEUED status indefinitely when the broker is down.

**AC-5: Health Check**
13. The `/api/v1/health/ready` endpoint response body includes a `checks` object with keys: `database`, `redis`, `worker`, and `document_processing`.
14. When Redis is down but the database is healthy, the response distinguishes this as `"status": "degraded"` or `"not_ready"` with `"checks": {"database": true, "redis": false, ...}`.
15. The endpoint returns HTTP 503 when Redis is unreachable (existing behavior preserved).

**AC-6: Test Coverage**
16. All new tests pass with mocked dependencies (Supabase, Redis).
17. Test for successful upload verifies storage upload is called, DB record is created, and status is QUEUED.
18. Test for storage upload failure verifies no DB record is created.
19. Test for DB commit failure verifies newly uploaded object is deleted.
20. Test for metadata-only endpoint verifies the chosen fix behavior (410, 422, or null URL).
21. Test for signed URL failure verifies `download_url: null` is returned without crashing.
22. Test for broker unavailable verifies document status is FAILED with reason.
23. Test for Celery import verifies `from app.tasks.celery_app import celery_app` succeeds.
24. Test for processing pipeline verifies QUEUED → PENDING_REVIEW or QUEUED → FAILED (never stuck in QUEUED).

**AC-7: Safety**
25. No database migrations are run.
26. No production Supabase data is modified.
27. No existing documents are deleted, retried, reprocessed, or re-uploaded.
28. No tenant isolation, RLS, auth, or membership logic is modified.
29. No secrets are exposed in code, logs, or test output.
30. The safe upload sequence in `upload_pdf_document` is unchanged.

---

## Out of Scope

**OS-1**: Installing or configuring Redis on the developer's local Windows machine. This requirement identifies the Docker Compose path as the recommended fix; local Redis installation is optional developer choice.

**OS-2**: Fixing or reprocessing existing orphaned database records (documents with no corresponding storage object). This fix prevents new orphans; cleanup of existing orphans is a separate operational task.

**OS-3**: Rewriting the document upload architecture to merge the two endpoints into one. This fix addresses the immediate bugs; API consolidation is a future enhancement.

**OS-4**: Adding a periodic health check or dead-letter queue for stuck QUEUED documents. This fix ensures new documents fail fast when Redis is down; monitoring and alerting for stuck documents is a separate operational task.

**OS-5**: Implementing a storage object existence verification job that audits all document records. This fix prevents new mismatches; auditing existing records is a separate data quality task.

**OS-6**: Running end-to-end tests with a live Supabase instance and real Redis broker. Tests will use mocks; live integration testing is a separate verification task.

**OS-7**: Changing the `LOCAL_ASYNC` fallback behavior to use a persistent queue or database-backed task queue. This fix ensures it logs failures; architectural changes to the fallback mechanism are out of scope.

**OS-8**: Modifying the Supabase bucket configuration, RLS policies, or access controls. This fix assumes the existing bucket and policies are correct; bucket-level changes are out of scope.

---

## Assumptions

**A-1**: The investigation report is accurate: the metadata-only endpoint has no active callers, and deprecation (Option A) is the safest fix for FR-1.3. If the design phase identifies callers, Option B (verification) will be used instead.

**A-2**: The existing `execute_document_processing` method in `document_service.py` (lines 168-182) correctly sets document status to FAILED on exception. This will be verified during implementation.

**A-3**: The existing test framework is pytest, and tests in `backend/tests/` use `@pytest.mark.asyncio` and `AsyncClient`. New tests will follow this convention.

**A-4**: The `ReadinessResponse` schema in `backend/app/schemas/common.py` already supports a `checks` dictionary. If not, the schema will be updated as part of FR-5.

**A-5**: The Docker Compose Redis service definition is correct (`redis:7-alpine`, port 6379). Only the worker command path is incorrect.

**A-6**: The existing cleanup logic in `register_and_upload` (lines 109-127 in `document_service.py`) correctly deletes the newly uploaded object if the DB commit fails. This will be verified and tested.

**A-7**: Mocking Supabase Storage calls in tests is achievable with standard pytest mocking techniques (e.g., `unittest.mock.patch` or `pytest-mock`).

**A-8**: The final report must document actual test results and whether Docker Compose was used, but live Supabase verification is not required for acceptance.

---

## Dependencies

**D-1**: Investigation report at `c:\Users\HP\OneDrive\Desktop\College Chatbot\.agents\tasks\storage-redis-investigation.md` (confirms root causes and file/line references).

**D-2**: Existing codebase structure and conventions (FastAPI, SQLAlchemy, Celery, pytest).

**D-3**: Docker Compose for Redis and worker services (optional for developer, required for verification of FR-3).

**D-4**: Mocking libraries for tests (pytest, pytest-asyncio, unittest.mock or pytest-mock).

---

## Risks and Mitigations

**R-1**: **Risk**: Deprecating the metadata-only endpoint (Option A) breaks an unknown caller.  
**Mitigation**: The design phase will search the frontend codebase and any integration tests for calls to `/documents/upload`. If callers exist, switch to Option B (verification). If uncertain, implement Option C (minimal fix) as a safe intermediate step.

**R-2**: **Risk**: The LOCAL_ASYNC fallback silently fails even after adding failure logging.  
**Mitigation**: Document in the final report that the fallback is unreliable for production and recommend using Docker Compose with Redis for local development. Consider deprecating the fallback in a future task (out of scope for this fix).

**R-3**: **Risk**: Tests with mocked Celery tasks do not catch real worker issues.  
**Mitigation**: Document in the final report that live Docker Compose verification was or was not performed. Recommend a separate smoke test task that uses live Redis and Celery.

**R-4**: **Risk**: Existing orphaned document records cause ongoing 404 errors in production.  
**Mitigation**: This fix prevents new orphans. Document in the final report that existing orphans require a separate cleanup task (out of scope).

**R-5**: **Risk**: The health check returning 503 when Redis is down causes false alerts in monitoring systems.  
**Mitigation**: Document the degraded state clearly in the response body. Consider adding a configuration flag in a future task to make Redis optional for local dev (out of scope).

---

## References

- Investigation Report: `c:\Users\HP\OneDrive\Desktop\College Chatbot\.agents\tasks\storage-redis-investigation.md`
- Backend API Router: `backend/app/api/v1/college_admin.py`
- Document Service: `backend/app/services/document_service.py`
- Storage Service: `backend/app/services/storage_service.py`
- Document Tasks: `backend/app/tasks/document_tasks.py`
- Celery App: `backend/app/tasks/celery_app.py`
- Health Endpoint: `backend/app/api/v1/health.py`
- Docker Compose: `docker-compose.yml`
- Test Conventions: `backend/tests/test_health.py`
