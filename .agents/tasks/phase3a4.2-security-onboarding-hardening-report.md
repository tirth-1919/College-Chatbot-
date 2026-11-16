# Phase 3A.4.2 — Security and Onboarding Hardening Report

## Executive decision

**NO-GO for production deployment and Phase 3B provider failover.**

Repository work now uses signed, short-lived RLS context; invitation-gated admin provisioning; reduced public registration responses; and token-bound anonymous chat sessions. The targeted application tests and frontend checks pass. However, the migration has **not** been run or validated against an isolated PostgreSQL database, no live database was inspected, the RLS signing key is not provisioned, and invitation email delivery is not production-ready. These gaps prevent a security or production-readiness claim.

No production SQL, database role, policy, schema, or data was accessed or changed. No credentials were printed or used.

## Evidence and validation limits

| Check | Result | Evidence |
|---|---|---|
| Application/unit regression tests | **PASS** | Backend command below: 40 passed. |
| Admin frontend build | **PASS** | `npm run build` completed successfully, including compilation, lint/type checks, and static page generation. |
| Admin frontend tests | **PASS** | `npm run test -- --reporter=dot`: 7 passed. |
| Pylance diagnostics for edited auth, chat, and focused test files | **PASS** | No diagnostics returned. |
| Isolated PostgreSQL migration/RLS validation | **BLOCKED** | PostgreSQL 17.6 binaries are installed under `C:\Program Files\PostgreSQL\17\bin`, but the required `vector.control` file is absent. The existing PostgreSQL service was not used because its data directory is not an approved disposable test instance. Docker CLI 29.9.3 is present, but Docker Desktop is not installed and its daemon is unavailable. No disposable database was created. |
| Live Supabase verification | **NOT VERIFIED** | No live connection was made. Prior live-audit reports are not evidence of the current database state. |
| Production RLS key provisioning | **BLOCKED** | The application requires `RLS_CONTEXT_SECRET`, and the matching database key must be securely provisioned in `auth_private.rls_context_keys`. Neither was provisioned during this task. |

Executed backend test command:

```text
python -m pytest tests\test_phase3a4_authz.py tests\test_chat_rls_and_telemetry.py tests\test_auth_endpoints.py tests\test_auth_security.py tests\test_database_models.py -q
40 passed
```

The backend tests use mocks. They do not prove PostgreSQL policy behavior, migration compatibility, database function ownership, or live tenant isolation.

## Reconciliation of prior findings

| Prior finding | Current repository evidence | Status | Severity |
|---|---|---|---|
| Application-settable `app.is_super_admin` could forge Super Admin access | `backend/app/database/session.py` signs the context with an independent HMAC key; `database/migrations/021_phase3a42_security_onboarding.sql` verifies it and returns false for invalid, expired, or missing signatures. Focused tests verify signature construction and missing-key failure. | **PARTIALLY FIXED** — database verifier and key ACLs were not tested on PostgreSQL; key provisioning is outstanding. | Critical |
| RLS settings could be forged or retained across pooled connections | Context values are transaction-local and signed. The existing async-engine check-in listener attempts `DISCARD TEMP` and `RESET ALL`. | **PARTIALLY FIXED** — mocked tests do not verify async-driver cleanup or database transaction behavior. | High |
| Registration could create an initial active administrator before approval/invitation | The Phase 3A.4.2 repository/API path now approves the institution and creates an invitation rather than provisioning an administrator immediately. The migration's acceptance function checks the college is approved and active before creating or promoting an account. | **PARTIALLY FIXED** — no isolated database lifecycle test; function ownership and existing-row compatibility are unknown. | Critical |
| Public registration/status lookups relied on unrestricted table reads or exposed excess data | The repository uses narrow definer functions for submission, availability, status, and additional-information submission. The status response schema is reduced and requires a tracking code. | **PARTIALLY FIXED** — SQL, grants, legacy tracking codes, and rate-limit behavior are unvalidated. | High |
| Anonymous chat sessions were not private to a visitor | Creation generates a visitor capability, persists only its hash, returns it once, and requires it for anonymous history/message/delete requests. Focused ownership tests cover valid and wrong tokens. | **PARTIALLY FIXED** — end-to-end RLS and connection-reuse tests need the blocked isolated database. | High |
| Admin invitation pages could show mock/local invitation success | Invitation acceptance and administrator management now use backend APIs; local/demo success and token data are removed. Failed API operations are surfaced, and responses no longer claim email was sent. | **PASS** for repository/UI behavior; delivery itself remains unverified and is a blocker below. | High |
| Existing unsafe RLS policy baseline and production role configuration | Migration 021 replaces several policies and adds functions, but no current Supabase catalogs or role grants were inspected. | **NOT VERIFIED** | Critical |

