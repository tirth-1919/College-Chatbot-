# Phase 3A.4.1 — Isolated PostgreSQL Validation Report

## Executive decision

**NO-GO for production deployment or approval.** The proposed Phase 3A.4 SQL executed on a fresh, loopback-only PostgreSQL test database, and targeted application flows and unit tests were exercised. Tests demonstrated useful tenant and user isolation, but also exposed critical onboarding/approval blockers and a super-admin trust-boundary limitation. The test database was only a focused schema reconstruction, not a complete production-equivalent database.

No production database was connected to, changed, or deployed during this phase. The proposed patch and rollback are in [phase3a4-targeted-rls-security-fix.sql](./phase3a4-targeted-rls-security-fix.sql).

## Test environment and scope

- **PASS** — Initialized a new PostgreSQL 17.6 cluster and database `phase3a41_isolated` in the session-only directory `C:\Users\HP\.copilot\session-state\305399f6-e77f-40ce-91ea-ae4adf622fdb\phase3a41-postgres`, listening only on `127.0.0.1:55439`.
- **PASS** — Used a synthetic `college_app_user` runtime role; the existing PostgreSQL service on port 5432 and all live Supabase credentials were left untouched.
- **BLOCKED** — Full migration-chain validation was not possible because the local PostgreSQL installation does not include the `vector` extension. A focused subset of migrations and prerequisite RLS helpers/policies was used instead.
- **PASS** — Applied the proposed patch only to the isolated database. No migrations or SQL were executed against production.
- **PASS** — After testing, ran the patch's rollback only in the isolated database. The original policy expressions and enabled-RLS state were restored.

The test fixtures were synthetic. No real email was sent, and no existing production college IDs, users, memberships, or data were accessed or altered.

## Runtime-role and RLS checks

| Check | Result | Isolated evidence |
|---|---|---|
| Application role is not superuser | PASS | `college_app_user.rolsuper = false`. |
| Application role cannot bypass RLS | PASS | `college_app_user.rolbypassrls = false`. |
| Application role has no inherited role memberships | PASS | No role memberships were present for the test runtime role. |
| Runtime role owns protected tables | PASS | The affected protected tables were owned by `postgres`, not `college_app_user`. |
| RLS is enabled on `users`, `college_memberships`, `chat_sessions`, and `chat_messages` | PASS | Catalog inspection showed `relrowsecurity = true` for all four. |
| RLS is forced on those tables | PASS | `relforcerowsecurity = false`; FORCE is not required for the non-owner runtime role, which remains subject to RLS. This does not constrain a superuser/table owner. |
| Proposed helper functions have constrained search paths and grants | PASS | In the tested schema, inspected `SECURITY DEFINER` functions were owned by `postgres`, used fixed `search_path = pg_catalog, pg_temp`, had `EXECUTE` granted to `college_app_user`, and did not retain PUBLIC execution in the inspected ACL. |

### Critical super-admin context limitation

**FAIL — The runtime role can set `app.is_super_admin = true` itself.** In an isolated role-level check, the `college_app_user` connection set the custom GUC and the `is_platform_super_admin()` helper then accepted that context. PostgreSQL custom GUCs are not an authentication boundary. This means RLS super-admin policies are trustworthy only while the application database credential remains exclusively server-side and all application code that sets context is trusted; a holder of that credential can forge the setting. The proposed SQL does not independently prove that the GUC was set by trusted server authorization.

Do not treat this as authorization through `X-College-ID`; the test was a direct database-role capability check. Production approval requires an explicit, reviewed threat model and a trusted server-side boundary for platform-admin access.

## Policy and isolation results

