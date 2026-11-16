# Phase 3A.4.4B — Step 2A: Supabase Compatibility and Migration Blocker Resolution Plan

## Final decision: READY FOR APPROVAL

There is a reviewed path to resolve the blockers without touching production or the existing disposable PostgreSQL container. **This is approval to review the plan only, not authorization to install/start another stack, change migration files, create roles, or execute migrations.** Migration execution remains prohibited until the required corrections and environment are separately approved.

## Scope and evidence

All investigation was read-only. No migration, application role, policy, compatibility shim, Supabase project, secret, or application data was created. The existing `college-chatbot-pg17-test` container and its volume remain untouched.

The project has no `supabase/config.toml`, no Supabase CLI on `PATH`, and no Supabase images cached locally. Docker currently reports only `college-chatbot-pg17-test` running, using `pgvector/pgvector:pg17` and binding `127.0.0.1:55439`. Node.js `v26.5.0` is present; Scoop is not. The repository's `docker-compose.yml` is for Redis/backend/worker, not a Supabase Auth/Postgres stack.

## 1. Environment options

| Option | What it provides | Suitability and limitations |
|---|---|---|
| **Supabase CLI local stack — recommended** | Official local stack orchestrating Postgres, Auth (GoTrue), and other Supabase services. Official docs describe `supabase init`/`supabase start` as local-only until a directory is explicitly linked; Auth is enabled by default in local config. Supabase's role documentation describes `anon` and `authenticated`; its RLS docs document `auth.uid()`. | Best match for Supabase bootstrap dependencies and role/function presence. Configure a separate project with `db.major_version = 17`; the official Supabase Postgres repository documents PG 17.12 and a PG17-compatible `vector` extension package. The exact CLI image digest, extension namespace/version, and `auth.uid()` function must still be verified from the started local stack before DDL. It does **not** make this application's custom JWT become a Supabase Auth JWT. CLI is absent; the official Windows install options include Scoop or npm (npm requires Node 20+, and this machine has Node 26). No install/start was attempted. |
| **Compose official Supabase Postgres and Auth components manually** | Supabase Postgres provides a PostgreSQL distribution and extensions; Auth is a separate service. | Not recommended for this chain: the database image alone is not the complete Auth bootstrap. Manually wiring Auth, database migrations, roles, JWT settings, and service dependencies risks a subtly incomplete or version-mismatched stack. Prefer the CLI's supported orchestration. |
| **Current vanilla PostgreSQL 17 + pgvector plus test-only bootstrap** | Could be made to contain names such as `auth.uid()`, `anon`, and `authenticated`. | Not a Supabase compatibility test. A hand-written function/role bootstrap would not reproduce GoTrue/PostgREST initialization or request claims. It would also require changes to the preserved container, contrary to this plan's isolation preference. Do not use as the primary target; do not add a shim without explicit approval and prominent “shim-only” labeling. |

### Compatibility requirements for the recommended target

- Create a **new** Supabase CLI project in a scratch directory outside the repository, with a unique project ID, its own containers/network/volume, and PostgreSQL major version 17. Do not link or log in to a hosted project.
- Keep the existing `college-chatbot-pg17-test` container and `college-chatbot-pg17-test-data` volume intact. Select non-conflicting host ports and verify every published port is bound only to `127.0.0.1` before continuing.
- Before applying project migrations, positively verify PostgreSQL 17, database identity, container/image digest, dedicated volume, `auth` schema, `auth.uid()` signature/return type, and the `anon` and `authenticated` roles.
- Verify `uuid-ossp`, `pgcrypto`, and `vector` are available and usable. Check extension versions and schemas. The project migrations use an unqualified `vector` type and explicitly qualify `public.digest`, `public.hmac`, and `public.gen_random_bytes`; therefore extension placement/search path matters. Do not assume the CLI image's extension schema matches the existing vanilla image.
- Supabase's published extension manifest lists a PG17-compatible `vector` build, while the existing disposable database reports pgvector `0.8.7`. The exact CLI image's installed version is not established by documentation alone. At runtime, confirm the `vector` extension version and that the migration's vector type/HNSW index requirements are supported; record the actual image and extension versions.
- The local CLI setup may print local database/API credentials. Keep that output local and out of reports/logs; use only test-only credentials protected on disk. Never supply production environment files or credentials.

## 2. Migration 017: `auth.uid()` use and authentication model

Migration 017 has five calls across these policies:

