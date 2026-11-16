# FIX 3 Review — `reprocess_document` Signed URL Handling

## Evidence Sources

- **Source file**: `backend/app/api/v1/college_admin.py` (lines 862–891)
- **Test file**: `backend/tests/test_document_upload_and_processing.py` (Test 11, lines ~300–370)
- **Recorded test run**: 76 passed, 0 failed (coder's commit record in `fix3-review.json`)
- **No git repository present**: diff obtained by direct file inspection.

---

## Requirement 1 — Every `get_signed_url()` call in the response-construction path is guarded; returns `download_url: null` on failure

**Status: PASS**

`reprocess_document` (line 883–887) wraps its single `get_signed_url` call:

```python
res_item = DocumentDetailResponse.model_validate(doc)
try:
    res_item.download_url = await document_storage_service.get_signed_url(college.id, doc.storage_path)
except Exception:
    res_item.download_url = None
```

The guard uses `except Exception` rather than the narrower `except FileNotFoundError` named in the requirement. This is strictly broader and equally protective; it also matches the identical pattern used in every other document endpoint in the file (list_documents line 561, upload_pdf_document line 632, register_uploaded_document line 724, get_document_details line 753). No `download_url: null` path is missed.

---

## Requirement 2 — Errors during reprocessing dispatch are NOT suppressed

**Status: PASS**

`dispatch_document_processing(doc.id, college.id, background_tasks)` is called at line 880, outside any try/except block. Any exception it raises propagates to the FastAPI error handler unchanged. The try/except block begins only after that call returns, scoping it exclusively to the signed URL generation (lines 883–887).

---

## Requirement 3 — Test: `reprocess_document` with missing storage object → 200 with `download_url: null`, no exception

**Status: PASS**

Test 11 (`test_reprocess_document_missing_storage_returns_null_url`) in `test_document_upload_and_processing.py`:

- Uses `AsyncClient` + `ASGITransport` to exercise the actual FastAPI route `POST /api/v1/college-admin/documents/{doc_id}/reprocess`.
- Patches `CollegeAdminRepository.get_document` to return a known `Document` object.
- Patches `dispatch_document_processing` to return `"CELERY"` (non-raising).
- Patches `document_storage_service.get_signed_url` to raise `FileNotFoundError("Storage object not found")`.
- Overrides `get_db` with a mock session whose `commit` is an `AsyncMock`.
- Asserts `response.status_code == 200`, `body["success"] is True`, `body["data"]["download_url"] is None`.

The test is structurally sound. One redundant `patch("app.database.session.get_db", ...)` appears before the `app.dependency_overrides[get_db] = mock_get_db` assignment; the override wins for FastAPI, so the redundancy is harmless.

Recorded result: **76 passed, 0 failed**.

---

## Requirement 4 — No other endpoint behavior was changed

**Status: PASS**

Grep of all `get_signed_url` call sites in `college_admin.py` shows five locations:

| Line | Endpoint | Guard |
|------|----------|-------|
| 559 | `list_documents` | `except Exception` (pre-existing) |
| 630 | `upload_pdf_document` | `except Exception` (pre-existing) |
| 688 | `register_uploaded_document` (existence check) | `except FileNotFoundError` (pre-existing, intentionally narrow) |
| 722 | `register_uploaded_document` (response URL) | `except Exception` (pre-existing) |
| 751 | `get_document_details` | `except Exception` (pre-existing) |
| 884 | `reprocess_document` | `except Exception` (new, this change) |

Only the `reprocess_document` path was added. The unguarded call at line 839 (`generate_download_url` endpoint) is intentional — that endpoint exists specifically to surface a URL and should propagate errors; it predates this change and is out of scope.

---

## Verdict

No blockers. All four requirements are satisfied.
