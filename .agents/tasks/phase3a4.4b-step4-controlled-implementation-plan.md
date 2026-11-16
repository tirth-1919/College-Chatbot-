# Phase 3A.4.4B — Step 4: Controlled Implementation Plan

## 1. Executive decision: READY FOR HUMAN REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION — NOT DATABASE VALIDATED

This report is a read-only implementation plan based on the Step 3 package, the Step 3.1 addendum, current repository source, migration SQL, tests, and local documentation. It recommends a staged implementation and database-validation process, but **does not authorize implementation, role/privilege changes, provisioning, or migration execution**.

The worktree migration history is not sufficient to choose Branch A or Branch B. Repository documentation contains instructions for applying SQL to Supabase, and a CD workflow contains a deployment job, but neither proves that any migration was applied, released, or deployed. An authorized human must establish the history for every relevant environment before selecting a branch.

Implementation remains blocked pending Gate 1–4 approvals and completion of the unknowns listed in this plan. No production database or `.env` was accessed; no SQL, migration, test, or container operation was run in this phase.

The status terms are distinct:

| Status | Meaning here |
|---|---|
| **READY FOR HUMAN REVIEW** | Current report status only: the proposal is available for human review. |
| **READY FOR IMPLEMENTATION APPROVAL** | Not reached; unresolved decisions and migration history remain. |
| **IMPLEMENTATION AUTHORIZED** | Not granted by this report or the prior planning steps. |
| **DATABASE VALIDATED** | Not claimed; no database or tests were executed in this phase. |

## 2. Original findings retained; corrected proposals identified

The Step 3 and Step 3.1 decisions remain proposals subject to the same human approvals: custom signed application identity (not `auth.uid()`), 24-hour absolute visitor-token expiry and matching-token feedback, guest-ticket create-only, aggregate-only college analytics, least-privilege user fields, protected audit/telemetry writes, and no general worker tenant setter. The prior findings about broad policy OR behavior, sensitive `select(User)` reads, raw GUC setters, migration 021/022 ownership, and uncertain migration history are retained. The worker-isolation recommendation is refined below to prefer tenant-isolated workers or approved trust cohorts; this is a proposal explicitly requiring the existing human decision, not a silently changed approved design.

The only project files changed for this correction are the existing Step 4 report and the separate requested change summary. No application, SQL, migration, test, or configuration source files were changed. No SQL statement, migration, test, seed script, production system, or existing PostgreSQL test container was executed or modified. The new PostgreSQL 17 membership query is documentation only and remains unexecuted.

All AIT/RCTI names in the proposed tests are fixture labels only. The test data must be synthetic with newly generated IDs and no real institutional information.

## 3. Repository evidence inspected

### Migration and design evidence

- The complete numbered migration inventory is `database/migrations/001_extensions.sql` through `database/migrations/022_minimize_auth_lookup.sql`.
- Prior Step 2 inventory states migrations 001–022 were reviewed, but none was executed in the preserved vanilla PostgreSQL test database. The report found the `auth.uid()` dependency in 017, Supabase role dependencies in 020, broad application grants in 018, and intermediate permissive policies in 019.
- Exact top-level `BEGIN;`/`COMMIT;` statements occur in 021 and 022 only. Other migrations contain procedural `BEGIN` blocks inside `DO` or function bodies, not file-wide transaction wrappers.
- Step 3 and Step 3.1 specify the proposed signed context, visitor-token, worker-lease, least-privilege, audit/telemetry, notification, and security-definer design. These remain proposals, not validated database behavior.

### Backend and test evidence

Current source confirms relevant paths in:

- `backend/app/database/session.py`, `backend/app/database/connection.py`, `backend/app/dependencies/auth.py`, `backend/app/dependencies/tenant.py`
- `backend/app/api/v1/auth.py`, `chat.py`, `feedback.py`, `support.py`, `users.py`, `memberships.py`, `colleges.py`, `college_admin.py`, `analytics.py`, `super_admin.py`
- `backend/app/models/user.py`, `chat.py`, `college.py`, `membership.py`, `registration.py`, `audit.py`, `ai.py`
- `backend/app/repositories/user_repository.py`, `college_repository.py`, `college_admin_repository.py`, `registration_repository.py`, `super_admin_repository.py`
- `backend/app/services/auth_service.py`, `support_service.py`, `in_app_notification_service.py`, `notification_service.py`, `ai_provider_service.py`, `document_service.py`, `crawler_service.py`, `knowledge_service.py`, `rag_service.py`
- `backend/app/tasks/celery_app.py`, `document_tasks.py`, `knowledge_tasks.py`, and `crawler_tasks.py`
- Existing focused tests include `backend/tests/test_auth_lookup.py`, `test_multi_tenant_isolation.py`, `test_chat_rls_and_telemetry.py`, `test_analytics_and_support.py`, `test_phase3a4_authz.py`, `test_email_notifications.py`, `test_auth_security.py`, and `test_database_models.py`.

The CI workflow runs backend tests with SQLite and does not establish real PostgreSQL RLS behavior. No dedicated Supabase/PostgreSQL RLS integration harness was identified in the inspected test files. No tests were run for this plan.

### Migration/deployment history evidence and limits

- `database/README.md` documents manual execution through the Supabase SQL Editor or `psql`; it is guidance, not an execution record.
- `.github/workflows/cd.yml` publishes container images and has a deployment job whose SSH/webhook deployment commands are comments/placeholders. It has no migration-application step.
- `.github/workflows/ci.yml` runs tests with an in-memory SQLite URL, not a Supabase/PostgreSQL migration target.
- The inspected repository documentation and workflow contain no authoritative per-environment migration ledger or evidence of which migrations have been applied.

**UNVERIFIED:** whether any migration 001–022 has been applied, released, or deployed in staging, production, a shared database, or another environment. Repository inspection cannot prove otherwise. A human with authorized deployment records must confirm this; do not connect to production to answer it as part of this phase.

## 4. Corrected migration 021 transaction plan

Migration 021 has its own `BEGIN` at the start and `COMMIT` at the end. There is no safe pause after executing its statements but before its internal commit. Required checks therefore belong either in preflight before starting 021 or as SQL assertions placed inside the migration transaction before `COMMIT`. A migration runner must not expose an intermediate state to application clients.

### Preflight before starting migration 021

On a separately approved disposable target only, and before the migration transaction:

1. Positively verify the target database, server version, isolated project/volume, local-only network binding, Supabase Auth schema/function and `anon`/`authenticated` roles, required extensions, and the expected migration predecessor. Stop on any mismatch.
2. Verify that every prerequisite relation, column, enum, extension routine, and role expected by 021 exists; verify the new columns/indexes/functions/policies created by 021 do not already exist. Check the migration ledger and schema for partial prior application. Do not rerun or guess state.
3. Keep the application, worker, pooler, and PostgREST/Data API clients disconnected. Confirm `college_app_user` and any worker role are `NOLOGIN`; only the approved migration principal is connected.
4. Take an approved snapshot/restore point if the target contains synthetic rows. Obtain explicit approval of the forward/backfill/contract behavior for any existing rows.
5. Run count-only data preflights without displaying tokens or hashes: invitation row count; NULL/empty `invitation_token` count; duplicate SHA-256 digest count; existing `initial_admin_password_hash` non-NULL count; existing guest sessions that have no visitor hash; and conflicting index/key values. A nonzero invalid-token or duplicate-hash count is a blocker. If any initial-admin password hashes remain and there is no approved preservation/retirement path, do not start 021.
6. Confirm no application caller still depends on the soon-to-be-dropped plaintext invitation token or `initial_admin_password_hash`. This is a source/contract review, not a catalog query.

### Assertions inside 021, before its internal COMMIT

The corrected migration must contain fail-closed assertion blocks, after the relevant operations but before its existing `COMMIT`:

- Immediately after invitation hash backfill and before dropping `invitation_token`: assert the row count is unchanged; every source token is non-NULL/nonempty; every new hash is non-NULL and equals the expected digest of its source token; and the resulting hashes are unique. Do not select or print token/hash values in notices or error text.
- Before dropping `college_registrations.initial_admin_password_hash`: assert the count of non-NULL values is zero, unless a separately approved migration has already transformed/preserved the values and the exact invariant is asserted. Otherwise raise an exception and abort.
- After token/index changes: assert the invitation hash column is NOT NULL, the unique index exists and is valid, and the plaintext token column is absent. Verify `initial_admin_password_hash` is absent only after the pre-drop assertion succeeded.
- For existing guest sessions, set the approved absolute expiry to the original creation time plus 24 hours; never extend it. Sessions with no recoverable matching visitor hash must fail closed rather than receive a fabricated token capability. Assert there is no live guest row treated as authorized without a valid matching hash and expiry.
- At the end of the migration, assert expected helper and policy functions exist with the intended signatures; RLS is enabled on every intended table; final policies are present; all legacy policies intended for removal are absent (including the five `auth.uid()` policies and broad permissive OR branches); the app and worker roles remain NOLOGIN; and security-definer owner/path/ACL assertions in Section 6 pass.

Any failed assertion must `RAISE EXCEPTION` (or otherwise return a nonzero migration result) before `COMMIT`, causing the whole 021 transaction—including DDL, token backfill, and drops—to roll back. The runner must stop immediately. Do not continue to 022 or test the partial state.

### Commit boundary and recovery

Once 021 reaches its own `COMMIT`, it is committed. A later catalog or application check cannot retroactively roll it back. If a post-commit check fails, keep all application clients offline, mark the target incomplete, and either rebuild only that specifically approved disposable target or use a separately reviewed forward repair. For a deployed Branch B environment, use its approved backup/restore or forward-only recovery plan. Do not recreate empty plaintext columns or claim that this restores dropped values. No preflight or in-transaction check above was executed for this report.

## 5. Corrected runtime-role testing strategy

The production capability/runtime roles can remain `NOLOGIN` during migration and RLS validation. A disposable **test harness login** may use one narrowly approved SET-only membership to the target NOLOGIN role; it must not own application objects, be superuser, have `BYPASSRLS`, or receive unrelated memberships. After `SET ROLE college_app_user`, `current_user` and `current_role` identify `college_app_user`, but `session_user` remains the harness login. A direct production login would instead have the authenticated service login as `session_user`; `SET ROLE` does not reproduce that fact. Do not claim it fully reproduces direct-login behavior.

| Approach | What it validates | What it does not validate | Membership/escalation and credential controls |
|---|---|---|---|
| Separate test-login role with copied direct grants | Some object ACL behavior for the clone and the fact a disposable login can connect. | It can drift from runtime grants; policies and functions targeted to `college_app_user` may not treat the clone identically; matching direct grants does not reproduce role membership/default-privilege paths or prove the intended role's effective access. | Keep test-only, local, no owner/superuser/BYPASSRLS, and never reuse a production URL/password. Do not create the clone during this phase. |
| **Dedicated harness login plus controlled `SET ROLE` — recommended for capability/RLS tests** | Checks effective privileges and RLS while `current_user`/`current_role` is the actual NOLOGIN runtime role. Exercises role-targeted policies, grants, function EXECUTE, row filters, and denied operations without enabling runtime LOGIN. | Does not validate the runtime role's own authentication, connection-pool identity, or `session_user` behavior as a direct login. `session_user` remains the harness. Any production path that relies on `session_user` must be separately tested with a matching disposable connection principal or remain unvalidated. | Create only in the approved disposable stack. The harness must be `NOINHERIT`, non-owner, non-superuser, non-BYPASSRLS, and have a single tightly scoped SET-only membership; no path to owner/admin roles. Assert identity values before each test. |
| Temporarily enable LOGIN on the intended runtime role | Direct authentication and connection behavior for that principal. | Not needed to prove RLS/effective privileges; it increases operational risk and can accidentally permit application connections before approval. | Not recommended for Gate 5 and prohibited by this planning phase. If an actual runtime-login smoke test is later required, it needs separate explicit approval and an isolated target after all security tests. |

### Effective-privilege verification

Do not compare role names or only inspect direct grants. Production authorization may involve several distinct identity inputs; each must be audited rather than conflated:

| Identity input | Production security path to inspect | What the repository evidence establishes / does not establish |
|---|---|---|
| `session_user` | Initial authenticated PostgreSQL connection identity; any RLS/helper/function checks, worker-pool principal mapping, audit attribution, or `SECURITY DEFINER` caller validation that reads it. It remains unchanged inside `SECURITY DEFINER`. | The backend uses a shared engine in `backend/app/database/connection.py`; the reviewed plan does not establish that production policies/functions rely on `session_user`. That absence must be verified from every relevant policy and function definition before the harness is treated as equivalent. |
| `current_user` / `current_role` | Effective SQL privilege identity, grants, role-targeted policies and function execution. `current_role` is the SQL alias for the effective role. `SECURITY DEFINER` changes the effective identity to the function owner while executing. | `SET ROLE` reproduces the selected runtime role for these checks, but not the direct-login `session_user`; inspect all functions/policies for identity checks and do not infer caller identity from `current_user` inside a definer function. |
| Role membership | Whether a principal can inherit privileges, `SET ROLE`, administer memberships, or reach a privileged owner/role; also affects effective ACL checks. | Direct membership alone is insufficient. Use the PostgreSQL 17 transitive-path audit below and check effective privileges after the role switch. |
| Signed application identity | User, tenant, worker, visitor, purpose, request, transaction, expiry and lease claims validated by the HMAC verifier; raw GUCs are not evidence. | `backend/app/database/session.py` signs/sets application context and the migration design supplies database verification. Test forged GUCs and signatures independently of PostgreSQL role identity. |
| Connection identity | The credential/principal selected by engine/pool configuration and its separation between web and worker processes. | The reviewed implementation uses a shared application engine and does not establish a separate worker connection principal. Treat worker connection identity as unimplemented/unverified until approved. |

