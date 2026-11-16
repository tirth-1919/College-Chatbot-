# Phase 3A.4.3 — Isolated PostgreSQL Migration, RLS, and Application Validation

## 1. Executive decision

# BLOCKED — NO SAFE ISOLATED POSTGRESQL ENVIRONMENT

No disposable database could be positively identified or created. PostgreSQL 17.6 binaries are installed, but pgvector is absent. The running Windows PostgreSQL service was not used because its data directory and purpose were not verified as disposable. Docker CLI is present, but Docker Desktop is not installed and the daemon is unavailable. Per the safety gate, no migration, database integration test, or full application test suite was run.

No production/Supabase connection was made. No production data, role, grant, policy, key, schema, or migration was changed. No secrets or credentials were read or printed.

## 2. Prerequisite reports

- **Available and reviewed:** [Phase 3A.4.1 isolated validation report](phase3a4.1-isolated-postgresql-validation-report.md).
- **Requested path not found:** `.agents/tasks/phase3a4.2-security-onboarding-fix-report.md`.
- **Available Phase 3A.4.2 report reviewed:** [Phase 3A.4.2 security and onboarding hardening report](phase3a4.2-security-onboarding-hardening-report.md). Its environment note was corrected after finding PostgreSQL binaries outside `PATH`.
- **Current migration reviewed statically:** [021_phase3a42_security_onboarding.sql](../../database/migrations/021_phase3a42_security_onboarding.sql).

## 3. Environment and isolation proof

| Check | Result | Evidence |
|---|---|---|
| PostgreSQL version | **PASS — available, not used** | `postgres.exe --version` reports PostgreSQL 17.6. |
| PostgreSQL binaries | **PASS — installed outside PATH** | `initdb.exe`, `pg_ctl.exe`, `psql.exe`, and `postgres.exe` exist under `C:\Program Files\PostgreSQL\17\bin`. |
| Existing PostgreSQL service | **NOT USED** | `postgresql-x64-17` is running. It was not connected to, stopped, or modified; its data directory is not verified as a disposable test cluster. |
| Required `vector` / pgvector extension | **BLOCKED** | `C:\Program Files\PostgreSQL\17\share\extension\vector.control` is absent. No replacement type or skipped migration was used. |
| `pgcrypto` extension files | **PASS — files present only** | `pgcrypto.control` exists. The extension was not created in any database. |
| `uuid-ossp` extension files | **PASS — files present only** | `uuid-ossp.control` exists. The extension was not created in any database. |
| Docker CLI | **PASS — installed** | Docker CLI version 29.9.3. |
| Docker daemon | **BLOCKED** | `docker info` failed because the Docker Desktop Linux engine named pipe is unavailable. |
| Docker Desktop | **BLOCKED** | The conventional Docker Desktop executable is absent. |
| Isolated database positively identified | **BLOCKED** | No cluster, database, test role, or isolated port was created or used. |

### Windows steps to establish an isolated environment

Docker Desktop is not installed on this machine. If approved for this workstation:

1. Install Docker Desktop for Windows using the organization's approved installer and enable its WSL 2 backend if prompted. Do not configure production credentials or connect it to Supabase.
2. Restart Windows if the installer requests it, then open **Start → Docker Desktop** and wait until Docker reports that its engine is running.
3. In PowerShell, verify the daemon with `docker info --format '{{.ServerVersion}}'` and verify the chosen pgvector image before creating a disposable container/database.
4. Alternatively, install a Windows PostgreSQL 17 pgvector build compatible with the installed PostgreSQL version. Keep its cluster in a new, dedicated data directory and bind it only to `127.0.0.1` on a dedicated port. Do not use the already-running Windows service.
5. Before proceeding, record the disposable cluster's data directory, port, database name, and synthetic runtime role; verify the connection identity and loopback binding without printing credentials.

Neither installation nor database creation was attempted.

## 4. Migration inventory and results

Static inspection found these SQL files, in the order used by the repository's filename-sorted runner:

| Order | Migration | Result |
|---:|---|---|
| 001 | `001_extensions.sql` | **BLOCKED — not executed** |
| 002 | `002_create_colleges.sql` | **BLOCKED — not executed** |
| 003 | `003_create_users_and_memberships.sql` | **BLOCKED — not executed** |
| 004 | `004_create_website_tables.sql` | **BLOCKED — not executed** |
| 005 | `005_create_document_tables.sql` | **BLOCKED — not executed** |
| 006 | `006_create_knowledge_tables.sql` | **BLOCKED — not executed** |
| 007 | `007_create_chat_tables.sql` | **BLOCKED — not executed** |
| 008 | `008_create_ai_and_audit_tables.sql` | **BLOCKED — not executed** |
| 009 | `009_create_feedback_and_support.sql` | **BLOCKED — not executed** |
| 010 | `010_create_indexes.sql` | **BLOCKED — not executed** |
| 011 | `011_prepare_rls.sql` | **BLOCKED — not executed** |
| 012 | `012_college_onboarding_and_registration.sql` | **BLOCKED — not executed** |
| 013 | `013_crawler_engine.sql` | **BLOCKED — not executed** |
| 014 | `014_document_processing_and_ocr.sql` | **BLOCKED — not executed** |
| 015 | `015_knowledge_and_rag_enhancements.sql` | **BLOCKED — not executed** |
| 016 | `016_analytics_support_and_multilingual.sql` | **BLOCKED — not executed** |
| 017 | `017_row_level_security_policies.sql` | **BLOCKED — not executed** |
| 018 | `018_create_application_role.sql` | **BLOCKED — not executed** |
| 019 | `019_complete_rls_policies.sql` | **BLOCKED — not executed** |
| 020 | `020_revoke_anon_grants.sql` | **BLOCKED — not executed** |
| 021 | `021_phase3a42_security_onboarding.sql` | **BLOCKED — not executed** |

`001_extensions.sql` explicitly requires `uuid-ossp`, `pgcrypto`, and `vector`. The repository runner at `scripts/migrate_and_seed.py` sorts and executes all `database/migrations/*.sql` files, then runs the development seed. It was inspected but **not run**, as required. There is no Alembic migration configuration under the backend or database directories.

The runner does not maintain a migration ledger or skip already-applied files. Migration 021 contains unguarded schema operations such as `ADD COLUMN`, so repeatability and fresh-database compatibility remain **NOT VERIFIED**. No migration was skipped, altered, or fabricated.

## 5. Migration 021 execution and schema compatibility

| Check | Result |
|---|---|
| Migration 021 parses and executes on actual preceding schema | **BLOCKED** |
| Complete fresh-database migration chain succeeds | **BLOCKED** |
| Enums, constraints, indexes, triggers, and foreign keys match application models | **NOT VERIFIED** |
| Existing invitation/registration row conversion succeeds | **NOT VERIFIED** |
| Migration idempotency behavior | **NOT VERIFIED** |
| Migration 021 was run on production | **NO — not run** |

The draft hashes and drops stored invitation plaintext tokens and drops `initial_admin_password_hash`. Existing-row nullability, duplicate hash conflicts, and compatibility with pending invitation data cannot be established from static inspection.

## 6. Runtime role, grants, RLS, and ownership

All catalog-dependent checks are **BLOCKED / NOT VERIFIED** because no isolated database was available:

- `college_app_user` role attributes (`rolsuper`, `rolbypassrls`, `rolinherit`), membership, table ownership, and actual effective privileges.
- Protected-table ownership, grants, enabled RLS, FORCE RLS, and combined policy behavior.
- Table inventory requested by the task: users, colleges, memberships, registrations, invitations, chat sessions/messages, documents, extracted facts, knowledge chunks/reviews, and website pages.
- Actual request runtime identity and whether ordinary requests use the least-privilege app role.

Static migration findings only: migration 018 specifies `NOSUPERUSER`, `NOBYPASSRLS`, and `NOINHERIT`, but grants broad DML on existing public tables and broad default privileges for later functions. Migration 020 revokes `anon` and `authenticated` grants. Migration 021 revokes PUBLIC execution on its listed functions and grants the runtime role. None of these declarations proves the effective privileges of an existing database.

## 7. Signed RLS context and key tests

| Test | Result |
|---|---|
| Missing application secret fails before SQL | **PASS — unit test from prior Phase 3A.4.2 focused run** |
| Invalid secret format/length | **NOT VERIFIED in this phase** |
| Matching app/database key verifies in PostgreSQL | **BLOCKED** |
| Wrong signature, expired context, or altered user/tenant/admin flags are rejected by PostgreSQL | **BLOCKED** |
| Direct GUC manipulation cannot grant Super Admin | **BLOCKED** |
| Ordinary user/college admin cannot obtain platform-wide access | **BLOCKED** |
| Approved platform Super Admin context works | **BLOCKED** |
| Temporary disposable test key provisioned | **NO — not provisioned** |
| Production key provisioned or inspected | **NO — not accessed** |