| Table | Policy | `auth.uid()` purpose in policy |
|---|---|---|
| `support_tickets` | `p_support_tickets_tenant_isolation` | Permit a ticket row when its `user_id` matches the request user, in addition to tenant/super-admin predicates. |
| `support_ticket_replies` | `p_ticket_replies_student_read` | Identify the ticket owner for reading non-internal replies. |
| `support_ticket_replies` | `p_ticket_replies_staff_insert` | Identify the ticket owner in the insert predicate, in addition to tenant/super-admin predicates. |
| `in_app_notifications` | `p_notifications_user_isolation` | Match notifications to a request user. |
| `feedback` | `p_feedback_tenant_isolation` | Match feedback to its request user. |

Supabase documents `auth.uid()` as returning the UUID of the user making the request; it is derived from Supabase's request/JWT identity context and is null when no authenticated user context is present. It is not a generic way to read an application's arbitrary bearer token.

The application uses **custom application authentication**, not Supabase Auth:

- `POST /login` calls the backend `AuthService`, verifies the local password hash, and issues a JWT signed with the application's configured key.
- Protected routes verify that application JWT and load the local `users` row.
- `set_rls_context()` signs the resolved identity/tenant values with the independent RLS context secret, then sets transaction-local `app.*` settings. Migration 021's `current_app_user_id()` validates that HMAC context before returning an identity.
- Supabase client usage found in the backend is for Storage; no Supabase Auth sign-in flow was found.

Consequently, a Supabase CLI stack will satisfy the **SQL dependency** on `auth.uid()`, but the backend does not set Supabase's JWT claim context. For requests made by this backend, `auth.uid()` will not represent the custom application's user. The project must not switch to Supabase identity implicitly or replace `auth.uid()` with an unsigned GUC/constant.

**Required correction for approval:** remove the user-identity dependency on `auth.uid()` from the application's RLS policy chain. Make the signed application identity helper available before user-specific policies are installed, or defer those policies until migration 021 has installed the signed helper. Then define final, explicit `USING` and `WITH CHECK` rules using the verified application user/tenant/admin helpers. Review the intended permissions per operation:

- Students may access only their own support tickets and non-internal replies; internal replies are staff-only.
- College admins may access tickets/replies for their verified college; super-admin access remains explicit.
- Notification reads/updates must remain user-scoped. Notification creation also needs an approved backend/service authorization path because application code can create a notification for a different recipient.
- Feedback submission supports optional/anonymous users, while feedback listing is admin-scoped. The database policy and route context must agree on those cases.

Migration 021 currently replaces user, membership, and chat policies but does **not** mention or replace the five policies above. They would remain after 021. In addition, the current tenant `OR` clauses and support-reply internal-note logic need a policy-level review rather than a mechanical function-name substitution. Add allow/deny tests for the actual app roles and each operation before approving the SQL correction.

## 3. Migration 018: application role and grants

### Role requirements

The backend's async engine connects through `DATABASE_APP_ROLE_URL` as `college_app_user`; normal application operation therefore requires a database role with `LOGIN`. The migration intends the role to have `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE`, `NOINHERIT`, and `NOBYPASSRLS`, and not own application tables. These attributes are appropriate starting constraints; also verify no role membership or ownership path grants bypass/owner privileges.

The password comment says to overwrite the migration's placeholder through database settings or `ALTER ROLE`. That appears intended to avoid embedding a real credential in source, but the SQL still creates a usable `LOGIN` role with a known placeholder password. It must not be used as-is.

### Effective privileges

Migration 018 grants:

- `CONNECT` on the database literally named `postgres`;
- `USAGE` on schema `public`;
- `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on **all** current public-schema tables;
- `USAGE` and `SELECT` on all current public-schema sequences;
- `EXECUTE` on `current_app_tenant()` and `is_platform_super_admin()`;
- default DML grants on all future tables, sequence grants on all future sequences, and `EXECUTE` on all future functions created by the migration role in `public`;
- no `CREATE` privilege on schema `public`.

The current Step 1 database is named `college_chatbot_test`, so the literal `GRANT CONNECT ... ON DATABASE postgres` does not target that database. The official CLI local database default is named `postgres`, so this particular grant aligns only if that default is retained. A portable correction should grant CONNECT to the actual migration database (for example via a reviewed `current_database()`-based statement) or explicitly configure and verify the database name.

The DML and default function grants are broad. PostgreSQL default privileges are scoped to the role that executes `ALTER DEFAULT PRIVILEGES` and to objects subsequently created by that owner; they are not a universal grant for every possible migration owner. The default `EXECUTE` grant can expose future functions, including future security-definer functions, to the runtime role. The comment that extension-owned objects are excluded is not enforced by `GRANT ... ON ALL ... IN SCHEMA public`. Prefer an approved table/function grant matrix and only narrowly scoped default grants.

### Proposed credential-safe correction

1. Create `college_app_user` initially as `NOLOGIN`, with no password set, while the migration chain is under review and validation. Keep all network/API consumers offline.
2. Apply explicit reviewed grants and verify `NOBYPASSRLS`, non-ownership, and no privileged memberships.
3. Only after the complete chain and RLS checks pass, enable `LOGIN` and provision a random **test-only** password through an interactive `psql \password college_app_user` prompt or an equivalent protected secret channel. Do not put the password in migration SQL, command-line arguments, logs, or this report.
4. Keep test credentials in a locally ACL-restricted secret file/manager and use them only for the isolated runtime test. No credential was generated or provisioned during this phase.

## 4. Migration 020: Supabase roles

Migration 020 has six unconditional privilege revocations from `anon` and six default-privilege revocations from `anon`/`authenticated` (tables, sequences, and functions). Its two suggested function grants are commented out and do not execute.

On the vanilla Step 1 image, `anon` and `authenticated` are absent; PostgreSQL does not treat `REVOKE ... FROM nonexistent_role` as a no-op. On a Supabase local stack these are standard API roles and should be provided by the official bootstrap. Keep migration 020 in the reviewed sequence; do not skip it or silently manufacture substitute roles. After it runs, verify effective grants and default privileges for the actual object owners, because `ALTER DEFAULT PRIVILEGES` affects only its executing owner.

## 5. Migration 019 → 021 and transaction/maintenance strategy

Migration 019 installs broad intermediate policies including `USING (true)` for user reads, `WITH CHECK (true)` for user inserts, and `USING (true)` for membership reads. Migration 021 replaces the user and membership policies with signed-context/self/tenant/admin rules, and replaces chat session/message policies with signed tenant/user or hashed visitor-token rules.

That transition is safe to test only while the application and any API client are prevented from connecting. A new local stack should use loopback-only ports; do not start the application; keep `college_app_user` `NOLOGIN`; and, where supported by the approved local config, disable the Data API during migration work. Use only the privileged migration connection. Do not run the chain against a hosted project.

Migration 021 and 022 each contain their own `BEGIN`/`COMMIT`. They must not be nested inside a single transaction that spans the whole chain: their `COMMIT`s would end that outer transaction. The reviewed 001–020 files do not contain explicit file-wide wrappers, database creation, or concurrent index creation. The recommended future boundary is **one transaction per migration**:

- Run 001–020 one file at a time with fail-fast behavior and a per-file transaction, after confirming the runner's transaction option and the PostgreSQL 17 enum behavior. The new enum labels in 013, 014, and 016 are not used by those same files; later files run after commit.
- Run 021 and 022 separately with fail-fast behavior, using their own explicit transactions and without an additional single-transaction wrapper.
- Stop at the first nonzero result and record file, timestamps, result, and SQLSTATE. Never continue the sequence after an error. Because earlier per-file commits remain, a failed disposable run should be treated as incomplete; do not resume blindly. Preserve its logs and either obtain an approved repair or discard only that newly created Supabase test project.

## 6. Recommended execution plan after approval

1. **Approve migration corrections first.** Review the 017/021 signed-context policy changes and operation-level permissions; correct 018's initial login/password behavior, database grant target, and overbroad default grants. Do not change files until separately authorized.
2. **Provision a separate CLI workspace.** Install/pin the Supabase CLI in an isolated scratch folder (Node 26 satisfies the documented npm runtime floor). Run local initialization/start only from that folder; do not run `supabase login` or `supabase link`. Configure PostgreSQL major 17 and a protected test-only DB password. Preserve the existing PostgreSQL container/volume.
3. **Verify the live local stack before migration DDL.** Capture non-secret evidence for container/image IDs, healthy status, PostgreSQL 17 version, database identity, loopback-only bindings, dedicated volume, Auth service, `auth` schema/function, required roles, extension availability/version/schema, and relevant function signatures. Do not report a Supabase compatibility test until these checks actually pass.
4. **Apply the reviewed SQL directly, one file at a time.** Use psql with `ON_ERROR_STOP`, avoiding `scripts/migrate_and_seed.py` and any automatic seed path. Execute only migrations 001–022, in order, with the per-file transaction boundaries above. Keep the application and external API clients offline.
5. **Validate schema and security.** Check objects, function owners/search paths, RLS policies, role attributes/memberships, table/sequence/function grants, and default privileges. Test RLS using generic disposable tenants/users—not AIT/RCTI data—with transaction-local signed test context and rollback fixtures. Include both allowed and denied cases for tickets, internal replies, notifications, and feedback. Do not mistake `auth.uid()` returning NULL on a direct SQL connection for an Auth integration test.
6. **Enable a test runtime login only after validation.** Provision a separate random test-only password via protected interactive/secret handling; confirm the role remains non-owner and `NOBYPASSRLS`, then test only against the isolated local stack.
7. **Clean up only the new local project when authorized.** Stop that project with its own CLI work directory/project ID, inspect exact container and volume names, and remove only those reviewed resources. Do not run `docker system prune`; do not stop, delete, or overwrite `college-chatbot-pg17-test` or its volume.

### Preflight and final verification query shapes

These are proposed checks only; none were run against a Supabase stack in this phase:

```sql
SELECT current_database(), current_user, version(),
       inet_server_addr(), inet_server_port();