After each controlled role switch:

1. Verify `current_database()`, server address/port, `session_user`, and `current_user`; abort unless the target is the approved local stack and `current_user` is the intended NOLOGIN role.
2. Verify the expected identity tuple: for the harness, `session_user` must be the test login while `current_user = current_role` must be the intended runtime role. Fail the test if an unexpected login, role, owner, or identity value appears. Inspect every production security path for the identity field it consumes; if it relies on `session_user`, this `SET ROLE` test is not a substitute for an approved disposable direct-login test.
3. Inspect direct and transitive role membership, including `SET`, `INHERIT`, and `ADMIN OPTION` paths using PostgreSQL 17 semantics as specified below. Verify that no runtime, harness, or negative-test principal can reach an unapproved owner/admin role.
4. Use `has_schema_privilege`, `has_table_privilege`, `has_column_privilege`, and `has_function_privilege` for effective privileges, then exercise known-existing positive and negative fixtures under `SET ROLE`. A privilege helper alone does not prove RLS row isolation.
5. Check `CONNECT` ACL separately with `has_database_privilege`; `SET ROLE` does not test authentication or the login role's ability to establish a connection.
6. Keep local test host/project identifiers and disposable credentials separate from all production configuration. Do not read `.env`, link/log in to hosted Supabase, embed a password in SQL/CLI arguments, or print a connection URL.

### PostgreSQL 17 transitive role-membership audit (proposed; not executed)

Inventory the protected-role set before evaluating memberships: all roles with `rolsuper` or `rolbypassrls`; owners of relevant schemas; every protected relation including sequences, tables, partitioned tables, views, materialized views and foreign tables; owners of all functions/procedures and other routines; owners of types/domains; extension owners; owners of default-ACL entries; the approved migration-owner role(s); and every built-in or custom role with elevated data, monitoring, DDL, or operational privileges. Also include owners of collations, conversions, operators, operator classes/families, event triggers, large objects, foreign-data wrappers/servers, procedural languages, text-search objects, publications/subscriptions, the current database, and tablespaces when present or relevant. The migration owner and other custom privileged roles must be identified by the accountable owner; PostgreSQL catalogs do not label them semantically.

Use a cycle-safe recursive traversal from every relevant login/runtime/harness/negative principal through `pg_auth_members.member -> roleid`. Carry the entire role path and the per-edge `set_option`, `inherit_option`, and `admin_option` values (PostgreSQL 17); do not collapse paths to a boolean or inspect only direct memberships. For each transitive route to a protected role, report the ordered role path and all edge flags. Additionally check effective `pg_has_role`/`has_*_privilege` results. Treat any route with effective `SET`, inherited privilege, or `ADMIN OPTION` as reachable/escalation-relevant; an `ADMIN OPTION` path is a blocker even if that principal cannot currently `SET ROLE` to the target.

Required assertions: production capability roles and test harnesses have no unapproved direct or transitive path to SUPERUSER, BYPASSRLS, protected schema/object owner, migration owner, SECURITY DEFINER owner, or other protected role; no unapproved membership grants `SET`, `INHERIT`, or `ADMIN OPTION`; no negative-test principal has any application/worker/owner membership; and every exception is named in a human-approved role matrix. Direct grants and effective privileges must also be checked because membership closure alone is not a complete ACL audit.

The inventory includes all object kinds in relevant non-system schemas (`pg_class` covers ordinary/partitioned tables, sequences, views, materialized views, foreign tables and other relation kinds); all `pg_proc` routines including functions and procedures; `pg_type` types/domains; `pg_extension` owners; schema owners; and the additional global/namespace-owned object categories shown below. Exclude only internal objects in `pg_catalog`, `information_schema`, `pg_toast*`, and temporary schemas from the application-object ownership scan. These are PostgreSQL-managed catalog/metadata objects, internal TOAST storage (whose owning application relation is inventoried), or ephemeral per-session schemas; they are not app-owned grant targets, and runtime roles must not create objects on a trusted definer `search_path`. Include Supabase and extension schemas such as `auth`, `storage`, `realtime`, and `extensions` if present or used. Database and tablespace owners, extension owners, elevated built-in roles and any human-identified migration owners are inventoried separately even when their objects are outside application schemas. Catalog objects without independent owner fields (for example cast/constraint/trigger metadata) are covered through the owning type, routine, or relation and their effective ACLs; verify that mapping in the implementation inventory. Record exclusions and their reason; do not treat an omitted or unknown category as clean.

The following PostgreSQL 17 catalog query is an example of the required cycle-safe upward traversal and protected-owner inventory. It is a proposed read-only query and was not executed. Extend the explicit protected-role inventory with every human-identified migration owner and other privileged built-in/custom role before using it; the catalog cannot infer every role's business purpose.

```sql
WITH RECURSIVE protected_roles(role_oid, reason) AS (
    SELECT oid, CASE
        WHEN rolsuper THEN 'SUPERUSER'
        ELSE 'BYPASSRLS'
    END
    FROM pg_catalog.pg_roles
    WHERE rolsuper OR rolbypassrls
    UNION
    SELECT n.nspowner, 'schema owner: ' || n.nspname
    FROM pg_catalog.pg_namespace AS n
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT c.relowner, 'protected relation owner: ' || n.nspname || '.' || c.relname
    FROM pg_catalog.pg_class AS c
    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT p.proowner,
           CASE WHEN p.prosecdef THEN 'SECURITY DEFINER owner: '
                ELSE 'routine owner: ' END || p.oid::regprocedure::text
    FROM pg_catalog.pg_proc AS p
    JOIN pg_catalog.pg_namespace AS n ON n.oid = p.pronamespace
    WHERE p.prosecdef
       OR (n.nspname NOT IN ('pg_catalog', 'information_schema')
           AND n.nspname NOT LIKE 'pg_toast%'
           AND n.nspname NOT LIKE 'pg_temp%')
    UNION
    SELECT t.typowner, 'protected type/domain owner: ' || n.nspname || '.' || t.typname
    FROM pg_catalog.pg_type AS t
    JOIN pg_catalog.pg_namespace AS n ON n.oid = t.typnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT e.extowner, 'extension owner: ' || e.extname
    FROM pg_catalog.pg_extension AS e
    UNION
    SELECT col.collowner, 'collation owner: ' || n.nspname || '.' || col.collname
    FROM pg_catalog.pg_collation AS col
    JOIN pg_catalog.pg_namespace AS n ON n.oid = col.collnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT op.oprowner, 'operator owner: ' || n.nspname || '.' || op.oprname
    FROM pg_catalog.pg_operator AS op
    JOIN pg_catalog.pg_namespace AS n ON n.oid = op.oprnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT opc.opcowner, 'operator class owner: ' || n.nspname || '.' || opc.opcname
    FROM pg_catalog.pg_opclass AS opc
    JOIN pg_catalog.pg_namespace AS n ON n.oid = opc.opcnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT opf.opfowner, 'operator family owner: ' || n.nspname || '.' || opf.opfname
    FROM pg_catalog.pg_opfamily AS opf
    JOIN pg_catalog.pg_namespace AS n ON n.oid = opf.opfnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT conv.conowner, 'conversion owner: ' || n.nspname || '.' || conv.conname
    FROM pg_catalog.pg_conversion AS conv
    JOIN pg_catalog.pg_namespace AS n ON n.oid = conv.connamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT evt.evtowner, 'event trigger owner: ' || evt.evtname
    FROM pg_catalog.pg_event_trigger AS evt
    UNION
    SELECT lom.lomowner, 'large object owner: ' || lom.oid::text
    FROM pg_catalog.pg_largeobject_metadata AS lom
    UNION
    SELECT d.defaclrole, 'default ACL owner'
    FROM pg_catalog.pg_default_acl AS d
    UNION
    SELECT fdw.fdwowner, 'foreign-data wrapper owner: ' || fdw.fdwname
    FROM pg_catalog.pg_foreign_data_wrapper AS fdw
    UNION
    SELECT srv.srvowner, 'foreign server owner: ' || srv.srvname
    FROM pg_catalog.pg_foreign_server AS srv
    UNION
    SELECT lang.lanowner, 'procedural language owner: ' || lang.lanname
    FROM pg_catalog.pg_language AS lang
    WHERE lang.lanowner IS NOT NULL
    UNION
    SELECT cfg.cfgowner, 'text-search configuration owner: ' || n.nspname || '.' || cfg.cfgname
    FROM pg_catalog.pg_ts_config AS cfg
    JOIN pg_catalog.pg_namespace AS n ON n.oid = cfg.cfgnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT dict.dictowner, 'text-search dictionary owner: ' || n.nspname || '.' || dict.dictname
    FROM pg_catalog.pg_ts_dict AS dict
    JOIN pg_catalog.pg_namespace AS n ON n.oid = dict.dictnamespace
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'
    UNION
    SELECT pub.pubowner, 'publication owner: ' || pub.pubname
    FROM pg_catalog.pg_publication AS pub
    UNION
    SELECT sub.subowner, 'subscription owner: ' || sub.subname
    FROM pg_catalog.pg_subscription AS sub
    UNION
    SELECT db.datdba, 'database owner: ' || db.datname
    FROM pg_catalog.pg_database AS db
    WHERE db.datname = current_database()
    UNION
    SELECT ts.spcowner, 'tablespace owner: ' || ts.spcname
    FROM pg_catalog.pg_tablespace AS ts
),
membership_paths(start_oid, reached_oid, role_path, set_edges,
                 inherit_edges, admin_edges) AS (
    SELECT m.member, m.roleid,
           ARRAY[m.member, m.roleid]::oid[],
           ARRAY[m.set_option]::boolean[],
           ARRAY[m.inherit_option]::boolean[],
           ARRAY[m.admin_option]::boolean[]
    FROM pg_catalog.pg_auth_members AS m
    UNION ALL
    SELECT path.start_oid, m.roleid,
           path.role_path || m.roleid,
           path.set_edges || m.set_option,
           path.inherit_edges || m.inherit_option,
           path.admin_edges || m.admin_option
    FROM membership_paths AS path
    JOIN pg_catalog.pg_auth_members AS m ON m.member = path.reached_oid
    WHERE NOT m.roleid = ANY(path.role_path)
)
SELECT start_role.rolname AS member_role,
       reached_role.rolname AS protected_role,
       ARRAY(
           SELECT path_role.rolname
           FROM unnest(path.role_path) WITH ORDINALITY AS edge(role_oid, ord)
           JOIN pg_catalog.pg_roles AS path_role ON path_role.oid = edge.role_oid
           ORDER BY edge.ord
       ) AS role_path,
       path.set_edges,
       path.inherit_edges,
       path.admin_edges,
       protected.reason
FROM membership_paths AS path
JOIN protected_roles AS protected ON protected.role_oid = path.reached_oid
JOIN pg_catalog.pg_roles AS start_role ON start_role.oid = path.start_oid
JOIN pg_catalog.pg_roles AS reached_role ON reached_role.oid = path.reached_oid
ORDER BY member_role, protected_role, role_path;
```

### Required-principal inventory and fail-closed assertions

Before any Gate 5 test, produce an approved expected-principal roster and reconcile it to `pg_roles` by exact role name and OID. Do not silently skip a role because it is absent or because its name differs. At minimum the roster must enumerate:

| Principal class | Required inventory |
|---|---|
| Runtime | `college_app_user` and every other intended web/API runtime role; record the approved `NOLOGIN` capability role and all expected attributes. |
| Worker | Every per-tenant/trust-cohort NOLOGIN worker capability role, plus each separate authenticated connection login mapped to a pool. If worker execution is disabled, record that explicitly and require no worker principal/claim function to be enabled. |
| Test harness | Every disposable harness login and its single permitted SET-only target role; verify it is not also a runtime, owner, migration, or negative-test principal. |
| Independent negative test | The separate unprivileged login; verify no application, worker, harness, migration, or SECURITY DEFINER owner membership. |

For every required principal, fail validation if it is missing, duplicated/ambiguous, unexpectedly LOGIN-capable, owner of any protected object, SUPERUSER, BYPASSRLS, has unexpected `CREATEROLE`/`CREATEDB`/replication attributes, or has any unreviewed direct/transitive membership or privilege path. Verify all direct and transitive membership edges and paths with PostgreSQL 17 `set_option`, `inherit_option`, and `admin_option`; check effective `SET`/inheritance with `pg_has_role`; enumerate all object ownership categories above; evaluate effective database, schema USAGE/CREATE, table, column, sequence, and function privileges with the corresponding `has_*_privilege` helpers. Include every relevant schema, not just `public`.

