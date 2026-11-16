# FIX 1 Review — Frontend Upload Caller
**File:** `apps/admin-frontend/src/services/college-admin-service.ts`  
**Review pass:** Second pass — prior blocker (missing frontend test execution) re-verified.

---

## Evidence Summary

### Diff source
No git history available (not a git repository). Review based on direct file inspection of current state.

### Requirement 1 — POST to `/upload-file` with multipart/form-data and actual File object

`uploadDocumentBinary` (service lines ~128–143) constructs a `FormData`, appends the `File` object as `"file"`, appends `category`, and optionally `description`. It calls `adminApiRequest` with `body: formData` targeting `"/college-admin/documents/upload-file"`.

`adminApiRequest` in `api-client.ts` detects `options.body instanceof FormData` via `isFormData`, skips setting `Content-Type` (allowing the browser to set the multipart boundary automatically), and passes the `FormData` body directly to `fetch`. The URL resolves to `${getApiBase()}/college-admin/documents/upload-file` → `POST /api/v1/college-admin/documents/upload-file`. **PASS.**

### Requirement 2 — No fake SHA-256 checksum

`uploadDocumentBinary` does not generate or attach any checksum. No SHA-256 construction is present anywhere in `uploadDocumentBinary`. The previously offending function (which generated `sha256_{uuid4().hex[:16]}`) has been replaced — no trace of fake checksum generation remains. **PASS.**

### Requirement 3 — Auth headers and college_id preserved

`adminApiRequest` sets `Authorization: Bearer <token>` from `localStorage.getItem("admin_auth_token")` and `X-College-ID` from `localStorage.getItem("admin_college_id")` on every non-auth request. The `isFormData` branch skips `Content-Type` only; Bearer token and `X-College-ID` are still applied. `college_id` is taken from the user context in localStorage (set at login), not generated client-side. **PASS.**

### Requirement 4 — Existing error handling and UI feedback preserved

`adminApiRequest` on non-2xx returns `{ success: false, error: data.detail || data.message || "An administrative API error occurred." }`. Network errors are caught and return `{ success: false, error: err.message }`. The calling component (`documents/page.tsx` lines ~148–166) checks `res.success`, calls `setUploadError(res.error || "Failed to process document upload.")` on failure, has a surrounding `catch` block for thrown exceptions, and a `finally` block that clears `isUploading`. **PASS.**

### Requirement 5 — Old metadata-only function renamed and documented

The old function is now named `registerPreUploadedDocument`. It carries a full `@deprecated` JSDoc block explicitly stating:
- It **MUST NOT** be used for new PDF uploads — use `uploadDocumentBinary` instead.
- The three preconditions that must all be true before it can legitimately be called.
- The consequence of misuse (HTTP 422, orphan DB record, Supabase 404 on every signed-URL request).

No callers of `registerPreUploadedDocument` were found in `apps/admin-frontend/src/**/*.tsx`. The UI component (`documents/page.tsx`) calls only `uploadDocumentBinary`. **PASS.**

### Requirement 6 — Frontend tests

File: `apps/admin-frontend/src/services/college-admin-service.test.ts`

Three tests are present and **verified by test execution** (see below):

1. **Successful upload (multipart to `/upload-file`, response has `document_id`)** — asserts URL contains `/college-admin/documents/upload-file`, body is `instanceof FormData`, `file`/`category`/`description` fields are correct, `Authorization: Bearer …` and `X-College-ID` headers are present, `Content-Type` is null (not manually set), `result.success === true`, `result.data.id === fakeDocumentId`. **PASS.**

2. **Upload failure — non-200 response (422)** — asserts `result.success === false`, `result.error` contains `"PDF validation failed"`, `result.data` is undefined. No silent failure. **PASS.**

3. **Upload failure — network error** — asserts `result.success === false`, `result.error` is truthy, `result.data` is undefined. **PASS.**

---

## Test Execution Evidence

Frontend tests run directly (coder had not provided recorded output — spot-check performed):

```
 ✓ src/services/college-admin-service.test.ts (3)
   ✓ collegeAdminService.uploadDocumentBinary (3)
     ✓ sends a multipart/form-data POST to /upload-file and returns document_id on success
     ✓ surfaces error state when the server returns a non-200 response — no silent failure
     ✓ surfaces error state on network failure — no silent failure

 Test Files  1 passed (1)
      Tests  3 passed (3)
   Duration  7.91s
```

All 3 tests pass. Prior blocker is cleared.

---

## Blockers

None.

---

## Verdict

APPROVED — all requirements satisfied, all three frontend tests pass.