Static code evidence: [session.py](../../backend/app/database/session.py) creates a five-minute HMAC context and fails closed if `RLS_CONTEXT_SECRET` is absent or invalid. Migration 021 verifies the signature against `auth_private.rls_context_keys`. Database function ownership, schema/table ACLs, the key pair, HMAC compatibility, and actual expiry behavior remain unverified.

Production key provisioning must be a separate approved operation: generate a unique random 32-byte value in an approved secret manager, store the same value in the application secret store and the private database key table using an authorized database-owner procedure, then verify equality through a non-disclosing check. Do not put the key in source control, logs, or this report.

## 8. SECURITY DEFINER function review

Migration 021 defines or replaces these relevant functions: `auth_private.is_request_context_valid`, `public.current_app_user_id`, `public.current_app_tenant`, `public.is_platform_super_admin`, `public.is_current_college_admin`, `public.user_belongs_to_tenant`, `public.lookup_user_by_email_for_auth`, `public.lookup_college_invitation_by_token`, `public.accept_college_admin_invitation`, `public.submit_public_college_registration`, `public.check_public_registration_availability`, `public.get_public_registration_status`, and `public.submit_public_registration_information`. It also adds the `prevent_user_privilege_self_change` trigger function.

| Check | Result | Static finding |
|---|---|---|
| Actual function owners | **NOT VERIFIED** | No database catalog was available. |
| Effective PUBLIC/runtime/other-role EXECUTE ACLs | **NOT VERIFIED** | Migration ACL statements were inspected, not applied. |
| Search path and writable-schema safety | **FAIL — review required** | Multiple definer functions set `search_path` including `public`; actual CREATE privileges and ownership are unknown. |
| User-record minimization | **FAIL — code defect identified** | `lookup_user_by_email_for_auth(text)` is `SECURITY DEFINER`, returns `SETOF public.users`, and selects a row by caller-provided email. The runtime role is granted EXECUTE. This exposes more columns than the login flow needs (including stored authentication/verification fields) to any caller able to invoke the function with the backend role. |
| `can_provision_college_admin()` | **NOT FOUND in migration 021** | No definition was found in the current migrations/backend search. The earlier helper behavior cannot be validated from this migration. |
| Trigger owner assumption | **NOT VERIFIED** | `prevent_user_privilege_self_change` contains a `current_user <> 'postgres'` exception; migration 021 does not establish or verify the function owner. |
| Invitation authorization and approval checks | **NOT VERIFIED** | Static function checks approval, active college, invitation state/expiry, and authenticated invitee identity. Execution, atomicity, and trigger interaction require isolated DB tests. |

The user lookup finding should be corrected and revalidated before a Phase 3A.4.4 pass. No code change was made during this blocked validation phase.

## 9. Registration and onboarding

The full registration/approval/invitation flow was **NOT RUN**. No synthetic rows were created.

| Required assertion | Result |
|---|---|
| Public intake via constrained function without unrestricted table SELECT | **NOT VERIFIED** |
| Duplicate handling and tracking/status lookup | **NOT VERIFIED** |
| Additional-information submission | **NOT VERIFIED** |
| Public user cannot approve or read another application | **NOT VERIFIED** |
| Pending college cannot provision an active administrator | **NOT VERIFIED** |
| Approval alone does not activate the proposed admin | **NOT VERIFIED** |
| Invitation acceptance activates only the intended admin | **NOT VERIFIED** |
| Wrong email/college, expiry, revocation, replay, and atomic rollback | **NOT VERIFIED** |
| Existing registrations and invitation rows migrate safely | **NOT VERIFIED** |

## 10. Invitation email integration boundary

No email was sent. Static inspection identified a **FAIL**:

- `notification_service.py` does not invoke an SMTP/Resend/SendGrid transport. When a provider variable is set, the current branch can mark a notification `SENT` without sending.
- Invitation links are hard-coded to `http://localhost:3001`.
- The invite response contains no plaintext token, correctly avoiding token disclosure, but there is no real delivery path for the invitee to receive the hash-only token.
- No mocked transport test exists in the results for this phase.

This boundary must be fixed and tested with a mocked transport before a later database validation can pass. It was not changed in this phase because the required isolated-database prerequisite failed and the task directs stopping when that environment is unavailable.

## 11. Anonymous visitor-token validation

Static code inspection found token generation using `secrets.token_urlsafe(32)`, storage of a SHA-256 hash, one-time return on session creation, and token checks for anonymous session history, message, and delete paths. A wrong-token ownership unit test passed in the previous focused suite.