An absent principal, missing owner category, incomplete object inventory, unknown login role, unexamined membership edge/path, unclassified effective grant, or failed catalog/privilege query is **BLOCKED / NOT VALIDATED**, never a passing or clean result. A reviewer must resolve the inventory gap before security tests count toward Gate 5.

The test harness must reproduce only the approved production capability role's effective ACL/RLS view via SET-only membership, while its own login remains unprivileged. The harness receives no independent data/function privilege beyond connection and the approved `SET ROLE` path. Before running a positive test, assert harness privileges alone cannot invoke protected functions or access fixtures; after switching, assert the intended runtime role and signed identity separately. Any identity mismatch, unexpected membership path, unexpected privilege, or row visible only because of the harness login is a test failure—not an acceptable fallback.

### Disposable unprivileged negative-test principal

The security matrix also requires a distinct disposable login principal, for example `college_app_negative_test`, in the separately approved synthetic environment. It must be non-superuser, `NOBYPASSRLS`, non-owner, non-CREATEROLE, have no direct or transitive membership in application, worker, migration, or SECURITY DEFINER owner roles, no unintended schema `CREATE`, and no direct `EXECUTE` on protected functions. Do not grant it `SET ROLE` to any application role.

For a meaningful RLS negative test, grant only the minimum table privilege needed on specifically approved synthetic fixture tables (not broad production-like privileges); the table remains RLS-protected and contains only synthetic A/B tenant rows. Separately verify that no grants means protected function calls and ungranted table operations fail at ACL evaluation. A denial caused by missing privilege must not be misreported as proof that an RLS predicate worked.

Using only Supabase `anon` does not establish this boundary: it is a named platform role with its own grants, policy targets, and possible default-privilege behavior, not a generic unprivileged database login, and it does not exercise arbitrary login-role membership or ownership mistakes. Both the actual `anon` contract and this separate negative principal require tests.

No harness role, runtime role, grant, or credential was created or changed for this plan.

## 6. Corrected SECURITY DEFINER ACL verification plan

`pg_proc.proacl IS NULL` is **not** evidence that PUBLIC EXECUTE is revoked. For a function with a NULL ACL, PostgreSQL's default function ACL normally includes PUBLIC EXECUTE. Verification must combine the stored ACL (including `acldefault` when NULL), owner-specific default ACLs, effective privilege helpers, role membership, schema ACLs, owner properties, function configuration, and actual function behavior under the controlled test role.

### Required checks for every SECURITY DEFINER function

1. Inventory every routine with `prosecdef = true`; include overload/signature, schema, owner, language, `proconfig`, and any nested security-definer calls.
2. Expand `COALESCE(proacl, acldefault('f', proowner))` and assert there is no EXECUTE grantee OID 0 (PUBLIC). Compare explicit grants to an approved per-function allowlist; no grant option, wildcard role, `PUBLIC`, `anon`, `authenticated`, web role, or worker role unless that exact function requires it.
3. Separately evaluate `has_function_privilege(role_oid, function_oid, 'EXECUTE')` for every relevant role to capture inherited and PUBLIC effective access. A direct ACL list alone misses membership-derived access.
4. Inspect `pg_default_acl` for every function-creating owner and schema; remove broad default function EXECUTE. Existing `proacl` and effective checks remain authoritative for functions already created.
5. Verify the owner is the explicitly approved NOLOGIN role, not a table owner, not SUPERUSER, not BYPASSRLS, and not a member/SET ROLE target accessible from any runtime/harness role. Check its effective SELECT/INSERT/UPDATE/DELETE rights on all application tables, including unrelated tenant tables.
6. Verify schema USAGE/CREATE ACLs for `public`, `auth_private`, and any extension schema. Runtime roles must not CREATE objects in schemas on a definer function's path.
7. Verify `proconfig` fixes `search_path` to `pg_catalog`; fully qualify every non-catalog object in the function body. Reject mutable caller-controlled search paths and any untrusted schema in a definer path.
8. Review nested calls. A SECURITY DEFINER routine invoking another SECURITY DEFINER routine transfers execution to the nested owner; inspect that owner's ACLs and table rights too. Static dependency catalogs may omit references inside PL/pgSQL or dynamic SQL, so source/definition review plus targeted tests is required. Dynamic SQL must be absent or safely schema-qualified and parameterized.
9. Verify RLS behavior using known fixtures: function owners must not own protected tables or bypass RLS; their role-targeted policies and object grants must be limited to their function's contract. A routine must not read or write another tenant's rows unless the approved Super Admin workflow explicitly requires it.
10. Test invocation by each permitted role and denied roles, including PUBLIC-equivalent access, `anon`, `authenticated`, web role, other-tenant worker role, and attempts to SET ROLE to a function owner. Test output for unintended data disclosure as well as writes.

### Proposed read-only catalog query shapes (not executed)

The following queries are examples for the future approved local environment. They were not run. Review any function definition locally for embedded sensitive literals before displaying it; never inspect or print the private key table's values.

```sql
-- Stored/default ACL entries for SECURITY DEFINER functions.
-- PUBLIC is grantee OID 0; a NULL proacl is expanded to PostgreSQL's default.
SELECT p.oid::regprocedure AS function_name,
       owner.rolname AS function_owner,
       CASE WHEN acl.grantee = 0 THEN 'PUBLIC' ELSE grantee.rolname::text END AS grantee_name,
       acl.grantor::regrole AS grantor,
       acl.privilege_type,
       acl.is_grantable,
       p.proconfig
FROM pg_catalog.pg_proc AS p
JOIN pg_catalog.pg_roles AS owner ON owner.oid = p.proowner
CROSS JOIN LATERAL pg_catalog.aclexplode(
    COALESCE(p.proacl, pg_catalog.acldefault('f', p.proowner))
) AS acl
LEFT JOIN pg_catalog.pg_roles AS grantee ON grantee.oid = acl.grantee
WHERE p.prosecdef
ORDER BY p.oid::regprocedure::text, grantee_name;

-- Effective EXECUTE for every role, including membership and PUBLIC effects.
SELECT p.oid::regprocedure AS function_name,
       r.rolname,
       pg_catalog.has_function_privilege(r.oid, p.oid, 'EXECUTE') AS can_execute
FROM pg_catalog.pg_proc AS p
CROSS JOIN pg_catalog.pg_roles AS r
WHERE p.prosecdef
ORDER BY p.oid::regprocedure::text, r.rolname;

-- Function-owner attributes and effective rights on application relations.
SELECT p.oid::regprocedure AS function_name,
       owner.rolname AS owner,
       owner.rolcanlogin, owner.rolsuper, owner.rolbypassrls,
       n.nspname AS table_schema, c.relname AS table_name,
       (c.relowner = owner.oid) AS owns_table,
       pg_catalog.has_table_privilege(owner.oid, c.oid, 'SELECT') AS can_select,
       pg_catalog.has_table_privilege(owner.oid, c.oid, 'INSERT') AS can_insert,
       pg_catalog.has_table_privilege(owner.oid, c.oid, 'UPDATE') AS can_update,
       pg_catalog.has_table_privilege(owner.oid, c.oid, 'DELETE') AS can_delete
FROM pg_catalog.pg_proc AS p
JOIN pg_catalog.pg_roles AS owner ON owner.oid = p.proowner
CROSS JOIN pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE p.prosecdef AND n.nspname = 'public' AND c.relkind IN ('r', 'p')
ORDER BY p.oid::regprocedure::text, c.relname;

-- Owner-specific default ACLs for functions.
SELECT owner.rolname AS object_owner,
       COALESCE(schema_ns.nspname, '<global>') AS schema_name,
       d.defaclobjtype,
       acl.grantee,
       acl.privilege_type,
       acl.is_grantable
FROM pg_catalog.pg_default_acl AS d
JOIN pg_catalog.pg_roles AS owner ON owner.oid = d.defaclrole
LEFT JOIN pg_catalog.pg_namespace AS schema_ns ON schema_ns.oid = d.defaclnamespace
CROSS JOIN LATERAL pg_catalog.aclexplode(d.defaclacl) AS acl
WHERE d.defaclobjtype = 'f'
ORDER BY owner.rolname, schema_name, acl.grantee;
```

In addition, inspect schema ACLs with `aclexplode(COALESCE(nspacl, acldefault('n', nspowner)))`, effective `has_schema_privilege`, and role membership closure (including whether a runtime role can `SET` to an owner). Catalog output is necessary but not sufficient: the test suite must prove that a definer function cannot access unrelated tenant fixtures and that nested calls do not expand authority.

## 7. Corrected worker isolation and job authorization plan

A job UUID is an identifier, **not** proof of authorization. Authorization must come from the authenticated worker principal/pool, a database-validated job/resource binding, an active lease, and a purpose-bound signed context. Running outside the web process does not make a worker trusted.

### Required job lifecycle

The new claim and context subparagraphs below elaborate on lifecycle steps 4–5; the numbered lease/retry/recovery steps then continue the lifecycle.

1. **Create and publish:** An authenticated request validates the user's current membership and the requested resource's tenant. In one transaction it creates a job with fixed job kind, tenant derived from the resource, exact resource key(s), bounded parameters, attempt/deadline state, and an idempotency key with a uniqueness constraint. Store an outbox event in the same transaction. The web role cannot update job tenant/resource after creation and cannot create arbitrary worker leases.
2. **Publish:** A narrowly privileged outbox dispatcher publishes only the generated job ID and version/queue routing metadata; it sends no caller-chosen tenant/resource authority or sensitive prompt/token. Publish is retried until acknowledged, then the outbox state is updated idempotently. Broker ACLs/TLS and publisher/consumer separation are defense in depth, not the database authorization check.
3. **Associate resources:** Use foreign keys and database-side checks to bind a job to a resource that exists and belongs to the derived tenant. For multiple resources, use a normalized job-resource table with constraints; do not accept arbitrary tenant/resource lists from the worker. Recheck the binding at claim and for each protected operation.
4. **Allowed claimant and pool authentication:** Only a separately approved, per-tenant or small-trust-cohort worker connection principal may reach the claim API. The proposed trust anchor is the PostgreSQL-authenticated connection principal (`session_user`) mapped in a protected database allowlist to one worker-pool ID, then a SET-only membership into that pool's NOLOGIN capability role for narrow SQL grants. The database credential must be provisioned through a separately approved protected identity/secret mechanism; the exact mechanism remains a human decision. PostgreSQL enforces the function EXECUTE ACL against the caller's effective role before entering the function; inside SECURITY DEFINER, the function must not mistake `current_user` (now its owner) for the caller. It validates the authenticated `session_user` mapping. A caller-supplied worker name, tenant ID, job UUID, `current_setting()` value, or unsigned GUC is only input—not proof. If a signed external identity is selected instead of the database-principal mapping, the database must verify its signature, issuer, audience, key ID, expiry, and pool binding; an HTTP claim is never accepted directly.
5. **Claim-function boundary:** The only callers are the exact worker capability role(s) listed in a reviewed per-function EXECUTE allowlist; revoke EXECUTE from PUBLIC, `anon`, `authenticated`, web roles, and unrelated worker pools. The proposed function is `SECURITY DEFINER` owned by a dedicated NOLOGIN, non-owner, non-SUPERUSER, non-BYPASSRLS role with fixed `search_path = pg_catalog`, fully qualified object references, and only the job/lease table privileges needed for claim. Its owner, schema USAGE, table ACLs, RLS policy, nested calls, and owner role-membership paths are explicit human approval decisions; `SECURITY DEFINER` is not proof of safety. Internally it derives pool identity from the authenticated principal mapping, locks the job, and validates job kind against the pool allowlist, queued/retryable state, attempt limit, cancellation/deadline, idempotency, exact resource foreign keys, resource tenant equals job tenant, and no active unexpired lease. Claiming a job UUID does not bypass any check.
**Lease and scoped context issuance after claim:** In the same atomic claim operation, generate a cryptographically random lease capability, store only its hash, bind it to job ID, exact resource set, tenant, worker-pool ID, attempt number, and expiry, then transition the job to running. Return only the opaque lease capability and minimal job descriptor. After claim, a restricted context-authorization function revalidates that active lease and authenticated pool on each new transaction, and installs the signed, purpose-bound, transaction-local WORKER context internally; the HMAC key is never returned. The signed claims include pool, job, resource IDs, tenant, lease digest, attempt, request ID, transaction ID, and short issue/expiry bounds. If the context signer is separate rather than a database function, it must independently verify a successful active claim before signing; this choice requires explicit design approval.