SELECT e.extname, e.extversion, n.nspname AS extension_schema
FROM pg_catalog.pg_extension AS e
JOIN pg_catalog.pg_namespace AS n ON n.oid = e.extnamespace
WHERE e.extname IN ('vector', 'pgcrypto', 'uuid-ossp');

SELECT to_regnamespace('auth') AS auth_schema,
       to_regprocedure('auth.uid()') AS auth_uid;

SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolinherit, rolbypassrls
FROM pg_catalog.pg_roles
WHERE rolname IN ('anon', 'authenticated', 'college_app_user');

SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
FROM pg_catalog.pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

Additional approved checks should confirm `auth.uid()` returns `uuid`, is NULL without an authenticated Supabase request context, and returns the verified subject only through the local Auth/API path; check `to_regtype('vector')` and the schema-qualified `public.digest`/`public.hmac` references used by the migrations; inspect `has_table_privilege`, `has_sequence_privilege`, function EXECUTE grants, RLS flags, ownership, and role memberships.

## 7. Isolation and cleanup

- Keep the current disposable PostgreSQL container, its `127.0.0.1:55439` binding, dedicated volume, and test-only password file intact.
- Create any future Supabase CLI project separately, with unique resources and local-only credentials. Never link it to or contact production Supabase.
- Use only generic synthetic test fixtures after approval; never AIT/RCTI data.
- Cleanup applies only to the new CLI project after explicit authorization and resource-name verification. No cleanup was performed.

## 8. Sources and repository evidence

Official documentation/source reviewed on 2026-11-16:

- [Supabase CLI local development](https://supabase.com/docs/guides/local-development/cli/getting-started) — local stack includes Postgres and Auth; local initialization does not itself link a hosted project.
- [Supabase CLI configuration](https://supabase.com/docs/guides/local-development/cli/config) and [CLI config template](https://github.com/supabase/cli/blob/develop/apps/cli/src/shared/init/testdata/templates/config.toml) — local Auth config and PostgreSQL `major_version` setting.
- [Supabase Docker/native runtime guidance](https://supabase.com/docs/guides/local-development/docker-and-native-runtimes) — Docker project isolation/runtime behavior.
- [Supabase Postgres repository](https://github.com/supabase/postgres) and [extension version manifest](https://github.com/supabase/postgres/blob/develop/nix/ext/versions.json) — PostgreSQL 17 and pgvector packaging.
- [Supabase RLS guide](https://supabase.com/docs/guides/database/postgres/row-level-security) — `auth.uid()` semantics and role/policy behavior.
- [Supabase Postgres roles](https://supabase.com/docs/guides/database/postgres/roles) and [pgvector guide](https://supabase.com/docs/guides/database/extensions/pgvector).

Repository evidence:

- [`auth_service.py`](../../backend/app/services/auth_service.py), [`jwt.py`](../../backend/app/security/jwt.py), [`dependencies/auth.py`](../../backend/app/dependencies/auth.py), and [`session.py`](../../backend/app/database/session.py) establish custom JWT authentication and signed transaction-local RLS context.
- [`017_row_level_security_policies.sql`](../../database/migrations/017_row_level_security_policies.sql), [`018_create_application_role.sql`](../../database/migrations/018_create_application_role.sql), [`019_complete_rls_policies.sql`](../../database/migrations/019_complete_rls_policies.sql), [`020_revoke_anon_grants.sql`](../../database/migrations/020_revoke_anon_grants.sql), and [`021_phase3a42_security_onboarding.sql`](../../database/migrations/021_phase3a42_security_onboarding.sql) establish the migration dependencies and policy transitions described above.
- [`support_service.py`](../../backend/app/services/support_service.py), [`support.py`](../../backend/app/api/v1/support.py), [`notifications.py`](../../backend/app/api/v1/notifications.py), and [`feedback.py`](../../backend/app/api/v1/feedback.py) show route-level ownership, role, notification, and feedback workflows that the final RLS rules must preserve.

## Confirmation

No migrations were executed. No database or production changes occurred. No production credentials or `.env` secrets were read. No roles, policies, shims, fake production data, or application/migration file changes were made. Only this requested plan report was created.
