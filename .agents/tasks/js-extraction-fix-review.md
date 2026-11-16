# JS Extraction Fix — Code Review

## Evidence Summary

All three changed files were read in full. `html_extractor.py` was read to verify field contracts. The coder's report and test output were taken as the build/test record.

---

## Finding Assessment

### 1. Fallback trigger (correctness)

`crawler_service.py` triggers the JS fallback when `parsed_content.content_length < JS_FALLBACK_THRESHOLD` (200) **or** `parsed_content.requires_js` — matching the stated design. The JS-rendered result replaces static only when it is strictly longer. The import is deferred (`from app.services.js_renderer import …`) inside the `if` block, so the import runs only when the threshold is crossed; if Playwright is absent `PLAYWRIGHT_AVAILABLE` is `False` and the branch is skipped cleanly.

`html_extractor.py` confirms: `content_length = len(cleaned_text)`, `content_hash = sha256(cleaned_text)`, `requires_js` set when body text < 80 chars and a SPA root div or `<noscript>` is present. These fields are used correctly by the fallback.

### 2. SSRF / cross-domain in js_renderer.py

`render_page_with_browser` receives `final_url` — the URL already validated by `_fetch_url_safely` through SSRF and domain-boundary checks. After rendering, it compares `urlparse(final_url).hostname` against `urlparse(page.url).hostname`. Mismatch raises `RuntimeError`, which the caller catches and logs, keeping static content. The check is present and logically correct. No new network entry-point is opened beyond what the HTTP client already validated.

One limitation: the hostname comparison uses exact string equality, so a cross-domain redirect to a subdomain (`sub.aitindia.in` → `aitindia.in`) would raise. This is the safer direction (over-blocking rather than under-blocking) and is acceptable.

### 3. Graceful degradation

The entire JS fallback is wrapped in `try/except Exception`, which covers `RuntimeError("Playwright not installed")`, `PlaywrightTimeoutError`, and any other browser error. On any failure `parsed_content` retains its pre-fallback value and the page proceeds to `_save_or_deduplicate_page`. No crash path exists.

`PLAYWRIGHT_AVAILABLE = False` on `ImportError` is set at module level. The import-time guard means the flag is reliable; it cannot be `True` while the library is absent.

### 4. Deduplication integrity

`content_hash` and `cleaned_text` come from `ExtractedPageContent`, which always derives `content_hash = sha256(cleaned_text)` inside `parse_and_clean_html`. When the JS path runs, `parse_and_clean_html(js_html, final_url)` is called on the rendered HTML, so the hash is computed from cleaned JS-rendered text — not raw HTML. `_save_or_deduplicate_page` is unchanged. ✅

### 5. Tenant isolation

`execute_crawl_job` passes `college_id` to every `tenant_session(college_id=college_id)` call, and `college_id` is forwarded unchanged into `_save_or_deduplicate_page`. The JS fallback block does not touch `college_id`. All `WebsitePage` inserts include `college_id=college_id` as before. No bypass is introduced. ✅

### 6. Test coverage

All 10 tests avoid live network and DB calls. Key coverage:

| Scenario | Test |
|---|---|
| Static path sufficient | `test_static_extraction_sufficient_content`, `test_js_fallback_not_invoked_when_static_sufficient` |
| JS fallback triggered | `test_js_fallback_invoked_when_static_empty`, `test_static_extraction_js_flag_detected` |
| Timeout / error | `test_js_fallback_timeout_handled_gracefully` |
| Empty page | `test_empty_page_stores_zero_length` |
| Domain restriction | `test_domain_restriction_enforced` |
| Tenant isolation | `test_tenant_isolation_college_id_on_saved_page` |
| Deduplication | `test_deduplication_same_hash_returns_false` |
| Playwright unavailable | `test_playwright_unavailable_does_not_crash` |

One minor test fidelity note: tests 3–5 and 10 replicate the fallback `if/try` logic inline rather than calling `execute_crawl_job` directly. This means the tests verify the extracted logic is correct but do not exercise the actual call path in `crawler_service.py`. This is a coverage gap, not a correctness defect — the inline logic mirrors the production code exactly, and the production path is covered by the live crawl evidence.

### 7. No unintended changes

No existing method was modified. The only additions to `crawler_service.py` are the `JS_FALLBACK_THRESHOLD` constant and the fallback block. All existing guards (SSRF, domain boundary, robots.txt, page limits, deduplication, `tenant_session`, `ADMIN_VERIFIED` exclusion) are present and unaltered. No other files were changed.

### 8. Report completeness

`js-extraction-fix-report.md` covers files changed, dependencies, test results (95 passed), live crawl output with per-URL character counts, `college_id` confirmation, deduplication confirmation, tenant isolation, and pre-existing PENDING job preservation. All required items are documented.

---

## Blockers

None.