**Authorize each database transaction:** Each protected transaction rechecks the context signature, purpose, key/pool binding, transaction ID and expiry, active lease/token hash, job status/attempt/deadline, and live resource-to-tenant relationship. Worker-supplied tenant/resource values are compared to database-derived values, never trusted as authority. A tenant GUC, worker name, UUID, or unsigned GUC alone grants nothing.
6. **Lease and heartbeat:** Use the database clock. Proposed defaults remain a five-minute lease, heartbeat every 60 seconds, and a one-hour absolute task limit; the lease cannot extend beyond the job deadline. Heartbeat requires the same authenticated pool and active lease capability, and atomically records renewal. Expired/revoked/completed leases immediately invalidate the context. Long jobs split DB work into bounded transactions and receive a newly verified context for each transaction.
7. **Retry and duplicate delivery:** Assume at-least-once queue delivery. Enforce a unique idempotency key for each job and step/effect; use unique constraints/upserts for DB work and an outbox/idempotency key for external side effects. Duplicate delivery of a running/completed job is a no-op or denied; stale claim tokens cannot renew or complete a later attempt. A retry gets a new attempt number and lease capability.
8. **Crash recovery:** A sweeper/claim function detects expired leases using DB time, records the failed attempt, and requeues only if retry policy permits; otherwise it moves the job to a terminal/dead-letter state. Partial effects must be transactionally atomic or idempotent. Do not clear job/audit history to make retries pass.
9. **Cross-tenant isolation:** Worker RLS policies require an active verified WORKER context, current tenant-bound pool, job and resource IDs, and a live lease. The database rechecks that resource tenant still equals the job tenant. Tests must prove both the protected fixture exists and the worker cannot reach another tenant's job/resource.
10. **Audit:** Record job creation with the verified initiating actor and tenant; record claim, heartbeat, retry, completion, cancellation and failure using DB-derived worker/job/resource identifiers. Do not accept caller-selected actor/tenant, lease secret, signature, prompt, or raw provider/error content in audit payloads.
11. **Compromised worker:** Give each tenant (or explicitly approved small trust cohort) a separate queue, runtime principal, signing key and secret scope; grant only that cohort's job functions and resource operations. Exclude job creation, account/admin changes, audit mutation, key-table access, and BYPASSRLS. Use short leases, broker ACLs, network/egress controls, secret rotation and per-job auditing. A compromised worker can still read/modify data required for jobs in its isolation pool and may abuse active leases; this cannot be eliminated by queue separation.

### Architecture options

### Claim/context function privilege contracts requiring human review

These are privilege boundaries, not existing database objects. Actual function signatures, schema/table names, and role names must be fixed only after the selected migration branch and schema inventory; do not assume these proposed objects already exist.

- **Claim function owner:** A dedicated NOLOGIN, non-SUPERUSER, non-BYPASSRLS role that owns no application tables and has no unapproved membership/SET path. Its only direct data access should be `SELECT`/`UPDATE` on eligible job rows, `SELECT`/`INSERT` on lease rows, and `SELECT` on the exact resource/tenant-binding rows needed to validate a claim. It must not read signing keys, arbitrary user data, prompts, or unrelated tenant data, and must not write general audit rows directly.
- **Claim function execution:** PostgreSQL enforces EXECUTE against the caller's effective role before entering the SECURITY DEFINER body. Grant EXECUTE only to the per-pool NOLOGIN worker capability role(s); the authenticated connection principal can use only the separately approved SET-only path. Revoke PUBLIC, `anon`, `authenticated`, web-role, unrelated-worker, and maintenance-role access unless a separately reviewed function contract explicitly needs it. The function itself validates the unchanged `session_user` mapping to the pool. Do not try to infer the invoker from `current_user` inside the definer body.
- **Context issuer:** Prefer a separate SECURITY DEFINER owner for context issuance, also NOLOGIN/non-owner/non-bypass, with only `SELECT` on the active job/lease/resource binding and the protected signing-key row for the mapped pool. It rechecks successful claim, active lease, pool, tenant, exact resources, attempt, request, xid, and expiry; signs and installs the transaction-local context internally; never returns the key. It may return the signed, transaction-bound context envelope to the worker only after that validation. The envelope is not reusable in another transaction; a new transaction must revalidate the lease and obtain a new envelope. If the context signer remains in a trusted worker service instead, key custody, claim confirmation, and signing authorization require separate human approval.
- **Other operations:** Heartbeat/completion/retry and expiry-sweeper functions need separate command-specific EXECUTE grants and minimal row privileges; do not bundle them into a general maintenance function or grant workers maintenance access. Any audit write must use a constrained event function/trigger with DB-derived identifiers, not broad audit-table INSERT.
- **Common requirements:** For every SECURITY DEFINER function specify the exact owner, schema USAGE, table/column grants, RLS policies, nested call graph, PUBLIC revoke, explicit EXECUTE grantees, fixed `search_path`, and owner membership closure. The claim owner, context issuer owner/key access, and exact grants remain human approval decisions.

| Option | Benefits | Risks and residual blast radius |
|---|---|---|
| One shared trusted worker/pool for all colleges | Simpler operations, one queue/deployment, easier upgrades. Per-job lease and RLS still constrain each transaction. | A compromised worker process/key or overly broad worker principal can claim all tenants' jobs and potentially read or alter every job resource in the shared pool. Job UUID alone cannot prevent that. Broker ACLs do not contain a worker that already has the shared credential. |
| Separate tenant-isolated workers/pools | Per-tenant queue, principal, signing key and DB function scope limits compromise to one tenant/pool; independent rate limits and revocation. | More deployment/secret/queue complexity; a misrouted job or shared secret can undo isolation. Each worker can still damage its assigned tenant's resources. |

**Recommendation for human approval:** use tenant-isolated workers (or small, explicitly approved trust cohorts if per-tenant deployment is infeasible), with per-pool principal/key and database-enforced tenant/job binding. Do not use a single shared key across all tenants as the default. If a shared worker is selected, record acceptance that compromise of that service may expose all jobs in its scope and require a separately approved compensating design. This recommendation does not silently resolve the existing human decision.

## 8. Updated migration-history decision tree

Do not select a branch from this report alone.

### Branch A — formally confirmed unreleased and unapplied everywhere

Only if an accountable owner confirms in writing that migrations 001–022 have never been applied, deployed, or released anywhere:

1. Make reviewed in-place corrections to 017, 018, 019, 021, and 022.
2. Keep the chain in numeric order and preserve its dependency edges.
3. Keep the runtime role `NOLOGIN` through migration and security validation.
4. Validate only on a separately approved, disposable Supabase-compatible local stack.
5. Do not enable a login, add credentials, or connect the application until the later authorization gate.

### Branch B — any application/release, partial application, or uncertain history

If any migration has been applied/released, or if history cannot be positively established:

1. Do not rewrite any numbered historical migration.
2. First obtain an approved, non-production inventory of migration state and live schema versions; record every environment separately. No production connection is authorized by this plan.
3. Build a forward-only corrective migration after the confirmed latest schema version. `023_phase3a44_rls_context_privileges.sql` is the proposed filename **only if** 022 is confirmed as the latest applied migration; otherwise choose the next unused version after inventory. Do not assume 022 is applied or invent a migration ledger.
4. Split non-additive changes into expand/backfill/validate/contract steps where required. Preserve compatibility during application rollout, especially for the context format, user token columns, and function return shapes.
5. Plan a maintenance window with all API, worker, pooler, and PostgREST clients disconnected while signed-context/RLS changes are switched. Do not retain an insecure v1 authorization path as an undocumented compatibility fallback.
6. Require a reviewed backup/restore point before any data transformation or destructive contract step.

**Human branch choice is required.** Any unresolved or partial migration history defaults to Branch B, not to in-place edits.

## 9. Updated implementation sequence and file-by-file plan

The order below is a dependency order for a future, explicitly approved implementation. New functions mentioned here are proposed design elements from Steps 3/3.1, not existing repository symbols unless identified as existing.

### 9.1 Migration and documentation files

### Future implementation order

This is a proposed sequence, not authorization:

1. Resolve the Section 10 decisions and select Branch A or B from documented migration history. Branch B remains mandatory for any applied, released, partial, or uncertain history.
2. Freeze the exact migration and backend contracts, especially context version/purpose, role grants, visitor expiry, auth lookup fields, job/lease schema, and function ownership. Review all dependent callers before changing interfaces.
3. Implement and review the database changes as an isolated, fail-closed migration sequence. Use corrected 021 preflight and in-transaction assertions before its internal `COMMIT`; run 022 only after 021 commits successfully. Do not connect application clients during the security cutover.
4. Implement backend identity boundaries, least-privilege ORM projections, job/lease flow, constrained audit/telemetry/notification writes, and compatible auth/onboarding routes. Keep runtime roles `NOLOGIN`.
5. In the approved disposable Supabase-compatible stack, run the focused application tests and the actual PostgreSQL security matrix through the dedicated harness plus controlled `SET ROLE`. Reconcile every catalog result and test failure before proceeding.
6. Only after Gate 5 and separate human approval, plan any runtime-login provisioning and coordinated deployment. Do not use this sequence as a production rollout authorization.

| Exact path | Existing behavior and issue | Proposed change and dependency/order | Regression risk, required verification, rollback |
|---|---|---|---|
| `database/migrations/017_row_level_security_policies.sql` | Installs policies that call Supabase `auth.uid()` for tickets, replies, notifications, and feedback. Includes `FOR ALL` rules and a published-chunk NULL-tenant branch. Backend identity is custom JWT plus signed application context, not Supabase Auth identity. | Branch A: defer user-dependent policies until verified helper functions exist; remove all `auth.uid()` dependencies; keep only reviewed non-final/default-deny policy state. Do not leave broad chunk access. Final operation-specific policies are installed after the signed helpers in 021. Branch B: preserve this file and implement equivalent changes forward-only. | Existing routes may fail closed until the final migration; that is intentional while the app is disconnected. Verify zero `auth.uid()` application-policy dependencies and no accidental `USING (true)`/NULL-tenant escape. A disposable per-migration transaction can roll back this file; deployed history requires a forward correction, not file rollback. |
| `database/migrations/018_create_application_role.sql` | Creates `college_app_user LOGIN` with a known placeholder password, grants broad table/sequence/function privileges and broad default privileges, and grants CONNECT to database `postgres`. | Create/validate `college_app_user` as `NOLOGIN`, no password, `NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS NOREPLICATION`; grant CONNECT to the actual migration database and only reviewed object/column/function privileges. Remove broad defaults and table-wide grants. Keep it NOLOGIN until the post-validation approval gate; credential provisioning is a separate protected operation, never migration SQL. Add an independently approved worker principal only if the worker decision selects one. | Missing grants can break ORM paths; excess grants defeat the plan. Verify role attributes, membership/ownership paths, object privileges, and defaults. Roll back only on an isolated unshared database; for an applied history use a reviewed forward revoke/grant correction. Never set or print credentials here. |
| `database/migrations/019_complete_rls_policies.sql` | Adds unsigned `current_app_user_id()` and intermediate broad user/membership policies (`USING (true)`, `WITH CHECK (true)`); several permissive policies combine by OR. | Remove/defer unsigned identity policies and broad interim access. Prefer default-deny until signed-context policies are installed; do not rely on adding a narrow permissive policy to constrain a broad one. Ensure every replaced legacy policy is explicitly dropped in the final migration. Branch B uses forward-only replacements. | A policy omitted from `DROP POLICY` can preserve access. Verify `pg_policies` inventory and effective positive/negative RLS results. In an isolated migration transaction rollback is possible before commit; deployed policy history is repaired forward-only. |
| `database/migrations/020_revoke_anon_grants.sql` | Unconditionally revokes from Supabase `anon` and `authenticated`; those roles are not created by this repository. | Keep every REVOKE; do not skip it or add fake roles. Run only on a verified Supabase-compatible local stack where official bootstrap supplies the roles. Audit effective ACL/default privileges after execution. | Vanilla PostgreSQL fails at a missing role; abort before DDL on an incompatible target. In a per-file transaction rollback is available before commit. No shim result may be represented as Supabase validation. |
| `database/migrations/021_phase3a42_security_onboarding.sql` | Contains the first signed-context functions, invitation-token hash conversion, visitor-token hash, registration/invitation functions, and selected policy replacement. It has its own transaction and destructive drops of invitation plaintext and initial-admin password hash. Five 017 `auth.uid()` policies and some other permissive policies are not replaced. SECURITY DEFINER ownership depends on migration executor; search paths include non-system schemas. | Branch A: install helpers before dependent policies; implement signed context v2 with request ID, key ID/purpose, PostgreSQL transaction ID and <=300-second lifetime; bind visitor digest and absolute 24-hour expiry; create job/lease functions and worker-specific policy only after the worker decision; replace all affected final policies and explicitly drop legacy permissive names; add final college/user/audit/telemetry/notification write boundaries; assign explicit NOLOGIN owners, fixed `pg_catalog` path plus qualified references, PUBLIC revocation and exact EXECUTE grants. Preserve the existing seven-field auth lookup contract. Branch B moves equivalent work into the approved forward migration after schema inventory. | Highest regression/data risk. Before starting, perform the Section 4 preflights: target/predecessor/prerequisite checks, client disconnection, snapshot approval, count-only token/hash checks, and caller-dependency review. Within the migration transaction, assert token backfill correctness, count preservation, uniqueness, safe handling of non-NULL initial-admin hashes, guest expiry/hash invariants, final RLS/policy state, and function owner/path/ACL state before the existing `COMMIT`. Any failed assertion must abort and roll back all 021 changes; there is no pause after execution but before its internal commit. After a successful commit, dropped values require an approved restore/rebuild or forward repair; an inverse SQL migration cannot recover them. |
| `database/migrations/022_minimize_auth_lookup.sql` | Explicit transaction drops/recreates `lookup_user_by_email_for_auth(text)` with seven returned columns and preserves the existing owner; that owner may be privileged. | Keep the seven-column result. Assign a specific non-login least-privilege owner and exact column SELECT plus role-targeted RLS behavior. Revoke PUBLIC, grant only the backend runtime function EXECUTE, and do not use CASCADE. Update backend projections/functions together. Branch B preserves this file and adds the correction forward-only. | Login can fail if owner/grants/result mapping change. Verify exact result shape, ownership, path, privileges, and local password verification; API responses/logs must not expose the hash. Transaction rollback before COMMIT; after deployment use a forward replacement and compatibility plan. |
| `database/README.md` | Tells operators to paste SQL into a Supabase cloud SQL Editor or connect to a hosted project, describes a historical 001–011 workflow, and suggests seed loading. This is not a migration ledger. | Replace unsafe/obsolete manual cloud execution guidance with the controlled environment, branch selection, per-file transaction, fail-fast, role-offline, backup, verification and explicit approval process. Clarify that documentation does not prove execution and that `scripts/migrate_and_seed.py` is not part of this security validation. | Documentation mismatch could lead to uncontrolled production application. Review links/commands and ensure no instruction implies this plan authorizes production work. Revert docs if inaccurate; no database rollback applies. |

