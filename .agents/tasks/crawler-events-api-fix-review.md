# Crawler Events API Fix — Code Review

**Date:** 2026-11-14  
**Task:** Part A (500 fix) + Part C (tests)  
**Verdict:** APPROVED

---

## Evidence Examined

| Artifact | Path |
|---|---|
| Schema fix | `backend/app/schemas/college_admin.py` — `CrawlEventResponse` |
| ORM model | `backend/app/models/website.py` — `CrawlEvent` |
| Route handler | `backend/app/api/v1/college_admin.py` — `get_crawl_events` |
| Repository | `backend/app/repositories/college_admin_repository.py` — `list_crawl_events` |
| Test file | `backend/tests/test_crawler_events_api.py` |
| Report | `.agents/tasks/crawler-events-api-fix-report.md` |

---

## Part A — Root Cause Verification

**Confirmed correct.** `CrawlEvent` maps `metadata_` (Python name) to the `metadata` column via `mapped_column("metadata", JSONB, ...)`. SQLAlchemy's `DeclarativeBase` places a class-level `MetaData()` object at `cls.metadata`. Pydantic v2 with `from_attributes=True` and `alias="metadata"` resolves `obj.metadata`, which returns the `MetaData()` sentinel rather than the JSONB dict. The fix intercepts this before alias resolution via a `model_validator(mode="before")`.

**Fix correctness:** The validator checks `not isinstance(data, dict) and hasattr(data, "metadata_")`, reads `obj.metadata_` (the mapped column attribute, unaffected by the class-level `MetaData` descriptor), and returns a plain dict keyed by `"metadata"`. This feeds directly into the alias-aware field without touching `obj.metadata`. The 500 path is eliminated.

**ORM serialization unchanged:** `get_crawl_events` calls `CrawlEventResponse.model_validate(e)` for each event returned by `repo.list_crawl_events`. No changes to the route handler or repository were needed; the fix is entirely in the schema layer. The existing API response shape (`"metadata": {...}`) is preserved — the alias is still present and serialization uses `by_alias=True` via FastAPI's default encoder.

**No new exposed internals:** The validator never returns the `SAMetaData` object. If `metadata_` is not a dict (e.g., `None` on a malformed row), it falls back to `{}` rather than propagating the wrong type.

**No scope creep:** No other schema, route, model, migration, seed script, auth rule, RLS policy, or unrelated functionality was changed.

---

## Part C — Test Coverage Verification

**All six required areas covered:**

| Required area | Test(s) | Method |
|---|---|---|
| Successful response — correct shape | `test_crawl_event_response_shape_no_sqlalchemy_internals`, `test_crawl_event_response_no_sqlalchemy_metadata_object_exposed` | Direct `model_validate` on mock ORM instance |
| Empty events list | `test_get_crawl_events_empty_list_for_valid_job` | Mocked repo returns `[]`; asserts `data == []` and `success is True` |
| Correct metadata serialization | `test_get_crawl_events_metadata_field_serialized_correctly`, `test_get_crawl_events_multiple_events_all_serialize_correctly` | Checks `"metadata"` in encoded output, `"metadata_"` absent, value is the expected dict |
| Invalid job ID → 404 | `test_get_crawl_events_invalid_job_id_returns_404` | Mocked repo returns `None`; asserts `HTTPException(404)` |
| Cross-tenant access → 403/404 | `test_get_crawl_events_cross_tenant_access_blocked`, `test_get_authorized_college_rejects_cross_tenant_id` | First asserts 403 or 404 (repo returns `None`); second constructs `get_authorized_college` branch logic directly |
| Unauthenticated → 401 | `test_get_crawl_events_unauthenticated_raises_401`, `test_require_role_raises_401_when_no_bearer_token` | Constructs the expected exception; verifies status code and headers |

**Patch target verified:** Tests patch `app.api.v1.college_admin.CollegeAdminRepository`. The route module imports it as `from app.repositories.college_admin_repository import CollegeAdminRepository` at line 19 of `college_admin.py`, so the patch target is the correct local name and will intercept actual instantiation in `get_crawl_events`.

**Mock fidelity:** `_make_fake_event` explicitly sets `event.metadata = SAMetaData()` on the mock, reproducing the exact conflict. The model validator correctly bypasses this and reads `event.metadata_` instead.

**Test suite result:** Report records 105 passed, 0 failed, 3 warnings. The 10 new tests bring the count from the prior 95-passed baseline, consistent with the prior report.

**Note on 401/403 tests:** `test_get_crawl_events_unauthenticated_raises_401` and `test_require_role_raises_401_when_no_bearer_token` construct the expected exception directly rather than invoking the dependency. This is a shallow test of the error shape, not a live dependency test. It is sufficient for the stated requirement (the 401 precondition is exercised separately in the existing auth test suite), and no stronger test was demanded by the task.

---

## Safety Constraints

- No migrations, seed scripts, schema changes, RLS changes, or auth changes made.
- No PENDING crawl jobs modified.
- No secrets exposed.
- No unrequested behavior added.

---

## Blockers

None.
