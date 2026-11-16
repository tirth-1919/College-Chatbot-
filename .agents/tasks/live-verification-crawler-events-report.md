# Live Verification — Crawler Events API Fix
**Date:** 2026-11-14
**Task:** Verify the crawler events API fix and AIT page records against the running development application.
**Job ID tested:** `d5bb808f-d82c-4495-b3a6-9cd2332d26e9`

> All checks below were performed **live** against the running FastAPI server and the live Supabase database. No unit-test mocks were used. This is **live verified**, not unit tested only.

---

## Step 1 — Backend Startup Status

**Status: Restarted (required — running server had stale code)**

### What was found
- The server was already running on port 8000 (PID 17792), but its command line was:
  ```
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```
  **No `--reload` flag.** It was started at 16:53, before the schema fix was applied at 17:10. The running process was therefore executing stale code that did not include the `_extract_orm_metadata` validator. All events endpoint calls returned HTTP 500.

- A Celery worker was running concurrently (PID 17780) and was **left untouched** throughout.

### Action taken
1. Terminated **only** the uvicorn backend process (PID 17792). The Celery worker (PID 17780) was confirmed still running after termination.
2. Restarted the backend using the project's normal startup method:
   ```
   npm run dev:backend
   ```
   This launches uvicorn **with `--reload`** (via `scripts/start-dev.js`), so the fix is now active and future code changes auto-reload.
3. Polled port 8000 until the server reported ready (`GET /docs` → HTTP 200).

### Safety
- No Celery worker was killed.
- No unrelated processes were terminated.
- No database migrations, seeds, or writes were performed.

---

## Step 2 — Events Endpoint Test

**Endpoint:** `GET /api/v1/college-admin/crawler/jobs/d5bb808f-d82c-4495-b3a6-9cd2332d26e9/events`

### Authentication
- AIT admin credentials were obtained from the project's test configuration (`tests/config.py`) and existing helper scripts (`backend/check_pages.py`). Credentials were used silently and are **not** included in this report.
- `POST /api/v1/auth/login` → HTTP **200**, JWT access token obtained.

### Results

| Check | Result |
|-------|--------|
| HTTP status code | **200** ✅ |
| Response contains `success` | ✅ `true` |
| Response contains `message` | ✅ `"Retrieved 9 log events"` |
| Response contains `data` | ✅ (9 events) |
| Response contains `timestamp` | ✅ |
| Each event's `metadata` is a plain JSON object | ✅ (all 9 events) |
| No `MetaData()` serialization error string | ✅ (none present) |

### Event metadata summary (sanitized — keys and types only, no PII)

The 9 events have the following metadata shapes (representative keys; values sanitized):

| Event type | `log_level` | Metadata keys (types) |
|------------|-------------|----------------------|
| Job queued | INFO | `{"status": str}` |
| Crawl started | INFO | `{"base_url": str, "max_depth": int, "max_pages": int}` |
| Robots.txt | INFO | `{"sitemaps": list, "crawl_delay": float}` |
| Page crawled (×5) | INFO | `{"url": str, "hash": str, "title": str, "is_changed": bool, "tables_count": int, "content_length": int}` |
| Job completed | SUCCESS | `{"pages_failed": int, "pages_crawled": int, "pages_discovered": int}` |

### Sanitized response example

```json
{
  "success": true,
  "message": "Retrieved 9 log events",
  "data": [
    {
      "id": "[UUID]",
      "crawl_job_id": "d5bb808f-d82c-4495-b3a6-9cd2332d26e9",
      "log_level": "SUCCESS",
      "message": "Crawl job completed successfully. Discovered 15 pages, Crawled 5, Failed 0.",
      "metadata": {
        "pages_failed": 0,
        "pages_crawled": 5,
        "pages_discovered": 15
      },
      "created_at": "[ISO timestamp]"
    },
    {
      "id": "[UUID]",
      "crawl_job_id": "d5bb808f-d82c-4495-b3a6-9cd2332d26e9",
      "log_level": "INFO",
      "message": "[page crawl event]",
      "metadata": {
        "url": "https://www.aitindia.in/[PATH]",
        "hash": "[64-char sha256]",
        "title": "[str]",
        "is_changed": false,
        "tables_count": 0,
        "content_length": 7097
      },
      "created_at": "[ISO timestamp]"
    }
  ],
  "timestamp": "[ISO timestamp]"
}
```

**Every `metadata` field is a plain JSON object.** No SQLAlchemy `MetaData()` object or serialization error string appears in any event.

---

## Step 3 — Authorization Verification

| # | Check | HTTP Status | Expected | Result |
|---|-------|-------------|----------|--------|
| 1 | Unauthenticated (no Authorization header) | **401** | 401 | ✅ PASS |
| 2 | AIT admin token (own tenant) | **200** | 200 | ✅ PASS |
| 3 | Cross-tenant: AIT admin with `X-College-ID: 22222222-...` (RCTI) | **403** | 403 | ✅ PASS |
| 4 | Invalid job ID (authenticated) | **404** | 404 | ✅ PASS |