### 9.2 Backend files

| Exact path | Existing behavior and relevant call site | Proposed change and dependency/order | Regression risk, required tests, rollback |
|---|---|---|---|
| `backend/app/database/session.py` | `set_rls_context()` signs v1 user/tenant/admin/verification/expiry fields; `set_chat_visitor_token()` separately sets a raw GUC; `tenant_session()` accepts tenant/user/admin inputs and is used by worker and request flows. | After identity, worker and lease decisions: implement atomic context v2 signing with request ID, xid, purpose, issue/expiry, key ID and visitor digest; separate USER/VISITOR/WORKER/PUBLIC_TICKET setters with guards; disallow web code from minting WORKER; ensure every new transaction signs again. Preserve pool reset behavior. | Every RLS-protected route/task can fail closed if context is missing or stale. Test commits, rollback, nested service behavior, pool reuse, GUC forgery and cross-transaction replay. Roll back backend release before schema cutover only; coordinated rollback after a new verifier requires a reviewed forward-compatible DB plan. |
| `backend/app/database/connection.py` | Shared async engine/session behavior and pool cleanup; current app/task connection setup does not establish separate worker SQL identity. | Keep transaction-local cleanup; after worker decision, add separately configured worker connection/principal only if approved. Do not load worker credentials/key in web process. | Connection lifecycle errors can leak/reset context or break background work. Test pool checkout/check-in and worker/web identity separation. Revert app connection configuration before enabling worker role; do not restore weaker database grants. |
| `backend/app/core/config.py` | Current app configuration supports the shared context/auth/database setup; no verified independent worker signer/credential boundary is established by current code. | Add validated configuration fields for separately protected worker signer/DB identity and key IDs only if approved; validate missing/invalid settings fail closed. Never place values in source or this report. | Misconfiguration can make worker claims impossible or accidentally expose signer to API. Configuration unit tests and deployment manifest review required; revert config before provisioning credentials. |
| `backend/app/dependencies/auth.py` | Resolves custom JWT user and sets signed USER context; optional-user path does not create an anonymous capability. | Preserve verified user-only identity; do not accept role/tenant claims as proof beyond current database checks. Set only USER context; anonymous endpoint handlers select a distinct, limited purpose. | Login/session hydration regressions. Run auth, role and forged-claim tests; revert app code before RLS cutover if necessary. |
| `backend/app/dependencies/tenant.py` | Tenant access path currently sets `app.current_college_id` directly after membership validation, invalidating a signed context once policies require its HMAC. | Replace raw `set_config` with the signed setter only after the membership check. Re-sign after each new transaction. | Tenant routes may return empty/denied if context timing is wrong. Test AIT/RCTI membership and no-tenant behavior. Roll back app release only while old DB policy is still approved; never weaken final RLS to accommodate stale code. |
| `backend/app/api/v1/college_admin.py` | `get_authorized_college()` checks authorization but uses raw tenant GUC at three locations; endpoints also commit in some flows. | Keep authorization-before-context ordering; call signed setter after authorization and renew context after commit before any further protected query. Propagate authenticated actor to upload work. | Admin operations may fail after commit or accidentally change tenant scope. Test per route and transaction boundary; coordinate release with migration. |
| `backend/app/api/v1/colleges.py` | `create_college()` directly creates a tenant for an authenticated caller; `update_college()` accepts a college ID without proving College Admin membership. | Resolve the human choice: route public creation through pending registration or restrict direct creation to Super Admin; verify active membership for profile updates; route state changes through constrained function. | Registration/admin UX and response schema can change. Test each approved role and transition; rollback route behavior before DB enforcement only if existing privileges remain safe. |
| `backend/app/api/v1/chat.py` | Generates random guest tokens, stores their hash and returns the token on session creation; later sets raw visitor-token GUC and has route-level ownership checks. | Set signed VISITOR context containing digest before protected reads/writes; remove raw-token GUC; store immutable `visitor_token_expires_at` at creation +24h; preserve one-time response and route-level expiry guard. | Guest history/message behavior can break; route guard alone is not RLS proof. Test correct/wrong/expired/cross-session tokens, including DB-level denials. Coordinate with schema; rollback only to an approved old DB version on disposable target. |
| `backend/app/models/chat.py`, `backend/app/schemas/chat.py` | `ChatSession` has `visitor_token_hash` but no expiry field; schema exposes an optional visitor token. | Add the database-matched absolute expiry field; retain token only on initial guest creation response; do not serialize hash/token on later reads. | ORM/schema mismatch can fail inserts or response validation. Test create/history responses and expiration. Revert model/schema before migration only; do not remove a persisted expiry in a deployed forward-only path. |
| `backend/app/api/v1/feedback.py`, `backend/app/schemas/support_and_analytics.py` | Feedback path reads message/session without first installing matching tenant context and accepts no guest-token header. | Accept token only in a header; establish signed USER or VISITOR context first; verify message/session/tenant/user relationship; keep feedback append-only and admin-read scoped. | Feedback may be denied until clients send token. Test authenticated and guest flows with matching and mismatched fixtures. Roll back endpoint before the policy cutover only. |
| `backend/app/api/v1/support.py`, `backend/app/services/support_service.py` | Ticket flows include commits around ticket/reply operations and separate notification commits; guest/admin authorization is partly route/service based, without consistent DB context. | Enforce public ticket create-only for active approved college; bind USER/PUBLIC_TICKET context; enforce student owner/public-reply and staff tenant/internal-reply rules; keep writes and event-specific notification atomic; remove unnecessary mid-flow commits. | Ticket create/list/reply/status and email/in-app notification behavior can regress. Test all actor classes and transaction failure atomicity. No broad guest access fallback on rollback. |
| `backend/app/services/in_app_notification_service.py` | `create_notification()` accepts arbitrary recipient/title/body/type/link and directly inserts/commits. | Replace arbitrary insert with the approved `TICKET_CREATED` and public `STAFF_REPLY` event contract; derive recipient/content from ticket and verified actor; allow only owner-read and `is_read` update; no guest recipient. | Existing notification UX changes, especially internal replies. Test event allowlist, recipient derivation, private-note exclusion and same-transaction write. |
| `backend/app/repositories/user_repository.py`, `backend/app/models/user.py` | `get_by_id()`/`list_users()` use `select(User)`, fetching password and token fields; generic update can write sensitive attributes. | Replace entity-wide selects with safe explicit projections; prevent lazy reads of deferred sensitive fields; route create/profile/role/credential changes through approved narrow boundaries. Retain the seven-field auth function for local hash verification. | ORM code may unexpectedly access unloaded fields; login and profile shape can regress. Test every actual caller and prohibit direct sensitive-column reads/writes under runtime role. |
| `backend/app/services/auth_service.py`, `backend/app/api/v1/auth.py`, `backend/app/api/v1/users.py`, `backend/app/api/v1/memberships.py` | Auth service handles login, registration, password reset and verification; forgot-password currently discards the service token; user APIs update profiles and Super Admin role/active state; membership assignment changes user role. | Use separate hashed, expiring, purpose-bound reset and verification tokens and atomic consume functions. Keep generic reset response and development-only one-time registration token semantics. Route profile changes separately from Super Admin privilege changes. Do not invent reset email delivery until approved. | Login, registration, password reset, verification and admin assignment are high-impact regression paths. Unit/API plus DB-backed role tests required. Revert application calls before switching SQL contract; no plaintext token recovery after storage migration. |
| `backend/app/api/v1/analytics.py`, `backend/app/repositories/college_admin_repository.py` | College analytics query chat messages/sessions directly; analytics routes do not establish signed tenant context. | Bind validated signed tenant; use a constrained aggregate-only DB function/view; deny raw message/prompt content to college admins. | Charts/counts may differ from existing UI. Compare approved aggregate outputs and deny cross-tenant/raw-content reads. |
| `backend/app/services/document_service.py`, `backend/app/services/crawler_service.py`, `backend/app/services/knowledge_service.py`, `backend/app/services/rag_service.py` | Request and background flows open tenant sessions; task updates use tenant/resource IDs; RAG reads approved/published chunks. | Propagate initiating user for HTTP uploads; background writes use job-scoped WORKER context; RAG selects only active same-tenant APPROVED/PUBLISHED content. Re-sign after transaction boundaries. | Document ingestion/crawling/reprocessing and answers may fail if job leases expire. Test retry/duplicate/resource binding and existing pipeline behavior; do not add generic tenant bypass on rollback. |
| `backend/app/tasks/celery_app.py`, `backend/app/tasks/document_tasks.py`, `backend/app/tasks/knowledge_tasks.py`, `backend/app/tasks/crawler_tasks.py` | Celery/local task paths receive tenant/resource IDs and use shared `tenant_session()`; local fallbacks execute in the web process. | After the worker decision, queue only generated job IDs; claim authoritative tenant/resource and a one-time lease through restricted functions; sign WORKER context with a separate key/principal. Set lease to five minutes, heartbeat 60 seconds, and cap renewal at the existing one-hour task hard limit unless the human approves alternatives. Local fallback must use validated USER context or fail closed, never mint WORKER. | Duplicate/retried/long jobs can expire or repeat work. Test stale leases, retry/idempotency and cross-resource access. Disable dispatch on rollback; revoke worker login/EXECUTE only through an approved controlled operation. |
| `backend/app/services/ai_provider_service.py`, `backend/app/api/v1/super_admin.py`, `backend/app/models/ai.py` | `_log_telemetry()` and the Super Admin probe directly insert events; provider exception text can be stored in `error_message`. | Use a constrained `record_ai_provider_event` function with exact observed event allowlist and bounded numeric metrics; no prompts, response bodies, credentials, raw errors or caller actor IDs. Keep reads aggregate/Super Admin only. | Metrics and monitoring may change. Test accepted/rejected event shapes and unchanged safe aggregate counts; preserve existing function signatures until both app and SQL are coordinated. |
| `backend/app/services/notification_service.py`, `backend/app/repositories/registration_repository.py`, `backend/app/models/registration.py` | Direct notification-log insertion stores recipient/content/error/metadata; additional-info logs include prompt and rejection metadata may include free text. Registration repository also writes audit rows directly. | Use `record_notification_delivery` and allow only observed event/status types with DB-derived IDs/times and redacted summary. Remove prompt, token URL, raw error/rejection text and arbitrary metadata. Recipient retention is subject to human approval. | Email delivery and admin logs may lose fields. Test each event/status and privacy assertion; transaction rollback or forward-only correction according to branch. |
| `backend/app/repositories/super_admin_repository.py`, `backend/app/repositories/college_repository.py`, `backend/app/repositories/college_admin_repository.py`, `backend/app/api/v1/super_admin.py` | Super Admin routes/repositories perform college approval, membership assignment, direct audit writes, configuration and user updates; college profile writes are not safely distinguishable from state transitions under a shared role. | Route protected state changes through narrow functions deriving actor from signed context; implement the approved function-only/direct-column grant matrix; ensure audit event and domain update commit atomically. Preserve only actual endpoint operations; no speculative DELETE grants. | Admin workflows can fail on grant or signature mismatch. Test allowed and forbidden actions per role, including status/active and actor forgery. |
| `backend/app/schemas/user.py`, `backend/app/schemas/registration.py`, `backend/app/schemas/super_admin.py` | Response models expose selected account/registration/audit/notification data; schemas must not reveal password/token fields or unapproved private notification content. | Reconcile output fields to safe projections and approved payloads; keep invitation hashes, credential hashes, bearer tokens and raw provider errors out of serialization. | API contracts/frontend types can break. Run response-schema/API tests with synthetic sensitive sentinels. |

### 9.3 Additional repository call sites

