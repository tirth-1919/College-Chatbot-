# JS Extraction Fix Report — AI FAQ College Chat Bot
**Date:** 2026-11-14  
**Scope:** JavaScript-rendered content extraction via Playwright fallback.  
**Tenant:** AIT only (`11111111-1111-1111-1111-111111111111`)

---

## 1. Files Changed

### New: `backend/app/services/js_renderer.py`
Created a new module with an async `render_page_with_browser(url, timeout_ms=15000)` function:

- Uses Playwright async API (`async_playwright`) to launch Chromium headless.
- Navigates with `wait_until="networkidle"` and the configurable `timeout_ms`.
- Validates that the final page URL hostname matches the initial URL hostname — raises `RuntimeError` on cross-domain redirect.
- Launches with `args=["--no-sandbox", "--disable-dev-shm-usage"]`.
- Module-level `PLAYWRIGHT_AVAILABLE = True`; set to `False` and raises `RuntimeError("Playwright not installed")` on `ImportError`.
- On any Playwright error or `TimeoutError`, raises descriptively — caller handles fallback.

### Modified: `backend/app/services/crawler_service.py`
Two changes:

1. **Added module-level constant** (after `logger = ...`):
   ```python
   JS_FALLBACK_THRESHOLD = 200
   ```

2. **Added JS fallback block** between the `parse_and_clean_html` call and the `async with tenant_session(...)` block that calls `_save_or_deduplicate_page`:
   ```python
   # JS rendering fallback
   if parsed_content.content_length < JS_FALLBACK_THRESHOLD or parsed_content.requires_js:
       try:
           from app.services.js_renderer import render_page_with_browser, PLAYWRIGHT_AVAILABLE
           if PLAYWRIGHT_AVAILABLE:
               js_html = await render_page_with_browser(final_url, timeout_ms=15000)
               js_parsed = parse_and_clean_html(js_html, final_url)
               if js_parsed.content_length > parsed_content.content_length:
                   parsed_content = js_parsed
                   logger.info("JS rendering fallback used for %s — %d chars extracted (was %d)", ...)
       except Exception as js_err:
           logger.warning("JS rendering fallback failed for %s: %s", ...)
           # Static content (possibly empty) is kept — do not abort the page
   ```

   All existing protections (SSRF, domain boundaries, robots.txt, crawl delays, page limits, deduplication, tenant isolation, no ADMIN_VERIFIED auto-labeling) are preserved unchanged.

### New: `backend/tests/test_js_extraction.py`
10 new test cases (all passing):

1. `test_static_extraction_sufficient_content`
2. `test_static_extraction_js_flag_detected`
3. `test_js_fallback_invoked_when_static_empty`
4. `test_js_fallback_not_invoked_when_static_sufficient`
5. `test_js_fallback_timeout_handled_gracefully`
6. `test_empty_page_stores_zero_length`
7. `test_domain_restriction_enforced`
8. `test_tenant_isolation_college_id_on_saved_page`
9. `test_deduplication_same_hash_returns_false`
10. `test_playwright_unavailable_does_not_crash`

---

## 2. Dependencies Added

| Dependency | Version | Status |
|------------|---------|--------|
| `playwright` | `>=1.48.0,<2.0.0` | Already in `requirements.txt` — no change needed |
| Chromium browser binary | bundled with Playwright | Already installed — `python -m playwright install chromium` was not required |

**Verification:**
```
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); b.close(); p.stop(); print('Playwright OK')"
# Output: Playwright OK
```

No new entries were added to `requirements.txt`.

---

## 3. Test Results

**Command:** `python -m pytest tests/ -v --tb=short`  
**Result: 95 passed, 0 failed, 3 warnings**

The 3 warnings are pre-existing (`StarletteDeprecationWarning`, `RuntimeWarning: coroutine never awaited` in unrelated document processing tests) — none are from the new code.

All 10 new `test_js_extraction.py` tests passed:

```
tests/test_js_extraction.py::test_static_extraction_sufficient_content PASSED
tests/test_js_extraction.py::test_static_extraction_js_flag_detected PASSED
tests/test_js_extraction.py::test_js_fallback_invoked_when_static_empty PASSED
tests/test_js_extraction.py::test_js_fallback_not_invoked_when_static_sufficient PASSED
tests/test_js_extraction.py::test_js_fallback_timeout_handled_gracefully PASSED
tests/test_js_extraction.py::test_empty_page_stores_zero_length PASSED
tests/test_js_extraction.py::test_domain_restriction_enforced PASSED
tests/test_js_extraction.py::test_tenant_isolation_college_id_on_saved_page PASSED
tests/test_js_extraction.py::test_deduplication_same_hash_returns_false PASSED
tests/test_js_extraction.py::test_playwright_unavailable_does_not_crash PASSED
```

All 85 pre-existing tests also passed.

---

## 4. Live Crawl Results