## Implementation evidence

The Phase 3A.4.2 migration draft at [021_phase3a42_security_onboarding.sql](../../database/migrations/021_phase3a42_security_onboarding.sql) adds:

- HMAC verification of short-lived request context, with fail-closed helper functions.
- Hash-only invitation tokens and an atomic acceptance function that checks approval, active status, invitation expiry, and signed-in invitee identity.
- A new anonymous chat visitor-token hash and policies coupling sessions/messages to the token and tenant.
- Narrow database functions for public registration intake and tracking-code operations.

The Python context writer in [session.py](../../backend/app/database/session.py) validates a 32-byte hex secret and sets identity/context values transaction-locally. With no configured secret it raises before issuing SQL. Tests in [test_phase3a4_authz.py](../../backend/tests/test_phase3a4_authz.py) cover signature generation and the missing-secret fail-closed case.

The invitation UI in [accept-invitation/page.tsx](../../apps/admin-frontend/src/app/(auth)/accept-invitation/page.tsx) no longer falls back to local mock invitations or reports fake acceptance. The administrator page in [admins/page.tsx](../../apps/admin-frontend/src/app/super-admin/admins/page.tsx) loads, resends, and revokes actual API invitations without displaying bearer tokens. The API permits a signed-in invited account to accept without changing its password, while still requiring a password for new accounts.

## Critical findings and remaining blockers

| Finding | Status | Severity | Required minimal action |
|---|---|---|---|
| Migration 021 and its helper/function ACLs have not been executed on a disposable database. | **BLOCKED** | Critical | Establish an isolated PostgreSQL instance with the project's required extensions and representative preceding migrations; validate the migration, policies, key ACLs, data conversion, and rollback/recovery path there. |
| RLS context signing key is not provisioned. The database fails closed without it, so normal protected application access will fail. | **BLOCKED** | Critical | Generate a unique 32-byte key through an approved secret-management process; provision it out of band to the application secret store and private database table; verify equality without printing it. |
| Live table ownership, role membership, `BYPASSRLS`, FORCE-RLS state, policy composition, and function execute grants are unknown. | **NOT VERIFIED** | Critical | Repeat the read-only Phase 3A.1/3A.3 catalog checks against the current project using the application role and an approved safe procedure. |
| Several `SECURITY DEFINER` functions use `search_path = pg_catalog, public, auth_private`; `public` object-creation privileges and function ownership are not established. The user lookup function returns `SETOF public.users`, including fields beyond the login credential fields, to `college_app_user`. | **NOT VERIFIED** | High | Verify ownership and `CREATE` privileges; minimize the auth lookup function's returned columns/operations and confirm only intended roles can execute it. |
| The privilege-update trigger permits the function owner named `postgres` to bypass checks. Migration 021 does not explicitly establish/verify that owner. Existing-user invitation promotion may fail or have different trigger behavior if the migration owner differs. | **NOT VERIFIED** | Critical | Confirm the intended owner in the isolated migration and make the trusted function/trigger ownership explicit in a reviewed migration. |
| Invitation email transport is not implemented. `notification_service.py` can mark a configured-provider path `SENT` without sending, and invitation links are hard-coded to `http://localhost:3001`. With no provider it records `SIMULATED`; the invitee cannot receive the hash-only token through the current UI. | **FAIL** | Critical | Implement and test a real mail transport and deployment-configured frontend URL before inviting real administrators; do not treat `SENT`/`SIMULATED` log values as delivery evidence. |
| Existing tracking codes remain stored in plaintext; the route's rate limit is in-process and legacy codes may have lower entropy than new codes. | **PARTIALLY FIXED** | High | Inventory legacy codes safely, require distributed rate limiting, and plan a compatible code-rotation/upgrade before relying on public status lookup for sensitive applications. |
| Database-level cross-college/user isolation, write-denial, chat-message RLS, visitor-token enforcement, worker role, and pool-reuse behavior were not exercised. | **BLOCKED** | Critical | Run the required AIT/RCTI, missing-context, cross-user, mutation, worker, and pool-reuse tests only against an isolated migration-equivalent PostgreSQL database. |