| Exact path | Existing behavior and proposed change | Risk, tests and rollback |
|---|---|---|
| `backend/app/api/v1/notifications.py` | `list_notifications()`, `mark_notification_as_read()`, and `mark_all_notifications_as_read()` directly read/update notifications. Keep owner-scoped reads and updates to `is_read` only; set verified user context before each query and prohibit arbitrary recipient/content/college changes. | Counts and mark-all behavior can regress. Test other-user and cross-tenant rows and exact update columns; revert app changes before the policy cutover only. |
| `backend/app/api/v1/college_registrations.py` | Public registration, status, additional-information, and availability endpoints call registration functions/repositories. Keep tracking-code capability checks and rate limits; do not expose tracking codes, invitation tokens, hashes, unrestricted registration rows, or free-form submitted content in logs. | Test valid/expired/reused/wrong tracking capabilities and response redaction. Roll back endpoint changes before SQL contract switch; no token recovery after destructive column changes. |
| `backend/app/repositories/membership_repository.py` | Reads memberships and creates rows; membership role/tenant values are authorization inputs. Keep only required self/admin reads and move assignment/invitation writes to validated Super Admin/invitation functions. | Login tenant resolution and membership administration can regress. Test self/tenant reads and cross-tenant writes; revert before the final policy cutover only. |
| `backend/app/repositories/chat_repository.py` | Direct ORM session/message/feedback create, read, and update paths. Align each operation with signed purpose, owner and visitor expiry policies; keep tenant/owner/session linkage immutable and feedback tied to its message/session. | Conversation/feedback API can fail on column/policy changes. Test direct restricted-role operations against existing synthetic rows; do not use mocked success as RLS proof. |

### 9.4 Proposed database role/function boundary

These are the Step 3.1 proposed names and constraints, to be approved and then verified against the exact migration state. They are not existing roles/functions unless identified as existing below.

- Runtime web role `college_app_user`: NOLOGIN until final approval; non-owner; no privileged membership or `SET ROLE` path; no SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS/REPLICATION; schema USAGE only, no CREATE; grants limited to actual call sites. In particular, user SELECT is column-limited, no table-wide UPDATE on users, colleges, or notifications; no direct INSERT to audit or telemetry logs; no direct notification INSERT; no unnecessary sequence/default EXECUTE grants.
- Core direct privilege intent: users may be selected only through approved safe columns plus the seven-field auth function, with profile UPDATE limited to `full_name`, `preferred_language`, and `preferences`; credential and role/active changes use functions. Colleges allow SELECT and no direct state-changing DML. Membership reads are limited to authorization needs; assignment/acceptance writes use constrained functions. Notifications allow owner SELECT and `is_read`-only UPDATE; insert uses a workflow function. Audit and notification logs are append-only and function-written; telemetry is function-written and aggregate-readable only by Super Admin. Other application tables retain only actual repository/task CRUD operations in the Step 3 matrix, narrowed by tenant/operation RLS.
- Optional runtime worker role `college_app_worker`: separate credential and signing key only if approved; exact task-specific object and function grants; no web role inheritance; no BYPASSRLS. Queue payload carries job ID only; job claim returns authoritative scope.
- SECURITY DEFINER owners: proposed NOLOGIN groups `college_rls_verifier`, `college_policy_definer`, `college_auth_definer`, `college_user_write_definer`, `college_onboarding_definer`, `college_registration_definer`, `college_write_definer`, `college_audit_definer`, `college_telemetry_definer`, `college_notification_definer`, and `college_worker_definer`. Each owner receives only the table/column grants and role-targeted RLS policies needed by its function group; none is a member of or assumable by a runtime role. No general-purpose BYPASSRLS owner is proposed.
- Existing security-definer functions in 021 that require explicit owner/path/ACL review include `auth_private.is_request_context_valid()`, `public.current_app_user_id()`, `current_app_tenant()`, `is_platform_super_admin()`, `is_current_college_admin()`, `user_belongs_to_tenant(uuid,uuid)`, `lookup_user_by_email_for_auth(text)`, invitation lookup/acceptance, and the public registration functions. 022 recreates the auth lookup and must preserve its seven-column contract.
- Proposed constrained functions include user registration/profile/admin/credential transitions; college profile/state transitions; audit recording; AI telemetry recording; notification delivery/ticket notification; worker claim/heartbeat/finish/context validation; and verified visitor digest lookup. Names and signatures from Steps 3/3.1 are design proposals, not validated implementations.
- For every SECURITY DEFINER function: fixed `search_path = pg_catalog`, fully qualify all non-`pg_catalog` objects, explicit owner, `REVOKE EXECUTE FROM PUBLIC`, exact per-role EXECUTE grants, authorization derived from validated context/capability, and catalog assertions for owner attributes/memberships. Trigger-only `prevent_user_privilege_self_change()` receives no direct runtime EXECUTE.
- Detailed object-by-object DML allowlist remains the Step 3 role/table matrix, refined in implementation against actual caller and ORM cascade traces. Grant no DELETE where no caller exists; verify the possible `document_paragraphs` delete-orphan path before deciding. A function-owner policy is not permission to grant the runtime role direct table DML.

### 9.5 Existing test files to extend

| Exact path | Intended coverage and dependencies | Regression/rollback |
|---|---|---|
| `backend/tests/test_auth_lookup.py`, `backend/tests/test_auth_security.py`, `backend/tests/test_auth_endpoints.py` | Preserve seven-column lookup and login semantics; safe ORM projections; password reset/verification purposes, expiry, one-time consumption, no token/hash serialization. Requires the user function/role design first. | Keep existing API response contracts unless explicitly approved; revert application-only changes before SQL contract switch. |
| `backend/tests/test_multi_tenant_isolation.py`, `backend/tests/test_phase3a4_authz.py` | Extend to use actual restricted `college_app_user` against local Supabase-compatible PostgreSQL and synthetic AIT/RCTI tenant rows; verify cross-tenant read/write denial, raw GUC forgery, user/admin/super roles, policy OR cleanup and role catalog constraints. | Mock-only tests are not proof of RLS. Run only at Gate 5; disposable DB can be rebuilt after a failed validation. |
| `backend/tests/test_chat_rls_and_telemetry.py`, `backend/tests/test_analytics_and_support.py` | Guest-token expiry/replay/session binding; feedback; guest-ticket create-only; internal reply; aggregate-only analytics; notification ownership and private content. | Preserve API behavior for valid users/visitors; RLS tests require known existing fixture rows and exact runtime principal. |
| `backend/tests/test_email_notifications.py`, `backend/tests/test_ai_answering.py`, `backend/tests/test_crawler_tasks_async.py`, `backend/tests/test_document_upload_and_processing.py`, `backend/tests/test_database_models.py` | Test redacted delivery/audit payloads, telemetry allowlist, worker job claims/lease/retry/idempotency, task actor propagation and visitor-expiry model mapping. | Do not treat mocked DB operations as security validation; pair with database matrix. |
| New database-integration test location | **UNVERIFIED:** no existing dedicated PostgreSQL RLS integration harness was found in the inspected test files. After inspecting pytest configuration during an authorized implementation phase, choose a repository-consistent path rather than assuming a new module name now. | Must use a separately provisioned local Supabase-compatible stack and synthetic fixtures only. Do not run during planning. |

### 9.6 Migration dependency map and transaction sequence

All 22 migrations remain in numeric order. The dependencies below reflect the reviewed SQL and prior complete inventory. For 001–020, the future runner should apply **one file per explicit transaction** only after reviewing every statement and confirming the selected runner's semantics. Do not combine multiple files into a transaction. 021 and 022 own their `BEGIN`/`COMMIT`; never wrap either in an outer transaction.

| ID / file | Main objects and dependency | Role/Supabase/compatibility requirement | Future transaction, verification and recovery |
|---|---|---|---|
| 001 `001_extensions.sql` | Installs `uuid-ossp`, `pgcrypto`, `vector`; defines common enum types. No predecessor. | Verify extension availability, schema placement and pgvector compatibility before dependent DDL. | One file transaction; verify extension versions/types. On disposable failure, stop and rebuild/restore only that target. |
| 002 `002_create_colleges.sql` | Creates `colleges`; depends on 001 types. | No runtime role yet. Existing `IF NOT EXISTS` does not reconcile incompatible schemas. | One transaction; verify table/columns/FKs/indexes. |
| 003 `003_create_users_and_memberships.sql` | Creates `users`, `college_memberships`; depends on 001/002. | User/role enums and foreign keys must match. | One transaction; verify columns/FKs/constraints. |
| 004 `004_create_website_tables.sql` | Website sources, crawl jobs/events, pages; depends on colleges and 001 types. | No worker role yet. | One transaction; verify parent FKs and indexes. |
| 005 `005_create_document_tables.sql` | Documents, pages, paragraphs; depends on users/colleges and 001 types. | Confirm ORM relationships/cascades before final grants. | One transaction; verify FK delete behavior and indexes. |
| 006 `006_create_knowledge_tables.sql` | Facts, chunks/vector, reviews; depends on colleges/users and `vector`. | Required pgvector type/operator/index support must be verified on the actual local image. | One transaction; verify vector type/dimension/index operator class. |
| 007 `007_create_chat_tables.sql` | Chat sessions/messages; depends on users/colleges and shared enums. | Visitor-expiry extension is later; do not permit app access during setup. | One transaction; verify session/message FKs and indexes. |
| 008 `008_create_ai_and_audit_tables.sql` | AI provider config/events and audit logs; depends on core tables. | Actual ORM/table-name compatibility to be confirmed in implementation. | One transaction; verify columns/indexes and no unintended grants. |
| 009 `009_create_feedback_and_support.sql` | Feedback and support tickets; depends on chat, colleges/users and status enums. | Ticket/reply policies are later. | One transaction; verify FK/constraints. |
| 010 `010_create_indexes.sql` | Lookup, tenant, full-text, HNSW indexes over 002–009. | Index definitions must match installed pgvector. `IF NOT EXISTS` does not validate same-name definitions. | One transaction; inspect index definitions, not only names. |
| 011 `011_prepare_rls.sql` | Initial helpers and RLS on core tables; depends on 002–009. | Helper assumptions read GUCs and are not signed authority yet. App must remain disconnected. | One transaction; verify RLS enabled and exact initial policies. Failure requires stop/rebuild, not continued use. |
| 012 `012_college_onboarding_and_registration.sql` | Registration, reviews, invitations, onboarding progress, notification logs and related policies; depends on core schema/011. | Contains public/onboarding access patterns later constrained. | One transaction; verify types, tables, FKs, and RLS. |
| 013 `013_crawler_engine.sql` | Crawler enum/metadata/index additions; depends on 004. | New enum values must not be used by same transaction before commit. | One transaction for this file, then verify values/columns/indexes. |
| 014 `014_document_processing_and_ocr.sql` | Document/OCR columns, types, indexes; depends on 005. | Same-file enum commit semantics must be checked; no application access. | One transaction per file; verify new columns/types/indexes. |
| 015 `015_knowledge_and_rag_enhancements.sql` | Chunk category/content-hash/metadata/update columns and indexes; depends on 006. | Later RAG policies require same tenant and approved state. | One transaction; verify columns and index definitions. |
| 016 `016_analytics_support_and_multilingual.sql` | Support fields/replies, notifications, language/preferences and indexes; depends on 003/007/009. | New support/notification tables remain inaccessible until final policies. | One transaction; verify all objects and RLS status. |
| 017 `017_row_level_security_policies.sql` | Enables RLS and adds ticket/reply/notification/feedback/knowledge/page/event/document policies; depends on 011 and 002–016. | Current source references absent-on-vanilla `auth.uid()` five times; official Supabase provides it but it does not identify this app's custom JWT user. Correct/defer before any run. | One transaction; verify policies and no `auth.uid()` app identity dependency. Abort on any error. |
| 018 `018_create_application_role.sql` | Creates `college_app_user`, grants schema/table/sequence/function and defaults; depends on objects/helpers from 011–017. | Current placeholder password, premature LOGIN, wrong hard-coded database name and broad grants must be corrected. | One transaction; verify attrs, memberships, ownership, ACLs/default ACLs. Keep NOLOGIN. |
| 019 `019_complete_rls_policies.sql` | Unsigned helper and policies for users/memberships/messages/facts/reviews/logs/chunks; depends on 017/018. | Broad permissive interim rules create an unsafe state if app connects; final policy OR behavior must be audited. | One transaction; app remains disconnected through 021. Verify all interim names are removed/replaced at final state. |
| 020 `020_revoke_anon_grants.sql` | Revokes grants/default privileges from `anon`/`authenticated`; depends on official Supabase role bootstrap and 018. | Must run unchanged in a verified Supabase-compatible target; no fake role shim or silent skip. | One transaction; verify effective ACLs/default ACLs. Missing roles are a preflight blocker. |
| 021 `021_phase3a42_security_onboarding.sql` | Signed context, key store, registration/invitation, visitor token, policies; depends on 012–020, `college_app_user`, pgcrypto. | Has its own transaction; includes token hashing and irreversible post-commit column drops. Apply corrections only under selected branch. | Use its own transaction only. Before commit verify token counts/hash uniqueness and all constraints. After committed failure, restore approved snapshot or rebuild disposable DB; do not invent inverse SQL. |
| 022 `022_minimize_auth_lookup.sql` | Drops/recreates auth lookup function to seven-column result; depends on 021 and role. | Has its own transaction; preserves current function owner, which must be reviewed/replaced with explicit restricted owner. | Use its own transaction only; inspect dependencies, owner, path, grants, exact result fields. Do not use CASCADE. |
| Proposed next forward migration | `023_phase3a44_rls_context_privileges.sql` only if inventory proves 022 is the last applied version; otherwise next unused ID. | Branch B only. Exact contents/order depend on live schema inventory, current policies/data, and compatibility review. Never edit old migrations or assume this ID. | One transaction per independently safe migration. Include staged non-transactional operations only with explicit plan. Fail fast; recover by approved backup/restore or a separately reviewed forward repair. |

