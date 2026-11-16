# Phase 3A.4.4A — Authentication Lookup and Invitation Delivery Remediation

## Final decision: PARTIAL

Application changes and focused tests are complete. PostgreSQL validation of the changed `SECURITY DEFINER` function was not performed, as required by the task's no-database-access restriction. Do not mark Phase 3A.4.4 complete until the proposed migration has been reviewed and validated against an isolated PostgreSQL database.

## 1. Root causes and files changed

### Root causes

- `lookup_user_by_email_for_auth(text)` returned `SETOF public.users`, exposing the complete user composite to callers instead of only authentication fields.
- Authentication, password-reset, and email-verification paths shared that broad lookup, so token and profile fields were unnecessarily available to those flows.
- `NotificationService` treated the presence of provider-related environment variables as proof of email delivery, despite having no transport implementation.
- Invitation links were fixed to `http://localhost:3001`; no environment validation enforced HTTPS or rejected localhost outside development.
- No tests demonstrated transport acceptance/rejection behavior or secret redaction.

### Files changed

- `backend/app/repositories/user_repository.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/email_transport.py` (new)
- `backend/app/core/config.py`
- `backend/.env.example`
- `.env.example`
- `database/migrations/022_minimize_auth_lookup.sql` (proposed; not executed)
- `backend/tests/test_auth_lookup.py` (new)
- `backend/tests/test_email_notifications.py` (new)
- `backend/tests/test_config.py`
- `backend/tests/test_phase3a4_authz.py`

## 2. Authentication lookup

**Before:** `RETURNS SETOF public.users`, exposing the whole table row, including `id`, timestamps, email, password hash, name, role, account flags, verification/reset tokens, preferences, language, and login metadata.

**After:** the proposed function returns only:

| Field | Reason |
|---|---|
| `id` | Bind signed user context and identify the account |
| `email` | Login identity and response/JWT claim |
| `hashed_password` | Required for local password verification |
| `full_name` | Existing response/JWT claim |
| `role` | Existing authorization and response behavior |
| `is_verified` | Existing response behavior |
| `is_active` | Account-status authorization |

`AuthUserLookup` is a dedicated immutable type; its password hash is omitted from its `repr`. The hash is used for local verification and is not included in API schemas, logs, or error messages.

The login flow uses the minimal lookup. Registration duplicate checking uses only its existence. Password-reset and email-verification flows use the lookup to obtain the account ID, establish signed user context, and only then retrieve the user's ORM row under that context. Their token fields are not returned by the authentication lookup.

Focused tests verify the selected fields, login/password verification, wrong-password rejection, and absence of a password hash from API serialization and logs.

## 3. Proposed database SQL, ownership, and grants

The proposed forward migration is [022_minimize_auth_lookup.sql](../../database/migrations/022_minimize_auth_lookup.sql). It changes only the authentication lookup function:

- Returns the seven fields listed above rather than `SETOF public.users`.
- Remains `SECURITY DEFINER` and uses fixed `search_path = pg_catalog`; the table is schema-qualified.
- Captures and restores the existing function owner during replacement.
- Re-establishes the grant state specified in migration 021: `PUBLIC` is revoked and `college_app_user` receives `EXECUTE`.
- Does not modify RLS policies, roles, data, or unrelated grants.

**BLOCKED — NOT VALIDATED:** The actual function owner, live ACL, function dependencies, and migration execution privileges were not inspected. No PostgreSQL instance was connected to, and the migration was not executed or tested. Validate the owner-preservation and grant result in an isolated database before deployment.

## 4. Email transport and status behavior

The repository previously had provider-variable detection but no provider implementation. A small injectable transport interface and a standard-library SMTP implementation were added.

- `SENT` is recorded only after SMTP `send_message` returns without refused recipients. This means the SMTP relay accepted the message; it does **not** prove inbox delivery.
- SMTP rejection, network failure, timeout, incomplete configuration, and missing configuration result in `FAILED`, with sanitized error text.
- No transport credentials are generated or requested. SMTP host, port, optional username/password, sender, STARTTLS, and timeouts are configuration inputs.
- Production SMTP configuration requires STARTTLS.
- Logs include only the event type and outcome—not recipient, content, invitation token, or full URL.
- Invitation audit content excludes the link and token. Existing invitation persistence continues to store only the invitation-token hash.
- No Resend or SendGrid transport exists; provider API-key presence alone no longer implies delivery.

## 5. Frontend invitation URL configuration

`ADMIN_FRONTEND_URL` now supplies the invitation-link origin. The settings validator rejects malformed URLs, credentials, query/fragment components, and whitespace. HTTP/localhost is allowed only for development; production requires HTTPS and rejects localhost. Development defaults to `http://localhost:3001`.

Invitation URLs encode the token as a query parameter. Tests verify configured URL use, development localhost acceptance, production rejection of localhost/non-HTTPS URLs, and that plaintext tokens do not appear in audit content, logs, or invitation API response schemas.

## 6. Tests and results

**PASS — 66 tests passed** with:

```text
python -m pytest -q tests/test_auth_lookup.py tests/test_email_notifications.py tests/test_auth_endpoints.py tests/test_auth_security.py tests/test_phase3a4_authz.py tests/test_config.py
66 passed in 32.47s
```

Coverage includes:

- SMTP relay acceptance and recipient rejection using mocks.
- Successful, rejected, timed-out, and network-failed transport outcomes.
- Missing provider configuration never produces `SENT` or `SIMULATED`.
- Configured frontend invitation URL and production URL validation.
- Minimal authentication lookup and functional password verification.
- No password hash in login API serialization/logs; no invitation token/hash in invitation response schemas or token/URL in notification logs.

Pylance diagnostics for changed application modules and focused tests reported no errors after the final changes.

**NOT REQUIRED:** No frontend source changed, so frontend tests/build were not run.

## 7. Remaining checks and limitations

| Check | Result | Notes |
|---|---|---|
| Application authentication and mocked email tests | PASS | 66 focused tests passed |
| Authentication lookup schema on PostgreSQL | BLOCKED | Migration not executed; no database access allowed |
| Live function owner, ACL, and dependency review | NOT VERIFIED | Must be reviewed before applying the migration |
| Isolated PostgreSQL migration validation | BLOCKED | Requires a disposable PostgreSQL environment |
| Real SMTP/provider delivery | NOT VERIFIED | Only mocked SMTP behavior was tested |
| Inbox delivery | NOT VERIFIED | SMTP acceptance is not end-to-end delivery |
| Frontend build/tests | NOT REQUIRED | No frontend files changed |

## 8. Production/database change confirmation

**PASS — No database connection, SQL execution, migration, production change, or production secret handling occurred.** Migration 022 is only a repository proposal and must not be applied until separately reviewed, validated in isolation, and explicitly approved.