### Authentication & Tenant Confirmation
- **User:** `admin@aitindia.in`
- **Role:** `COLLEGE_ADMIN`
- **`college_id`:** `11111111-1111-1111-1111-111111111111` ✅
- **Domain:** `aitindia.in` ✅
- **Status:** `APPROVED` ✅

### Crawl Job
- **Source:** `source_id = 3cb58f26-5496-4706-880a-e4a0454832e3` (`https://www.aitindia.in/`, max_depth=1, max_pages=5)
- **Job ID:** `d5bb808f-d82c-4495-b3a6-9cd2332d26e9`
- **Status:** `COMPLETED`
- **Pages discovered:** 15
- **Pages crawled:** 5
- **Pages failed:** 0
- **Duration:** ~62 seconds (JS rendering adds ~12s per page due to `networkidle` wait)

### Extracted Content Per Page

| URL | `content_length` (chars) |
|-----|--------------------------|
| `https://www.aitindia.in/` | **7,097** |
| `https://www.aitindia.in/about/ait-group` | **3,025** |
| `https://www.aitindia.in/departments/computer-eng` | **1,287** |
| `https://www.aitindia.in/placement/cell` | **858** |
| `https://www.aitindia.in/academics/calendar` | **425** |

**Total extracted:** 12,692 characters across 5 pages  
**Previous result:** 0 characters (all pages empty before this fix)

The JS rendering fallback fired on every page (all had `content_length < 200` from static extraction alone since `www.aitindia.in` is a React SPA).

---

## 5. `college_id` Confirmed

All 5 stored `WebsitePage` records have:
```
college_id = 11111111-1111-1111-1111-111111111111
```
No other college's pages were created or modified. ✅

---

## 6. Deduplication Confirmed

A second crawl job (`job_id = 578df0f8-9705-4ae2-ae37-4c8f91a94a39`) was run against the same source immediately after.

| URL | Result |
|-----|--------|
| `https://www.aitindia.in/` | **UNCHANGED** (hash matched) |
| `https://www.aitindia.in/placement/cell` | **UNCHANGED** |
| `https://www.aitindia.in/academics/calendar` | **UNCHANGED** |
| `https://www.aitindia.in/departments/computer-eng` | **UNCHANGED** |
| `https://www.aitindia.in/about/ait-group` | CHANGED (live site updated between runs) |

4/5 pages deduplication-matched (content hash identical → `_save_or_deduplicate_page` returned `False`, no new record created). The one "changed" page had its live content genuinely updated between the two crawls. No new pages were created. ✅

---

## 7. Tenant Isolation Confirmed

After both crawl runs, querying all pages for the AIT admin token:

- **Total pages:** 5
- **All `college_id`:** `11111111-1111-1111-1111-111111111111` (100%)
- **Other-tenant pages:** 0 ✅

No RCTI or other tenant data was accessed or modified.

---

## 8. Pre-existing PENDING Jobs

The five pre-existing PENDING jobs (`f6c46a15`, `bc7f536c`, `234a5ea7`, `f84e3438`, `28d5cd39`) were not modified. ✅

---

## 9. Remaining Limitations and Known Gaps

1. **Crawl speed:** Each page with JS rendering takes ~10–15 seconds (Playwright `networkidle` wait). For large sites this is a significant slowdown. Mitigation: the fallback only fires when `content_length < 200` or `requires_js == True`, so ordinary static sites are unaffected.

2. **CrawlEvents endpoint HTTP 500:** The existing `GET /api/v1/college-admin/crawler/jobs/{id}/events` endpoint returns 500. This is a pre-existing bug (a Pydantic/SQLAlchemy `metadata` naming conflict identified in the prior crawl report) — not introduced by this change. Deduplication was confirmed by comparing content hashes directly via the pages endpoint.

3. **Playwright cross-platform compatibility:** The `--no-sandbox` flag is required on Linux CI environments. On Windows (current machine), Chromium runs fine without it too, but it doesn't hurt.

4. **`networkidle` timeout risk:** Some pages with continuously-loading analytics scripts may never reach `networkidle`. If this becomes an issue, the fallback should be changed to `domcontentloaded` + a short `asyncio.sleep`. For the AIT site, `networkidle` worked reliably within 15 seconds.

5. **Worker health check false negative:** The `/health/ready` endpoint showed `worker: false` during the crawl run even though the Celery worker was processing jobs correctly. This is a pre-existing quirk of the health check ping timing — not introduced by this change.

---

## 10. Safety Checklist

- [x] Only AIT tenant used (`11111111-1111-1111-1111-111111111111`)
- [x] Only `https://www.aitindia.in/` crawled
- [x] No RCTI or other tenant data accessed or modified
- [x] No migrations or seeds run
- [x] No model changes (`WebsitePage` unchanged)
- [x] No existing PDF documents touched
- [x] No secrets exposed in this report
- [x] Crawl controlled (`max_depth=1`, `max_pages=5`)
- [x] Pre-existing PENDING jobs not modified
- [x] No automatic `ADMIN_VERIFIED` status assigned
- [x] SSRF protection, domain boundary, robots.txt compliance all preserved
- [x] Application validation not bypassed