### Explicit final-policy inventory work

Before granting runtime LOGIN, list policies from the actual target catalog and compare with source. At minimum, the final migration plan must account for:

- `colleges`: replace `p_colleges_admin_all`; retain only approved public read and explicitly authorized profile/state operations.
- `users`: remove 019 `p_users_read`, `p_users_insert`, and broad update/delete variants; retain only verified self/admin access and constrained writes.
- `college_memberships`: remove 019 `p_memberships_read`/`p_memberships_write` broad rules.
- `support_tickets`, `support_ticket_replies`, `in_app_notifications`, and `feedback`: replace all five 017 `auth.uid()` dependencies with signed app identity and operation-specific rules.
- `knowledge_chunks`: remove any NULL-tenant published-read path; RAG access is same-tenant and active APPROVED/PUBLISHED only.
- `chat_sessions`/`chat_messages`: explicitly drop both the tenant policies and surviving super-admin permissive branch before installing final user/visitor/admin rules.
- `extracted_facts`, `knowledge_reviews`, `notification_logs`: replace every applicable `FOR ALL` and tenant-or-NULL policy; do not rely on OR-combined policies to narrow access.
- Crawler/document/page/event policies: split operations by admin/worker use and retain parent-tenant checks; keep document paragraph access default-deny until ORM cascade behavior is verified.
- AI provider config/events and audit logs: explicitly enable and verify RLS; no raw direct write privilege beyond the approved contract.

No new permissive policy is a substitute for dropping a broad old one. Verify each table's exact policy list, command, `USING`, and `WITH CHECK`; PostgreSQL permissive policies OR together.

## 10. Human decisions still required

| Decision required | Current evidence | Options | Security implications | Recommendation | Human approval |
|---|---|---|---|---|---|
| 1. Have migrations 001–022 ever been applied/released? | No authoritative ledger found. Prior test report says none executed in its disposable target only; README gives cloud execution instructions. | Confirm unreleased/unapplied everywhere (A); confirm any/uncertain deployment (B). | Incorrectly rewriting deployed SQL loses history and can break environments. | Require written per-environment inventory; default uncertain history to B. | YES |
| 2. One trusted worker for all colleges vs tenant-isolated workers | Current Celery tasks share app engine/context; no separate DB principal/key is established. | One shared worker with per-job DB-validated authorization; separate tenant-isolated worker principals/keys/queues; or small explicit trust cohorts. | A shared worker compromise can reach every tenant in its scope. Tenant isolation reduces blast radius but increases operations complexity; all choices still require job/resource binding and active leases. | Prefer tenant-isolated workers or explicitly approved small trust cohorts. Permit an all-tenant shared worker only after documented blast-radius acceptance and independently reviewed compensating boundaries. | YES |
| 3. Worker claim, lease, retry and duplicate rules | Current task payloads carry tenant/resource IDs; no DB lease proof. Step 3.1 proposes 5-min lease, 60-sec heartbeat, existing 1-hour task cap. | Approve those limits or choose others; at-least-once idempotent jobs vs stricter single execution. | Expired/duplicated tasks can corrupt or cross-scope data absent lease/resource binding. | Job ID only in queue; DB claim derives tenant/resources; one-time lease token hash; 5/60/1-hour defaults; idempotent tasks and fail closed. | YES |
| 4. Exact SECURITY DEFINER owners/grants/search paths/RLS | 021 has many SECURITY DEFINER routines without explicit owners; 022 preserves existing owner. | Distinct NOLOGIN least-privilege owners; fewer owner groups; owner policies versus narrowly approved BYPASSRLS. | Owner/membership/search-path errors can defeat RLS or permit object shadowing. | Distinct NOLOGIN, no BYPASSRLS owners, fixed `pg_catalog` paths, fully qualified references, PUBLIC revoke, per-function EXECUTE, no runtime SET ROLE path. | YES |
| 5. Password-reset email delivery | Forgot-password route currently discards service-returned token; no end-to-end delivery behavior is established. | Configure approved email delivery; defer resets; another explicitly approved channel. | Returning tokens in public responses or storing plaintext risks account takeover. | Decide delivery owner/provider; store only purpose-bound token hash; keep generic response; never return token outside approved development-only registration behavior. | YES |
| 6. Notification recipient-email retention and duration | Current logs store recipient and content/metadata; prompt and error strings can be persisted. | Retain address for a bounded approved period; keyed/irreversible recipient reference; omit. | PII and account-linkability exposure; retention may be needed for operations. | Retain only if necessary, with explicit period and deletion process; omit message/prompt/token/error content. | YES |
| 7. Public college registration vs Super Admin-only creation | Public registration function creates pending/inactive tenant; `/colleges` route directly creates a college for authenticated user. | Route public create through pending registration; restrict direct create to Super Admin. | Generic insert can create unauthorized tenants or bypass approval. | Public endpoint only creates pending registration; state activation Super Admin only. | YES |
| 8. EDITOR/VIEWER permissions | Membership model contains role values; current helper primarily checks ADMIN and no complete role capability matrix was established. | Read-only/editor capabilities; no separate DB powers until product use is specified. | Role confusion can elevate users or strand existing members. | Define capability matrix before adding policies; default deny writes for EDITOR/VIEWER until approved. | YES |
| 9. Audit allowlists and telemetry metric bounds | Actual callsites include audit actions, provider event types, numeric metrics, free-form payload/error fields. | Approve event/payload keys, category set, bounds and retention. | Forged admin history, secret leakage or unbounded/inaccurate metrics. | Use Step 3.1 allowlists; derive actor/targets; store bounded numbers/fixed error categories only. | YES |
| 10. Signing-key overlap/rotation procedure | Current key table requires a single active key; v1 lacks key ID, purpose, xid/request binding. | Maintenance cutover with old/new verification overlap; staged dual-version; secret-manager rotation operator. | Unsigned or long-lived fallback permits replay; premature key retirement breaks requests. | Add key IDs/purpose and <=300-second contexts; one signer per purpose with short old-key verification overlap; maintenance cutover and named rotation operator. | YES |
| 11. PostgreSQL identity contract and worker claim trust anchor | Existing backend uses a shared engine and signed GUC context; this report does not establish whether deployed policies/functions inspect `session_user`, `current_user`, `current_role`, or external worker identity. | Authenticated per-pool database principal mapped to a NOLOGIN capability role; approved signed external identity with database verification; or another reviewed mechanism. Separately decide whether any direct-login test is required after SET ROLE coverage. | A mismatch between connection identity and effective role can invalidate tests or permit confused-deputy behavior; job UUID/GUC/worker name is not proof. | Prefer DB-authenticated `session_user` mapping plus constrained SET-only capability role; keep runtime roles NOLOGIN. Audit every identity-consuming function/policy and do not claim equivalence where `session_user` differs. | YES |

## 11. Updated security test matrix — design only

Run these only after Gates 1–4, against a separate verified local Supabase-compatible PostgreSQL stack. Keep actual runtime roles `NOLOGIN`. Connect through the dedicated disposable test harness, then use its single approved SET-only membership to `SET ROLE` to the actual restricted role (`college_app_user` and, where approved, `college_app_worker`); verify `current_user` after each switch. Do not run these tests as `postgres`, a table owner, or a copied-grants role. This validates effective privileges and role-targeted RLS, but not runtime-role authentication or `session_user` behavior as a direct login. Use synthetic A/B colleges with generated IDs and generated users/tickets/sessions/messages. For each denial, first prove the protected fixture exists via an authorized control context. Roll back test transactions or remove only the known synthetic fixture rows after each test. No test below was executed.

| Test identity / setup | Action | Expected result and negative assertion | Cleanup |
|---|---|---|---|
| Disposable harness `SET ROLE college_app_user`, synthetic AIT user and an existing RCTI session/message | Query the other tenant's known session/message; repeat with RCTI user against AIT rows. | Both cross-tenant reads return denied/no rows while control proves the rows exist; direct SELECT of another tenant's rows is not possible. | Roll back fixture transaction. |
| Disposable harness login before and after `SET ROLE college_app_user`; approved identity-consuming policies/functions identified by source review | Assert `session_user`, `current_user`, and `current_role`; exercise each path that uses them, plus signed-identity checks. | Before switch, current identity is the harness; after switch, `session_user` is still harness and `current_user = current_role = college_app_user`. Test fails if a production check accepts harness-only privileges/identity, if any identity source differs from its documented contract, or if a path requiring direct runtime `session_user` is marked covered by SET ROLE alone. Such a path remains unvalidated pending a separately approved test. | Roll back. |
| Separate `college_app_negative_test` login with no application/worker/owner memberships; two synthetic tenant rows and only the minimum test-fixture table privileges needed to exercise RLS | Attempt protected SECURITY DEFINER calls, worker claim and maintenance functions; set forged tenant/user/admin GUCs; try `SET ROLE` to app, worker, migration, and definer-owner roles; read/update the other tenant's known fixture; try `row_security = off` and schema `CREATE`. | Protected EXECUTE and role switches fail by ACL; caller-set GUCs do not change signed identity; cross-tenant reads return no rows and updates affect zero rows under RLS; disabling row security never exposes rows; CREATE denied. A baseline attempt without fixture-table grants must fail at ACL and is not counted as an RLS assertion. | Roll back; fixtures and any minimal test-only grants exist only in the approved disposable environment. |
| `college_app_negative_test`, inspect role identity and authorization helpers before and after denied actions | Record `session_user`, `current_user`, `current_role`; inspect direct/transitive role-path report; attempt user/tenant identity changes and privileged maintenance operations. | Identity remains the negative-test login; no protected role path, `ADMIN OPTION`, inherited privilege, `BYPASSRLS`, table ownership, or protected-function EXECUTE. Any unexpected identity/privilege is a test failure. | No row cleanup; remove only test principal/grants under approved disposable-environment cleanup. |
| Disposable harness `SET ROLE college_app_user`, two users in one synthetic college, sessions/messages for both | User 1 reads User 2's session/messages and attempts to update owner/session/tenant IDs. | Denied; own rows remain accessible; ownership/parent IDs cannot be reassigned. | Roll back. |
| Disposable harness `SET ROLE college_app_user`, user row with non-null password hash and token fields | Direct SELECT of `hashed_password`, verification/reset token hashes, and unapproved sensitive columns; call the approved login lookup. | Direct sensitive-column access denied; lookup returns exactly seven approved auth fields to the backend function caller; hash does not appear in API JSON/logs. | Roll back; no real credentials. |
| Disposable harness `SET ROLE college_app_user`, ordinary student | Directly update own role, active/verified state; grant own Super Admin membership or use `SET ROLE` to an owner. | SQL permission/RLS/trigger denial; no role membership or privilege elevation. | Roll back. |
| Disposable harness after `SET ROLE` to the applicable runtime role, any signed-context protected table | Set arbitrary tenant/user/admin/purpose GUCs without signature and query/update matching known rows. | Denied; raw caller-controlled GUCs never authorize. | Roll back. |
| Disposable harness after `SET ROLE` to the applicable runtime role, one valid signed request context | Alter a signed field; use expired/overlong time; copy signature to a second transaction; replay after commit. | Altered, expired, overlong and cross-xid contexts denied; same exact claims only work in the signed transaction for <=300 sec. | Roll back each transaction. |
| Disposable worker harness `SET ROLE` to approved worker role, queued job bound to synthetic tenant A/document A | Claim and update exact resource; then try tenant B or another A resource, stale/expired lease, wrong lease token, duplicate completion. | Exact active job succeeds; every mismatched, expired, duplicate or unleased resource action is denied. Web role cannot claim or mint WORKER. | Roll back job fixtures. |
| Disposable worker harness authenticated/mapped to synthetic pool A; known queued job belongs to synthetic pool B | Submit B's valid job UUID, spoof B's tenant/worker GUCs or worker name, then attempt claim/context installation. | Denied before lease creation; no attempt/lease mutation for B; no signed context is issued. Verify B's job exists through a separate control identity. | Roll back job fixtures. |
| Disposable harness `SET ROLE college_app_user` with VISITOR context, two guest sessions with distinct hashes | Access own session with matching token; use token 1 for session 2, missing token, raw GUC digest, expired token, or renew expiry. | Only matching unexpired token works; cross-session/missing/raw/expired denied; expiry immutable at creation +24h. | Roll back. |
| Anonymous visitor and existing other-owner ticket/feedback fixtures | Create a guest ticket in active approved A and submit feedback with the matching visitor token; then try guest list/detail/update/reply and feedback with no, mismatching, or expired context. | Valid guest ticket create and matching feedback succeed; guest ticket read/update/reply and mismatched feedback are denied. | Roll back. |
| Student and College Admin with public/internal ticket replies | Student reads own public reply and tries internal reply/other user's ticket; Admin A reads A internal reply and tries B ticket. | Owner sees only public replies; admin sees only same-tenant content; internal reply insertion by student denied. | Roll back. |
| Ordinary user plus another user's in-app notification | Read and mark own notification read; read/update other user's notification or insert arbitrary recipient/body. | Own read and `is_read` update permitted; other-owner access and direct insert/content change denied; no internal-reply notification. | Roll back. |
| Disposable harness switching to the specifically approved notification-log writer and Super Admin reader, with synthetic registration/invitation rows | Record an allow-listed delivery status; attempt to read private email content and submit prompt, token URL, arbitrary metadata, caller-selected recipient or raw provider error. | Only approved event/status and redacted summary persist; private body, prompt, invitation token/link, raw error and unapproved recipient data are absent; non-Super Admin cannot read logs. | Roll back. |
| Disposable harness switching to non-admin and Super Admin roles with existing audit fixtures | Insert forged actor/action/target or update/delete audit row; Super Admin invokes approved action. | Forged caller identity, unknown action/payload, direct DML/update/delete denied; authorized action writes one DB-derived actor row atomically. | Roll back. |
| Disposable harness switching among approved USER/VISITOR/WORKER and Super Admin roles | Submit known allowed event and bounded metrics; submit raw prompt/error, unknown event, negative/oversized metrics, wrong config/tenant. | Allowed event records only approved numeric/category fields; unauthorized or out-of-range values denied; no prompts, credentials, provider response or raw exception persists. | Roll back. |
| Disposable harness switching to College Admin A and Super Admin, pending/approved synthetic colleges | Admin updates profile; attempts insert, approve, activate, change slug/status or touch B. Super Admin uses valid transition function. | Admin may update only approved same-tenant profile fields; cannot create/approve/activate/change protected state; Super Admin valid transition and audit commit together. | Roll back. |
| Disposable harness switching to each approved runtime role, all SECURITY DEFINER functions | Inspect catalogs; invoke functions with forged tenant/actor/token/job inputs; attempt PUBLIC and owner-role execution. | Owner is explicit NOLOGIN/non-bypass; fixed path; PUBLIC revoked; exact runtime grants only; authorization checks deny misuse and cross-tenant probes. | Roll back; catalog is read-only. |
| Disposable harness after separately switching to `college_app_user` and `college_app_worker` | Inspect effective role attributes/memberships/ownership, attempt `CREATE` in public, read private key table, exercise unneeded functions. | No ownership, SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS, privileged membership, schema CREATE, key access, or non-allowlisted EXECUTE. | No row cleanup needed; role changes prohibited during test. |