| Check | Result |
|---|---|
| Token entropy and hash-only storage in the database | **NOT VERIFIED in PostgreSQL** |
| Token required for history/messages/delete under actual RLS | **BLOCKED** |
| Two visitors in same/different colleges are mutually isolated | **BLOCKED** |
| Visitor cannot change tenant ownership | **BLOCKED** |
| Expiration/revocation of anonymous visitor tokens | **NOT IMPLEMENTED / NOT VERIFIED** |
| Transaction and pooled-connection cleanup for visitor token | **BLOCKED** |

No database test used `user_id IS NULL` as proof of visitor identity.

## 12. AIT/RCTI, chat, pooling, and worker checks

All PostgreSQL-level checks below are **BLOCKED**:

- AIT/RCTI cross-tenant read/write/delete isolation and missing-context behavior.
- Cross-user profile, membership, chat-session, and chat-message isolation.
- Assistant/fallback message persistence under `WITH CHECK`.
- Tenant/user/GUC tampering rejection.
- Connection commit, rollback, exception, reuse, and concurrent-request isolation.
- Async driver compatibility of the pool check-in listener.
- Worker tenant context, worker connection role, and retry/handoff cleanup.

Static worker paths use `tenant_session()` in background services/tasks, but that is not proof of actual role identity or database isolation. The pool listener attempts `DISCARD TEMP` and `RESET ALL`; those commands were not tested against an async PostgreSQL connection. Transaction-local settings are also present in application code, but cleanup must be proven with connection-reuse tests.

## 13. Repository regression tests

The mandatory environment gate failed before running the requested test commands in this Phase 3A.4.3 task. The preceding Phase 3A.4.2 turn recorded these results for the same repository state:

| Test type | Prior result | Limitation |
|---|---|---|
| Focused backend pytest selection | **40 passed** | Mocked/unit tests; not run as Phase 3A.4.3 DB validation. |
| Admin frontend Vitest | **7 passed** | Does not exercise PostgreSQL or real email delivery. |
| Admin frontend `npm run build` | **PASS** | No database validation. |
| Full backend suite | **NOT RUN in this phase** | Stopped at the missing isolated database prerequisite. |
| Real isolated PostgreSQL integration tests | **BLOCKED** | No pgvector-enabled disposable instance. |
| Live external email/provider tests | **NOT RUN** | No real messages or provider credentials used. |

Mocked results are not counted as PostgreSQL validation.

## 14. Recovery and rollback

Migration 021 contains irreversible changes: plaintext invitation tokens are hashed and the original column is dropped; `initial_admin_password_hash` is also dropped. Those values cannot be reconstructed. Do not invent a downgrade that restores plaintext tokens, restore the unsafe prior RLS baseline, or use production data for recovery testing.

No rollback was tested. Required next validation is a synthetic-row migration and recovery exercise on a disposable database. Prefer a reviewed forward-fix that retains hash-only tokens; rotate/reissue pending invitations through the application after delivery is reliable.

## 15. Change summary

- **Application/database code changes in this phase:** none.
- **Database actions:** none.
- **Documentation:** corrected the PostgreSQL/Docker environment evidence in the Phase 3A.4.2 report and created this validation report.

## 16. Remaining risks and exact next steps for Phase 3A.4.4

1. Install or provide an approved PostgreSQL 17 + pgvector test environment, or install/start Docker Desktop and use a verified pgvector PostgreSQL image. Do not use the existing running PostgreSQL service.
2. Positively identify the isolated data directory, loopback-only binding, dedicated port/database, and synthetic runtime role before any SQL execution.
3. Review/fix the broad `lookup_user_by_email_for_auth` return and the unimplemented email transport, false `SENT` status, and localhost invite URL.
4. Apply migrations 001–021 in filename order only to that disposable database (never through the prohibited seed runner). Stop at the first failure; record SQL state and migration.
5. Verify role ownership/grants, policy composition, function owners/ACLs/search paths, and synthetic RLS key behavior.
6. Run registration, invite, anonymous chat, AIT/RCTI, pooling, worker, and rollback/recovery tests with synthetic data and the actual `college_app_user` role.
7. Run the focused and full backend suites plus admin frontend tests/build, recording unit versus database-backed results separately.
8. Reconcile all findings and issue a new decision. Phase 3B and any production deployment remain on hold.

**BLOCKED — NO SAFE ISOLATED POSTGRESQL ENVIRONMENT**