## Rollback and recovery

**Automatic rollback SQL: BLOCKED / intentionally not supplied.** Migration 021 hashes and drops the existing plaintext invitation-token column and drops `initial_admin_password_hash`. Those values cannot be reconstructed from the new representation. Reinstating old application code or restoring prior policies would also risk reviving the known unsafe policy baseline and would not restore working pending invitation links.

The migration has **not** been applied, so there is currently nothing to roll back. Before any future deployment:

1. Take a verified database backup/PITR checkpoint and preserve the exact migration/schema version.
2. Validate migration and recovery on an isolated database with representative pending/accepted invitation rows.
3. If an issue occurs after deployment, prefer a reviewed **forward-fix** while retaining the secure hash-only schema. Pending invitations whose delivery is uncertain must be rotated/reissued through the verified application path.
4. Do not restore plaintext invitation tokens, restore unsafe `USING (true)` policies, or execute a downgrade on production without a separately reviewed and explicitly approved recovery plan.

## Acceptance criteria

| Criterion | Result |
|---|---|
| Signed tenant/user/super-admin context fails closed when key is absent | **PASS** in unit tests; database verification **NOT VERIFIED** |
| Caller-settable GUC alone cannot grant Super Admin access | **PARTIALLY FIXED** in repository design; isolated/live database proof **NOT VERIFIED** |
| Registration remains pending until approved and invitation accepted | **PARTIALLY FIXED** in repository/migration draft; database regression **BLOCKED** |
| Public registration/status access uses constrained operations | **PARTIALLY FIXED** in repository/migration draft; database grants and SQL behavior **BLOCKED** |
| Anonymous chat requires per-session visitor capability | **PASS** in focused mocked ownership tests; PostgreSQL RLS proof **BLOCKED** |
| Invitation pages use real APIs and do not invent local success | **PASS** |
| Real invitation delivery and production frontend URL | **FAIL** |
| Production migration has been tested on an isolated PostgreSQL database | **BLOCKED** |
| Current live Supabase state and runtime role have been verified | **NOT VERIFIED** |
| Production readiness / proceed to Phase 3B | **NO-GO** |

## Files changed in this continuation

- [auth.py](../../backend/app/api/v1/auth.py)
- [chat.py](../../backend/app/api/v1/chat.py)
- [super_admin.py](../../backend/app/api/v1/super_admin.py)
- [registration.py](../../backend/app/schemas/registration.py)
- [registration_repository.py](../../backend/app/repositories/registration_repository.py)
- [test_phase3a4_authz.py](../../backend/tests/test_phase3a4_authz.py)
- [test_chat_rls_and_telemetry.py](../../backend/tests/test_chat_rls_and_telemetry.py)
- [accept-invitation/page.tsx](../../apps/admin-frontend/src/app/(auth)/accept-invitation/page.tsx)
- [admins/page.tsx](../../apps/admin-frontend/src/app/super-admin/admins/page.tsx)

**Final recommendation: NO-GO.** Do not deploy migration 021 or proceed to Phase 3B until an isolated PostgreSQL validation passes, the signing key and function ownership are verified, invitation delivery is real and deployment-configured, and current live Supabase catalogs are reconciled.