## 12. Updated rollback and recovery strategy

This is a future runbook, not authorization to execute.

1. Complete human Gate 1 and formally choose Branch A or B. For Branch B, first inventory each environment through an approved process and identify the actual last-applied migration and schema state.
2. Obtain Gate 3 approval for a **new** local Supabase CLI project, isolated from the preserved vanilla PostgreSQL container. Verify PostgreSQL major version 17, pgvector version/schema, Auth `auth` schema and `auth.uid()`, `anon`/`authenticated` roles, dedicated volume/network, and loopback-only ports. No hosted-project login/linkage.
3. Keep API, worker, pooler and Data API clients offline; keep runtime roles `NOLOGIN`. Positively verify target identity before every DDL phase.
4. Take an approved snapshot of any synthetic nonempty validation DB before destructive changes. For 021, complete preflights before it starts and embed every data-dependent assertion before its internal `COMMIT`; if an assertion fails, the transaction must roll back. Never attempt to pause after the migration statements but before its internal commit.
5. Apply the reviewed files in numeric/approved forward order, one migration at a time. For 001–020, use one transaction per file only after explicit compatibility review; use fail-fast behavior. Run 021 and 022 with their internal transactions only, never nested. Record filename, start/end timestamps, exit status, and SQLSTATE. Stop on first failure.
6. After each committed migration, run only its approved read-only catalog assertions. Do not continue after a migration error; do not patch SQL in flight or resume a partial chain without an approved repair plan.
7. Before runtime login, verify every policy, function owner/search path, PUBLIC and role grants, table/column grants, sequence/default privileges, role membership, RLS state, helper-function privileges, and both allowed and denied access on known fixtures.
8. Enable login/provision test credentials or signing keys only after separate authorization and complete catalog/security test approval. Credential delivery must use an approved protected channel and values must never be logged or placed in migration files.
9. After failure in an uncommitted migration transaction, abort and retain the ledger. For a disposable validation environment, rebuild only that specifically identified new project after approval; do not modify or delete the preserved container/volume. For a deployed Branch B environment, use the approved restore point or separately reviewed forward repair. Never run an improvised destructive downgrade.
10. 021-equivalent changes that hash tokens and drop columns have no data-preserving inverse after commit. Recovery is an approved backup restore or a new disposable rebuild; do not recreate empty plaintext columns and claim rollback.

### Proposed read-only verification query shapes

The following are design examples only. None was executed for this report. Run only on the approved local disposable target after a separate execution approval.

```sql
-- Target identity and server
SELECT current_database(), current_user, version(),
       inet_server_addr(), inet_server_port();

-- Supabase compatibility and extensions
SELECT to_regnamespace('auth') AS auth_schema,
       to_regprocedure('auth.uid()') AS auth_uid;
SELECT e.extname, e.extversion, n.nspname AS extension_schema
FROM pg_catalog.pg_extension AS e
JOIN pg_catalog.pg_namespace AS n ON n.oid = e.extnamespace
WHERE e.extname IN ('vector', 'pgcrypto', 'uuid-ossp');

-- RLS/policy catalog comparison
SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
FROM pg_catalog.pg_policies
WHERE schemaname IN ('public', 'auth_private')
ORDER BY schemaname, tablename, policyname;

-- Runtime role attributes and role memberships
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolinherit, rolbypassrls, rolreplication
FROM pg_catalog.pg_roles
WHERE rolname IN ('college_app_user', 'college_app_worker');

-- Memberships and object ownership / RLS state
-- Direct edge inventory only; this is not a transitive membership audit.
-- Use the recursive PostgreSQL 17 traversal in Section 5 for reachability.
SELECT member.rolname AS member, parent.rolname AS granted_role,
       m.set_option, m.inherit_option, m.admin_option
FROM pg_catalog.pg_auth_members AS m
JOIN pg_catalog.pg_roles AS member ON member.oid = m.member
JOIN pg_catalog.pg_roles AS parent ON parent.oid = m.roleid;
SELECT n.nspname, c.relname, c.relowner::regrole AS owner,
       c.relrowsecurity, c.relforcerowsecurity
FROM pg_catalog.pg_class AS c
JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname IN ('public', 'auth_private')
  AND c.relkind IN ('r', 'p');

-- Security-definer owner, path and function grants
SELECT p.oid::regprocedure, r.rolname AS owner, p.prosecdef, p.proconfig,
       p.proacl
FROM pg_catalog.pg_proc AS p
JOIN pg_catalog.pg_roles AS r ON r.oid = p.proowner
WHERE p.prosecdef
ORDER BY p.oid::regprocedure::text;
```

Additional approved checks must inspect actual function/table/column ACLs, `pg_default_acl`, role memberships, object ownership, RLS enabled/forced state, and exact auth lookup result fields. Catalog queries alone do not prove row isolation; execute the synthetic positive/negative matrix as the restricted roles.

## 13. Explicit approval gates, files changed, and limitations

1. **Gate 1 — Human design approval:** Approve Steps 3 and 3.1; resolve all eleven decisions in Section 10; approve function owners, worker trust anchor, policy behavior and rollback approach.
2. **Gate 2 — Migration-history confirmation:** Provide written environment-specific migration status; select Branch A only with explicit unreleased/unapplied confirmation, otherwise Branch B. Confirm recovery point and migration compatibility.
3. **Gate 3 — Disposable environment readiness:** Approve a separate Supabase-compatible local environment; verify versions, roles, auth schema/function, extensions, isolated volume/network and loopback-only ports. Define the harness and independent negative-test principal with no privileged membership paths; use only synthetic fixtures and narrowly scoped test-only table privileges where needed to exercise RLS. Keep the existing PostgreSQL test container untouched.
4. **Gate 4 — Controlled implementation authorization:** Approve exact files, branch-specific migration IDs, worker/key/role provisioning plan and recovery runbook. Provide explicit authorization to modify files; this Step 4 report is not that authorization.
5. **Gate 5 — Database security validation:** Apply approved migrations; verify runtime role restrictions and the complete PostgreSQL 17 membership closure; execute synthetic two-tenant tests through SET ROLE plus independent negative-principal tests. SET ROLE validates the effective capability role (`current_user`/`current_role`) but does not validate direct-login `session_user` behavior. Any production authorization path relying on `session_user` must remain explicitly **UNVALIDATED** until a separately approved disposable direct-login test using the appropriate test principal/authentication model is completed; SET ROLE alone can never satisfy that requirement. Do not mark Gate 5 complete for such a path before that test. Confirm no unresolved critical finding. Only then consider a separate release/provisioning approval.

No gate may be skipped. This plan has not passed Gates 1–5.

### 13.1 Files inspected and files changed

**Files read or specifically inspected for this correction:**

- `.agents/tasks/phase3a4.4b-step4-controlled-implementation-plan.md`
- `.agents/tasks/phase3a4.4b-step3-final-approval-package.md`
- `.agents/tasks/phase3a4.4b-step3.1-security-gap-closure.md`
- `.agents/tasks/phase3a4.4b-step2-migration-validation-report.md`
- `database/migrations/021_phase3a42_security_onboarding.sql` (transaction boundary, token/hash changes, policies, and function security)
- The repository source, test, workflow, and documentation paths enumerated in Section 3; migration inventory findings for 001–022 are carried forward from the prior Step 2 investigation.

**Files modified or created in this documentation correction:**

- Modified: `.agents/tasks/phase3a4.4b-step4-controlled-implementation-plan.md`
- Modified: `.agents/tasks/phase3a4.4b-step4-correction-summary.md`

Only these documentation files were changed. No source-code, SQL, migration, test, or configuration files were changed. No SQL statement, migration, test, database, role, credential, key, container, volume, test data, or deployment was executed or modified. The PostgreSQL 17 recursive query in this Markdown report is a proposed example only and was not executed.

### 13.2 Limitations and unresolved blockers

- **Migration history:** UNVERIFIED. This is the primary blocker to selecting in-place versus forward-only edits.
- **Supabase compatibility:** No new Supabase stack has been provisioned or verified. The preserved PostgreSQL container is not Supabase Auth.
- **Worker boundary:** No separate worker DB principal/key, claim source, queue trust boundary, or fallback decision exists in current code.
- **Database identity semantics:** The reviewed plan does not establish whether deployed policies/functions rely on `session_user`, `current_user`, `current_role`, or a role-membership path. The SET ROLE harness intentionally has a different `session_user`; direct-login equivalence remains unverified wherever it matters.
- **Role closure and negative principal:** No role catalog was queried. The PostgreSQL 17 recursive membership audit, protected-role allowlist, and independent negative-test login are proposed only; their setup and outcomes remain unverified.
- **Worker claim implementation:** The per-pool authenticated principal mapping, claim/context function owners and grants, signing-key access boundary, and lease schema are proposed, not implemented or validated.
- **Transaction-bound context:** Code has multiple explicit commits and raw tenant/token GUC setters. A signer/verifier rollout must coordinate all callers; partial deployment would fail closed and break requests.
- **Sensitive ORM reads:** `select(User)` currently fetches mapped sensitive fields; column revocation without coordinated projection changes breaks runtime code.
- **Password reset:** Delivery path is not established; do not invent a channel or expose reset token.
- **Policy OR behavior:** Old permissive policies can continue granting access despite new narrow policies; exact final catalog comparison is mandatory.
- **SECURITY DEFINER ownership:** Actual ownership depends on migration executor. Do not infer or preserve a privileged owner without catalog verification and a reviewed correction.
- **Operational correctness:** Celery retries, lease expiry, event idempotency, notification atomicity and multi-transaction jobs require integration tests.
- **Potentially irreversible data operations:** Migration 021 hashes and drops plaintext invitation token and drops initial-admin password hash. A committed drop cannot be undone by SQL alone.
- **Documentation/deployment ambiguity:** `database/README.md` still documents direct hosted SQL execution. The CD workflow does not prove migrations were run; authoritative change records are unavailable in this read-only repository review.

### 13.3 Exact recommended next action

Have the authorized database/release owner provide a written migration-history statement for every environment (including whether any migration was applied, released, partially applied, or is uncertain), then obtain human decisions for all eleven items in Section 10. If any history is applied or uncertain, select Branch B and inventory the current schema through an approved non-production process before naming the forward migration.

After that, seek separate approvals for Gate 3 environment provisioning and Gate 4 file modifications. Until those approvals are explicit, do not change code, migrations, roles, credentials, keys, containers, or databases.

## Final recommendation

**READY FOR HUMAN REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION — NOT DATABASE VALIDATED**

Verified: repository source paths, migration SQL inventory/order, explicit transaction boundaries in 021/022, identified current call paths, local test/documentation limits, and the absence of repository evidence proving a particular deployment state.

Proposed: branch-specific file changes, security boundaries, forward-migration plan, test matrix, transaction/recovery runbook and implementation gates.

Unknown: migration application/release state in every environment; local Supabase stack runtime/version; actual deployed role/policy/function ownership; worker trust/lease operational configuration; reset-email and notification retention decisions.

Requires explicit human approval: migration branch, all eleven decisions, environment provisioning, implementation authorization, and later database-validation/release authorization. No implementation is complete or authorized by this report.