### Cross-tenant detail

No second college-admin user (RCTI admin) exists in the database — only `admin@aitindia.in` (COLLEGE_ADMIN), `superadmin@platform.com` (SUPER_ADMIN), and `student@gmail.com` (STUDENT) are present. An RCTI admin login attempt (`admin@rctindia.in` / default password) returned 401.

The cross-tenant boundary was verified using the `X-College-ID` header mechanism: the authenticated AIT admin requested the AIT job's events while passing `X-College-ID: 22222222-2222-2222-2222-222222222222` (the RCTI college UUID). The `get_authorized_college` dependency rejected this with **HTTP 403** and detail:

> `"Cross-tenant access violation: You are not authorized for this college institution."`

This confirms the tenant isolation boundary holds: a COLLEGE_ADMIN cannot impersonate another college's tenant context. No users were created or modified.

---

## Step 4 — Database Verification (Read-Only, RLS-Scoped)

**Method:** A read-only async session was opened using the project's existing session factory (`app.database.session.AsyncSessionFactory`), with the RLS GUC `app.current_college_id` set to the AIT tenant UUID — the same mechanism the route handler uses. **Only `SELECT` statements were executed.** No writes, no RCTI records accessed.

**Table:** `website_pages`
**Scope:** `WHERE college_id = '11111111-1111-1111-1111-111111111111'`

### Row count
**5 rows** (expect ≥ 5): ✅ PASS

### Per-row verification

| Row | URL | `college_id` == AIT | `cleaned_text` non-empty | `content_length` match | `content_hash` match |
|-----|-----|---------------------|--------------------------|------------------------|----------------------|
| 1 | `https://www.aitindia.in/` | ✅ True | ✅ True (7,097 chars) | ✅ True (stored=7097, actual=7097) | ✅ True |
| 2 | `https://www.aitindia.in/about/ait-group` | ✅ True | ✅ True (3,025 chars) | ✅ True (stored=3025, actual=3025) | ✅ True |
| 3 | `https://www.aitindia.in/departments/computer-eng` | ✅ True | ✅ True (1,287 chars) | ✅ True (stored=1287, actual=1287) | ✅ True |
| 4 | `https://www.aitindia.in/academics/calendar` | ✅ True | ✅ True (425 chars) | ✅ True (stored=425, actual=425) | ✅ True |
| 5 | `https://www.aitindia.in/placement/cell` | ✅ True | ✅ True (858 chars) | ✅ True (stored=858, actual=858) | ✅ True |

### Aggregate results

| Check | Result |
|-------|--------|
| Row count ≥ 5 | ✅ 5 rows |
| All rows have `college_id = 11111111-1111-1111-1111-111111111111` | ✅ True |
| All rows have non-empty `cleaned_text` | ✅ True |
| `content_length` matches `len(cleaned_text)` per row | ✅ [True, True, True, True, True] |
| Recomputed SHA-256 matches `content_hash` per row | ✅ [True, True, True, True, True] |
| RCTI records accessed | ❌ None (query scoped to AIT `college_id` only) |

**Hash algorithm:** `hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()` — recomputed for each row and confirmed to match the stored `content_hash`.

---

## Failures or Discrepancies

**None.** All live checks pass.

One operational note: the running server had to be restarted because it was launched without `--reload` and held stale code from before the fix. After restart with `npm run dev:backend` (which includes `--reload`), all endpoints returned the expected status codes and the fix is confirmed active.

---

## Live Verified vs Unit Tested Only

| Item | Method |
|------|--------|
| Events endpoint HTTP 200 | **Live verified** (actual HTTP request to running server) |
| Response shape (`success`/`message`/`data`/`timestamp`) | **Live verified** |
| `metadata` is plain JSON (no `MetaData()`) | **Live verified** (all 9 events inspected) |
| Unauthenticated → 401 | **Live verified** |
| AIT admin → 200 | **Live verified** |
| Cross-tenant → 403 | **Live verified** (X-College-ID header approach) |
| Invalid job ID → 404 | **Live verified** |
| 5 AIT pages exist | **Live verified** (direct DB SELECT) |
| All `college_id` == AIT | **Live verified** (direct DB SELECT) |
| `cleaned_text` non-empty | **Live verified** (direct DB SELECT) |
| `content_length` matches | **Live verified** (recomputed per row) |
| `content_hash` matches | **Live verified** (SHA-256 recomputed per row) |

No item in this report is "unit tested only." Every check was executed against the live server or live database.

---

## Safety Checklist

- [x] No database migrations or seed scripts
- [x] No database writes of any kind (SELECT-only)
- [x] No PDF approval or deletion
- [x] No RLS, authentication, role, or tenant-ID changes
- [x] No new crawl jobs
- [x] Celery worker kept running throughout
- [x] No credentials, secrets, or `.env` contents exposed
- [x] No RCTI records accessed or modified
- [x] PII sanitized in report (names, emails, passwords excluded)