| Required behavior | Result | Test outcome |
|---|---|---|
| User can read own profile, but not another user's profile | PASS | Isolated runtime-role reads were scoped to the current user; cross-user reads returned no row. |
| College memberships are limited to self, same-college authorized admin, or trusted platform-admin context | PASS | Cross-user and cross-tenant membership reads were denied in tested ordinary-user/tenant contexts. Super-admin results inherit the GUC limitation above. |
| AIT cannot read RCTI records and RCTI cannot read AIT records | PASS | Both directions were exercised with synthetic tenant rows and returned no cross-tenant data. |
| Missing tenant context exposes no protected tenant rows | PASS | Protected tenant queries returned no rows without tenant context. |
| Cross-tenant inserts and updates are rejected | PASS | Role-level mutation attempts against the other synthetic tenant were rejected by RLS. |
| User cannot read or mutate another user's private chat session in the same college | PASS | Another user's session was not visible and cross-owner mutations were denied. |
| Chat messages work only through an authorized session | PASS | User and assistant message rows persisted under the owning user's tenant/session; foreign-session access was denied. |
| Anonymous sessions are private to a visitor | NOT VERIFIED | The policy scopes anonymous sessions to a college but `user_id IS NULL` does not identify a visitor. Without a per-visitor credential/token, same-college anonymous sessions are not proven private. |
| Unauthorized user/membership writes are rejected | PASS | Cross-tenant attempts were rejected for tested ordinary runtime-role contexts. This does not eliminate the super-admin-GUC trust-boundary issue. |
| Super-admin cross-tenant access is protected from an untrusted database caller | FAIL | Direct runtime-role GUC spoofing succeeded; current helper design trusts a caller-settable value. |
| Full AIT/RCTI behavior against production-equivalent schema | NOT VERIFIED | The isolated schema omitted parts of the full migration chain and extensions. |

The proposed patch's permissive policies were evaluated as an effective set, not as isolated policy fragments. The focused role-level tests covered the changed `users`, `college_memberships`, `chat_sessions`, and `chat_messages` paths.

## Registration and onboarding results

| Flow/check | Result | Evidence |
|---|---|---|
| Public student registration and login | PASS | Database-backed registration and login completed under the isolated RLS context. |
| Email verification and password reset | PASS | Both paths completed against the isolated database. |
| Invitation acceptance, admin login, replay rejection, and expiry update | PASS | The invitation transaction completed with RLS enabled; replay was rejected and expiry state persisted after narrow repository fixes. |
| ORM user/assistant message and fallback-message persistence | PASS | Synthetic chat session/message writes and cross-user denial worked. No external model/provider call was made. |
| SQLAlchemy pooled connection reuse does not retain transaction-local tenant/user context | PASS | Reused connection and worker session checks observed context cleanup after transaction rollback. |
| Public `college_registrations` submission under the runtime role | FAIL | An attempted application-role insert was rejected. Migration 012 supplies only a `p_registrations_super_admin` policy for this table, so the public registration repository's insert path has no matching policy. |
| Legacy pending-college onboarding under the runtime role | FAIL | The application's pending `colleges` insert was rejected by the isolated RLS policies. The route subsequently provisions an admin and membership in the same onboarding flow. |
| Approval path waits for invitation acceptance before activating the initial admin | FAIL | With a synthetic registration seeded by the isolated setup role and notifications mocked, `approve_registration_transactional` created an active, verified `COLLEGE_ADMIN` and `ADMIN` membership immediately. It created no invitation row. This is inconsistent with invitation-gated provisioning. |
| Pending-college provisioning is restricted to approved colleges | FAIL | The proposed `can_provision_college_admin()` helper returned true for a pending, inactive college when the provisioning GUC/email values were set. It does not require the college's approval. |

The repository changes from the preceding Phase 3A.4 work introduce a timezone/context fix in [registration_repository.py](../../backend/app/repositories/registration_repository.py): invitation expiry now compares timezone-aware UTC values, establishes tenant context before mutation, and flushes user/membership changes before marking the invitation accepted. A focused regression test was added in [test_phase3a4_authz.py](../../backend/tests/test_phase3a4_authz.py). These fixes passed the selected tests below, but do not resolve the public registration or approval lifecycle blockers.

Relevant implementation evidence: the approval method creates an approved college and directly provisions the initial admin in [registration_repository.py](../../backend/app/repositories/registration_repository.py); the legacy onboarding route creates a pending college and admin in [colleges.py](../../backend/app/api/v1/colleges.py); and migration 012 defines the registrations policy as Super Admin-only in [012_college_onboarding_and_registration.sql](../../database/migrations/012_college_onboarding_and_registration.sql).

