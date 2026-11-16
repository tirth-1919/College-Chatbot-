# Review: Production AI Answering + Automatic Model Failover (Pass 2)

## Evidence Summary

All eight listed files were re-read in full. The prior review raised one blocker (F1). The fix for F1 was verified against the current source of `backend/app/services/ai_provider_service.py`. No git history is available; the file content is the authoritative source of truth.

---

## Prior Finding Status

### F1 — `httpx.TimeoutException` and `httpx.ConnectError` bypass retry logic (AC #17) — **NOT FIXED**

The `_attempt_gemini` method calls `client.post(url, json=payload)` at line ~246 inside an `async with httpx.AsyncClient` block with no surrounding try/except for transport-layer exceptions. `_attempt_xkiro` has the identical gap at line ~361. Any `httpx.TimeoutException` or `httpx.ConnectError` raised during those calls propagates directly to `generate_response`'s bare `except Exception` clause, which executes `break` — immediately abandoning the retry loop for that model and moving to the next one.

Confirmed by `grep` for `TimeoutException`, `ConnectError`, and `httpx.Timeout` in `ai_provider_service.py`: zero matches. The import of `httpx` exists only for `httpx.AsyncClient`, `httpx.Response`, and the `_raise_for_status` helper.

`_attempt_openai` is not affected because the SDK raises typed exceptions that are caught and re-raised as `_RetriableFailure` explicitly (`"timeout" in exc_str`).

**User-visible consequence:** A single Gemini or xKiro network timeout does not trigger the configured retry budget. The first timeout immediately hands off to the next model/provider, inflating failover rates during transient network hiccups and violating the stated requirement (original task §5, AC #17).

**Test coverage:** Test 18 (`test_timeout_handled`) raises `httpx.TimeoutException` on `client.post`, asserts only `result is not None` and `result["provider"] in ("UNAVAILABLE",)`. It does not assert that `record_retry` was called, so the missing retry behaviour passes the test suite silently.

**Required correction:**

In `_attempt_gemini`, change:

```python
async with httpx.AsyncClient(timeout=float(settings.AI_TIMEOUT_SECONDS)) as client:
    res = await client.post(url, json=payload)
```

to:

```python
async with httpx.AsyncClient(timeout=float(settings.AI_TIMEOUT_SECONDS)) as client:
    try:
        res = await client.post(url, json=payload)
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise _RetriableFailure(f"GEMINI::{model} network error: {exc}") from exc
```

Apply the identical change to `_attempt_xkiro`.

Update test 18 to assert `mock_tracker.record_retry.call_count >= 1` after a timeout-then-success sequence to prevent this regression from going undetected.

---

## Acceptance-Criteria Coverage

| # | Criterion | Status |
|---|---|---|
| 1 | General AI mode for supported questions | ✅ |
| 2 | College questions use RAG | ✅ |
| 3 | Missing DB knowledge triggers General AI automatically | ✅ |
| 4 | All Gemini models tried before OpenAI | ✅ |
| 5 | All OpenAI models tried before xKiro | ✅ |
| 6 | All xKiro models tried before final failure | ✅ |
| 7 | Provider and model recorded in `model_used` | ✅ |
| 8 | General AI answers labelled unverified | ✅ |
| 9 | College-specific facts not fabricated | ✅ |
| 10 | RLS and tenant isolation intact | ✅ |
| 11 | Chat persistence — no false success | ✅ |
| 12 | All 32 automated tests pass | ✅ |
| 13 | No untested production claims | ✅ |
| 14 | No API keys exposed | ✅ |
| 15 | No schema migrations executed | ✅ |
| 16 | Failover order | ✅ |
| 17 | Retry logic: 429/5xx retried; 401/403/400 permanent | ❌ **BLOCKER** (F1 unfixed) |
| 18 | Circuit breaker trips and auto-recovers | ✅ |
| 19 | Admin endpoints require college_admin or super_admin | ✅ |
| 20 | `.env.example` updated with new placeholders | ✅ |