## Proposed SQL and rollback results

- **PASS** — The full proposed patch executed successfully on the isolated PostgreSQL database.
- **PASS** — The patch's rollback section executed successfully on that same isolated database.
- **PASS** — Post-rollback catalog inspection showed RLS still enabled on the four affected tables and restored the baseline policies, including the original unrestricted `users` and `college_memberships` SELECT expressions and tenant-only `chat_sessions` policy.
- **PASS** — Synthetic row counts were unchanged by rollback:

  | Table | Before rollback | After rollback |
  |---|---:|---:|
  | `users` | 14 | 14 |
  | `college_memberships` | 9 | 9 |
  | `chat_sessions` | 4 | 4 |
  | `chat_messages` | 8 | 8 |
  | `college_registrations` | 1 | 1 |
  | `college_admin_invitations` | 6 | 6 |

The restored policies are the **known unsafe baseline**, intentionally restored only to close out a disposable test database. This rollback result is not a recommendation to roll back any production policy. No data rows were removed by the patch rollback.

## Repository test and syntax results

- **PASS** — `python -m pytest tests\test_phase3a4_authz.py tests\test_chat_rls_and_telemetry.py tests\test_auth_endpoints.py tests\test_auth_security.py tests\test_database_models.py -q`: **35 passed**.
- **PASS** — Pylance syntax checks reported no syntax errors for the modified `registration_repository.py` and `test_phase3a4_authz.py`.
- **PASS** — Targeted database-backed registration, invitation, chat, role/RLS, and pool-context checks described above completed against the isolated database, except for the explicitly failed onboarding/approval cases.
- **NOT VERIFIED** — Full project migration-chain and full integration-suite validation; the isolated schema is incomplete due to the missing local `vector` extension.
- **NOT VERIFIED** — Actual production Supabase state after the earlier Phase 3A.3 read-only audit; this phase made no live connection.

## Acceptance criteria summary

| Criterion | Status |
|---|---|
| Proposed SQL parses and executes on an isolated PostgreSQL instance | PASS |
| `users` and `college_memberships` reads are appropriately scoped for tested ordinary users/tenants | PASS |
| Chat sessions enforce user and tenant ownership for authenticated users | PASS |
| Cross-tenant reads and mutations are denied in tested paths | PASS |
| Valid registration, authentication, verification, reset, and invitation paths work | PASS |
| Public college registration works with the proposed RLS/schema | FAIL |
| Initial admin activation is invitation-gated and approval-safe | FAIL |
| Pending-college admin provisioning requires approved/trusted authorization | FAIL |
| Super-admin context cannot be forged by a database-role caller | FAIL |
| Chat assistant/fallback persistence works in the exercised database path | PASS |
| Provider invocation, actual email delivery, and complete production-equivalent schema are verified | NOT VERIFIED |
| Production data/schema/roles/policies were left unchanged | PASS |
| Production readiness | NO-GO |

## Required follow-up before reconsideration

1. Resolve the product/security lifecycle for institutional registration: provide a narrowly authorized public submission path without granting broad registration-table access, and align both onboarding endpoints with the same policy.
2. Make initial administrator activation invitation-gated, or explicitly redesign and threat-model pending-college admin access. Do not retain a helper that authorizes arbitrary provisioning merely because a college is pending.
3. Replace or otherwise harden the super-admin trust boundary; a caller-settable custom GUC is not proof of server-side authorization. Keep the application database credential backend-only in the meantime.
4. Re-test the revised SQL and full repository migrations against a disposable PostgreSQL instance with the required extensions and production-equivalent role grants.
5. Repeat registration, approval, invitation, AIT/RCTI isolation, cross-user chat, missing-context, write-denial, pool-reuse, and worker checks. Include provider/chat API integration tests and an anonymous-session privacy decision.
6. Reconcile this report's findings with the current live database before deployment. Obtain explicit approval before any production SQL or policy change.

**Final recommendation: NO-GO for Phase 3B provider failover or production deployment until the blockers above are addressed and the revised design passes full isolated validation.** Provider failover should not proceed on the assumption that the tenant-security patch is production-ready.
