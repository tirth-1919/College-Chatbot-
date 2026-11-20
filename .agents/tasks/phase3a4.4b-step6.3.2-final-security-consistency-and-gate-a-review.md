# Phase 3A.4.4B — Step 6.3.2: Final Security Consistency Corrections and Gate A Pre-Approval Review

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Auditor, Database Migration Reviewer  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Predecessor Documents:**
- [Step 3 Final Implementation Approval Package](./phase3a4.4b-step3-final-approval-package.md)
- [Step 3.1 Security Gap Closure Addendum](./phase3a4.4b-step3.1-security-gap-closure.md)
- [Step 4 Controlled Implementation Plan](./phase3a4.4b-step4-controlled-implementation-plan.md)
- [Step 5 Human Review and Decision Approval Package](./phase3a4.4b-step5-human-review-and-decision-approval.md)
- [Step 6 Human Decision Resolution Package](./phase3a4.4b-step6-human-decision-resolution.md)
- [Step 6.1 Technical Consistency & Auth Diagnostic](./phase3a4.4b-step6.1-technical-consistency-and-auth-diagnostic.md)
- [Step 6.2 Technical Findings Correction and Consolidation](./phase3a4.4b-step6.2-technical-findings-correction.md)
- [Step 6.3 Final Technical Consistency Review](./phase3a4.4b-step6.3-final-technical-consistency-review.md)
- [Step 6.3.1 Final Technical Corrections Addendum](./phase3a4.4b-step6.3.1-final-technical-corrections-addendum.md)
**Deliverable Document:** `.agents/tasks/phase3a4.4b-step6.3.2-final-security-consistency-and-gate-a-review.md`

---

## 1. Executive Decision

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR FORMAL HUMAN GATE A DECISIONS
================================================================================
```

This report represents the comprehensive, definitive, and strictly read-only technical consistency review and Gate A pre-approval audit for Phase 3A.4.4B. It resolves all lingering documentation-level ambiguities, reconciles source-code and migration evidence against planning documents, eliminates informal shorthand signatures, and establishes the exact boundary conditions under which the project may proceed to formal human and specialist Gate A decision-making.

### Explicit Operational Boundaries

1. **Audit and Documentation Only:** This document is an audit and governance artifact. It **does not constitute implementation authorization**.
2. **Zero Code or SQL Modifications:** No application source code, SQL migrations, DDL, or database objects have been created, modified, or executed.
3. **Zero Database Connections:** No socket or TCP connection has been made to local PostgreSQL, hosted Supabase, Redis, or any remote database.
4. **Gate Separation Maintained:**
   - **Gate A (Human Design and Specialist Approval):** **NOT COMPLETE** (Pending formal human owner and specialist sign-offs).
   - **Gate B (Implementation Authorization):** **NOT AUTHORIZED** (Implementation strictly prohibited).
   - **Gate C (Isolated Database Validation):** **NOT VALIDATED** (Validation strictly prohibited until Gate B).
   - **Production Release:** **NOT APPROVED** (Strictly prohibited).

---

## 2. Scope and Strict Read-Only Safety Declaration

In strict compliance with project safety directives, the following sixteen operational boundaries were upheld throughout this review:

1. Did not modify application source code in `backend/`, `apps/`, or `tests/`.
2. Did not modify SQL files, migrations, or DDL scripts in `database/`.
3. Did not create, alter, or execute database roles, grants, policies, functions, triggers, or schemas.
4. Did not execute SQL queries or statements against any database.
5. Did not connect to local PostgreSQL, hosted Supabase, or any remote database.
6. Did not connect to or modify Redis.
7. Did not execute migrations, Alembic upgrades, Supabase migrations, or database initialization routines.
8. Did not modify `.env`, `.env.*`, secrets, credentials, API keys, or connection strings.
9. Did not start, stop, recreate, or modify Docker containers, images, volumes, networks, or services.
10. Did not install, uninstall, or upgrade any package or dependency.
11. Did not modify CI/CD workflows (`.github/workflows/`) or deployment configuration.
12. Did not modify Git branches, commits, or repository history.
13. Did not alter existing user accounts, role IDs, tenant records, documents, or sessions.
14. Did not implement any proposed security remediation or architectural change.
15. Did not claim that PostgreSQL, Supabase, RLS, or production security has been validated without authorized runtime test evidence.
16. Did not print credentials, secret values, or complete sensitive connection strings in this report.

All technical findings are classified according to strict evidentiary standards:
- `[VERIFIED FROM REPOSITORY SOURCE]`: Confirmed directly by static inspection of repository files.
- `[VERIFIED FROM EXISTING TEST EVIDENCE]`: Grounded in existing test run logs archived in reports.
- `[VERIFIED FROM EXISTING DOCUMENTATION]`: Recorded in predecessor audit reports.
- `[PROPOSED DESIGN]`: Recommended architectural design or specification not yet implemented.
- `[NOT VERIFIED]`: Database catalog state, live runtime configuration, or unexecuted test suites.
- `[REQUIRES HUMAN DECISION]`: Blocked on an accountable project owner or specialist sign-off.

---

## 3. Files and Evidence Inspected

The following repository artifacts were inspected statically:
- `database/migrations/001_extensions.sql` through `022_minimize_auth_lookup.sql` [VERIFIED FROM REPOSITORY SOURCE]
- Specifically inspected DDL:
  - `database/migrations/017_row_level_security_policies.sql` lines 1–110 [VERIFIED FROM REPOSITORY SOURCE]
  - `database/migrations/018_create_application_role.sql` lines 1–45 [VERIFIED FROM REPOSITORY SOURCE]
  - `database/migrations/019_complete_rls_policies.sql` lines 1–115 [VERIFIED FROM REPOSITORY SOURCE]
  - `database/migrations/020_revoke_anon_grants.sql` lines 1–35 [VERIFIED FROM REPOSITORY SOURCE]
  - `database/migrations/021_phase3a42_security_onboarding.sql` lines 1–751 [VERIFIED FROM REPOSITORY SOURCE]
  - `database/migrations/022_minimize_auth_lookup.sql` lines 1–53 [VERIFIED FROM REPOSITORY SOURCE]
- Application Backend Code:
  - `backend/app/database/connection.py` lines 1–65 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/database/session.py` lines 1–209 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/repositories/user_repository.py` lines 1–65 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/services/auth_service.py` lines 1–120 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/api/v1/auth.py` lines 1–95 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/api/v1/chat.py` lines 1–210 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/tasks/celery_app.py` lines 1–50 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/tasks/document_tasks.py` lines 1–180 [VERIFIED FROM REPOSITORY SOURCE]
  - `backend/app/core/config.py` lines 1–215 [VERIFIED FROM REPOSITORY SOURCE]
- Test Configuration and Suites:
  - `tests/config.py` lines 1–99 [VERIFIED FROM REPOSITORY SOURCE]
  - `.github/workflows/ci.yml` lines 1–65 [VERIFIED FROM REPOSITORY SOURCE]
  - `.github/workflows/cd.yml` lines 1–55 [VERIFIED FROM REPOSITORY SOURCE]

---

## 4. Corrections from Step 6.3.1

Step 6.3.1 provided valuable initial corrections, but contained several documentation-level inconsistencies and shorthand notations that are formally corrected in this section:

1. **search_path Count Inconsistency (9 vs. 10 functions):**
   - *Previous Inconsistency:* Step 6.2 reported 10 functions using `pg_catalog, public, auth_private`; Step 6.3 reported 10; Step 6.3.1 mentioned both 9 and 10 in different sections.
   - *Root Cause Identified:* In migration `021`, exactly **10 functions** declare `SET search_path = pg_catalog, public, auth_private`. However, one of those 10 functions (`public.prevent_user_privilege_self_change()`, line 362) is a **TRIGGER function** that does **not** declare `SECURITY DEFINER`! Exactly **9 functions** with that search path are `SECURITY DEFINER`.
   - *Resolution:* There are 10 total functions in migration `021` declaring `pg_catalog, public, auth_private`, of which **9 are `SECURITY DEFINER`** and **1 is an unprivileged trigger routine**.
2. **Malformed Argument Signature in Inventory:**
   - *Previous Inconsistency:* In Step 6.3.1, Function #13 (`submit_public_registration_information`) was written with argument shorthand `(text, txt, jsb)`.
   - *Correction:* Replaced with the verbatim SQL signature: `(p_tracking_code text, p_response text, p_additional_documents jsonb DEFAULT '[]'::jsonb)`.
3. **Migration 022 DDL Operation:**
   - *Previous Ambiguity:* Reports described migration 022 alternatively as "modifying", "re-defining", or "replacing" the function.
   - *Exact DDL Verified:* Migration `022` lines 14–16 explicitly executes `DROP FUNCTION public.lookup_user_by_email_for_auth(text)` followed by `CREATE FUNCTION public.lookup_user_by_email_for_auth(p_email text)` [VERIFIED FROM REPOSITORY SOURCE]. This two-step process was required because PostgreSQL prohibits `CREATE OR REPLACE FUNCTION` from altering a function's return type (changing from `SETOF public.users` to `TABLE(...)`).
4. **URL Scheme Translation Prohibition:**
   - *Previous Inconsistency:* Step 6.3 suggested stripping or translating `postgresql+asyncpg://` to `postgresql://` in `tests/config.py`.
   - *Correction:* Test connection guards must validate schemes strictly against an allowed set; converting non-PostgreSQL or mismatched schemes dynamically is prohibited.

---

## 5. D-05: Exact SECURITY DEFINER Inventory and search_path Risk Analysis

### 5.1 Exact Repository Function Inventory

Every `SECURITY DEFINER` function across migrations `001_extensions.sql` through `022_minimize_auth_lookup.sql` is cataloged below [VERIFIED FROM REPOSITORY SOURCE]:

```
+----+---------------------------------------------------------------+--------------+-------+--------------------+---------------------------------+---------------------+-----------------------+
| #  | Schema & Function Name (Exact Signature)                      | Return Type  | Migr. | DDL Action in Migr.| Exact SET search_path           | PUBLIC Revoked?     | Migration Role Grants |
+----+---------------------------------------------------------------+--------------+-------+--------------------+---------------------------------+---------------------+-----------------------+
| 1  | auth_private.is_request_context_valid()                       | boolean      | 021   | CREATE OR REPLACE  | pg_catalog, auth_private        | Yes (PUBLIC, app)   | None (Internal only)  |
| 2  | public.current_app_user_id()                                  | uuid         | 021   | CREATE OR REPLACE  | pg_catalog, auth_private        | Yes (PUBLIC)        | college_app_user      |
| 3  | public.current_app_tenant()                                   | uuid         | 021   | CREATE OR REPLACE  | pg_catalog, auth_private        | Yes (PUBLIC)        | college_app_user      |
| 4  | public.is_platform_super_admin()                              | boolean      | 021   | CREATE OR REPLACE  | pg_catalog, auth_private        | Yes (PUBLIC)        | college_app_user      |
| 5  | public.is_current_college_admin()                             | boolean      | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 6  | public.user_belongs_to_tenant(p_user_id uuid, p_college_id u.)| boolean      | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 7  | public.lookup_user_by_email_for_auth(p_email text)            | SETOF users  | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 8  | public.lookup_college_invitation_by_token(p_token text)       | TABLE(...)   | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 9  | public.accept_college_admin_invitation(p_tok, p_fn, p_pw, p_u)| TABLE(...)   | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 10 | public.submit_public_college_registration(p_payload jsonb)    | TABLE(...)   | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 11 | public.check_public_registration_availability(p_sl, p_dom)    | boolean      | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 12 | public.get_public_registration_status(p_tracking_code text)   | jsonb        | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 13 | public.submit_public_registration_information(p_tc, p_r, p_ad)| jsonb        | 021   | CREATE OR REPLACE  | pg_catalog, public, auth_private| Yes (PUBLIC)        | college_app_user      |
| 14 | public.lookup_user_by_email_for_auth(p_email text)            | TABLE(7 col) | 022   | DROP then CREATE   | pg_catalog                      | Yes (PUBLIC)        | college_app_user      |
+----+---------------------------------------------------------------+--------------+-------+--------------------+---------------------------------+---------------------+-----------------------+
```

*Note on Function #13:* Exact signature is `public.submit_public_registration_information(p_tracking_code text, p_response text, p_additional_documents jsonb DEFAULT '[]'::jsonb)` [VERIFIED FROM REPOSITORY SOURCE].  
*Note on Non-Definer Trigger Routine:* `public.prevent_user_privilege_self_change()` (`021` lines 362–389) sets `search_path = pg_catalog, public, auth_private` but is NOT `SECURITY DEFINER` [VERIFIED FROM REPOSITORY SOURCE].

### 5.2 Definitive Reconciliation of Function Counts

1. **Total Written Definitions Across Migrations = 14:** Migration `021` contains 13 `CREATE OR REPLACE FUNCTION ... SECURITY DEFINER` blocks; migration `022` contains 1 `CREATE FUNCTION ... SECURITY DEFINER` block [VERIFIED FROM REPOSITORY SOURCE].
2. **Net Active Functions in Resulting Schema = 13:** When migrations are applied sequentially, Function #14 drops and replaces Function #7. Exactly 13 distinct functions exist in the resulting database catalog (1 in `auth_private`, 12 in `public`) [VERIFIED FROM REPOSITORY SOURCE].
3. **search_path Breakdown in Migration 021 (13 Definer Functions):**
   - **4 functions** declare `SET search_path = pg_catalog, auth_private` (Functions #1, #2, #3, #4) [VERIFIED FROM REPOSITORY SOURCE].
   - **9 functions** declare `SET search_path = pg_catalog, public, auth_private` (Functions #5, #6, #7, #8, #9, #10, #11, #12, #13) [VERIFIED FROM REPOSITORY SOURCE].
   - (Plus 1 trigger function declaring `pg_catalog, public, auth_private`, accounting for the 10 total `SET search_path` occurrences).

### 5.3 search_path Risk Analysis and Prerequisites for Safety Determination

Including `public` in the `search_path` of a `SECURITY DEFINER` function is a recognized configuration vulnerability (CWE-426). However, asserting whether this is an *actively exploitable vulnerability* or *currently safe* cannot be determined from migration files alone.

To prove either conclusion, the following eight prerequisites must be verified against an authorized, running database catalog [NOT VERIFIED]:
1. **Explicit Schema Privileges:** Verify `pg_namespace.nspacl` for schema `public`. Does any non-superuser role possess `CREATE` privilege?
2. **Role Memberships and Inheritance:** Verify whether `college_app_user` or any untrusted role inherits `CREATE` via intermediate role memberships (`pg_auth_members`).
3. **Object Creation Capabilities:** Verify whether any untrusted web client or authenticated database user can create tables, views, operators, or types in `public`.
4. **Function Ownership (`proowner`):** Verify `pg_proc.proowner`. If functions are owned by `postgres` or `supabase_admin`, do those roles possess `rolsuper=true` or `rolbypassrls=true`? (Superuser attributes cannot be assumed; they must be verified in `pg_roles`).
5. **Unqualified Object References:** Verify whether any query inside the 9 definer functions references tables, operators, or functions without explicit schema qualification (`public.`).
6. **Search-Path Manipulation Possibilities:** Verify whether transaction-local GUCs or session settings can alter the effective search path during definer execution.
7. **Runtime Role Capabilities:** Verify the runtime role executing the query (`pg_roles.rolcanlogin`).
8. **Malicious Object Precedence:** Verify whether an attacker can define a custom operator (e.g., custom `=` for `uuid` or `text`) that PostgreSQL's parser resolves before `pg_catalog` operators.

---

## 6. D-22: Authentication Lookup Function Privilege Analysis

### 6.1 Call-Site and Privilege Trace

1. **Calling Component:** `backend/app/repositories/user_repository.py` lines 38–60 (`get_auth_account_by_email`), invoked by `backend/app/services/auth_service.py` line 75 during user login [VERIFIED FROM REPOSITORY SOURCE].
2. **Database Role Utilized:** The repository receives an `AsyncSession` initialized by `backend/app/database/connection.py`, which binds `DATABASE_APP_ROLE_URL` (`college_app_user`) [VERIFIED FROM REPOSITORY SOURCE].
3. **Password Hash Exposure:** The returned 7-field projection from `public.lookup_user_by_email_for_auth(p_email)` explicitly includes `account.hashed_password` (field 3) [VERIFIED FROM REPOSITORY SOURCE].
4. **Application Endpoint Exposure:** Because `college_app_user` is the single shared database role utilized across all application connection pools (including student chat, document uploading, and public forms), any application endpoint running on that connection pool possesses the privilege to execute `SELECT * FROM public.lookup_user_by_email_for_auth(...)` [VERIFIED FROM REPOSITORY SOURCE].

### 6.2 Separation of Grant States

```
+------------------------------------+---------------------------------------------------------------------------------+
| Grant State Category               | Architectural Status and Evidence Base                                          |
+------------------------------------+---------------------------------------------------------------------------------+
| Repository-Defined Grants          | Code in user_repository.py expects EXECUTE access for college_app_user.        |
|                                    | [VERIFIED FROM REPOSITORY SOURCE]                                               |
+------------------------------------+---------------------------------------------------------------------------------+
| Migration-Defined Grants           | Migration 021 line 206 and 022 line 51:                                         |
|                                    | REVOKE ALL ON FUNCTION ... FROM PUBLIC;                                         |
|                                    | GRANT EXECUTE ON FUNCTION ... TO college_app_user; [VERIFIED FROM SOURCE]       |
+------------------------------------+---------------------------------------------------------------------------------+
| Actual Live Database Grants        | UNKNOWN / NOT VERIFIED. Live catalog grants in pg_proc.proacl remain uninspected.|
+------------------------------------+---------------------------------------------------------------------------------+
| Proposed Least-Privilege Design    | PROPOSED DESIGN: Dedicated authentication service connection role                |
|                                    | (college_auth_user) with exclusive EXECUTE; revoked from college_app_user.       |
+------------------------------------+---------------------------------------------------------------------------------+
```

### 6.3 Proposed Least-Privilege Architecture (Design Only — Not Implemented)

To isolate sensitive password hashes from the general application connection pool [PROPOSED DESIGN]:
1. **Dedicated Authentication Role:** Provision a distinct PostgreSQL login role (`college_auth_user`) mapped to a dedicated connection pool (`DATABASE_AUTH_ROLE_URL`) utilized exclusively by `AuthService`.
2. **Exclusive Privilege Grant:**
   ```sql
   REVOKE EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) FROM college_app_user;
   GRANT EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) TO college_auth_user;
   ```
3. **Database-Level Verification Alternative:** Alternatively, implement `public.verify_user_password(p_email text, p_password_attempt text) RETURNS TABLE(user_id uuid, role text, is_active boolean)` using `pgcrypto.crypt()`, verifying the Bcrypt hash inside PostgreSQL and never exposing `hashed_password` across the network socket.

### 6.4 Technical Distinction: CAST Syntax vs. Missing Function

Standardizing on `public.lookup_user_by_email_for_auth(CAST(:email AS text))` resolves asyncpg/SQLAlchemy parameter type resolution (`unknown` parameter coercion). However:
- `CAST(:email AS text)` **cannot** resolve an error if the function does not exist in the database catalog, if the function signature differs, or if the calling role lacks `EXECUTE` privilege [VERIFIED FROM REPOSITORY SOURCE].
- The live database status of `lookup_user_by_email_for_auth` remains **NOT VERIFIED**.

---

## 7. D-16: Disposable Test Environment and Redis Isolation Review

### 7.1 Comprehensive Fail-Closed Database URL Guard [PROPOSED DESIGN]

The future test safety guard must validate every database URL independently before creating an engine or opening a socket:
- Applicable URLs in codebase: `DATABASE_URL`, `DATABASE_APP_ROLE_URL`, `ASYNC_APP_URL`, `ASYNC_ADMIN_URL`, `SYNC_ADMIN_URL`, `SYNC_APP_URL` (`tests/config.py` lines 28–35) [VERIFIED FROM REPOSITORY SOURCE].
- **Ten Validation Requirements:**
  1. *Allowed Schemes:* Strictly `postgresql://` or `postgresql+asyncpg://`. Reject non-PostgreSQL schemes without conversion.
  2. *Allowed Hosts:* Strictly loopback (`127.0.0.1`, `localhost`, `::1`).
  3. *Expected Port:* Must match the port configured for the selected local test profile. Port `54322` is an example (Supabase CLI default), but the guard must accept the profile's configured port.
  4. *Disposable Database Name:* Must match the dedicated test database name (e.g., `postgres_test`).
  5. *Expected Role:* Must match expected test roles (`postgres` for admin URL; `college_app_user` for app role URL).
  6. *No Hosted Cloud Infrastructure:* Explicitly reject any hostname containing `supabase.co`, `supabase.in`, `amazonaws.com`, or public IPs.
  7. *No Environment Fallback:* If a test URL is missing, abort immediately. Do not fall back to `.env` or production.
  8. *No SQLite Translation:* Prohibit converting SQLite strings into PostgreSQL URLs.
  9. *Fail-Closed Execution:* Terminate test runner via `sys.exit(1)` before any network connection attempt.
  10. *All URLs Must Pass:* If even one URL fails validation, zero engines or connections are created.

### 7.2 Redis Test Isolation Architecture [PROPOSED DESIGN]

- **Current Repository State:** `backend/app/core/config.py` lines 144–146 configures `REDIS_URL = "redis://localhost:6379/0"`, `CELERY_BROKER_URL = ".../0"`, and `CELERY_RESULT_BACKEND = ".../1"` [VERIFIED FROM REPOSITORY SOURCE].
- **Critical Isolation Finding:** Using separate Redis database indexes (`/14`, `/15`) on a shared Redis instance does **not** provide robust infrastructure isolation. Redis database indexes share the same memory space, CPU, credentials, and network interface; a `FLUSHALL` command or key collision impacts all indexes.
- **Proposed Test Architecture:** Testing Celery and background tasks requires a **dedicated disposable Redis container** on an isolated loopback port, distinct credentials, and a dedicated network boundary [PROPOSED DESIGN].
- **Safety Boundary Upheld:** Zero connections or modifications were made to Redis during this review.

---

## 8. D-06 / D-07 / D-18: Identity and Test Architecture

### 8.1 Rigorous Identity Layer Distinction

```
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Identity Primitive       | Context Scope         | Consumed By                 | Functional Purpose                |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| session_user             | TCP Physical Session  | Connection listener,        | Authentication, Connection Mgmt,  |
|                          |                       | PgBouncer, pg_stat_activity | Connection-level audit logging    |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| current_user / current_role | Transaction / Routine | SQL object privilege checks | Authorization (Table ACLs, DDL)   |
|                          | (Switches on SET ROLE)| (pg_class, pg_proc grants)  |                                   |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Application JWT          | HTTP Request          | FastAPI dependencies        | Client Authentication & RBAC      |
|                          |                       | (get_current_user)          |                                   |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Signed Request Context   | Database Transaction  | PL/pgSQL RLS helpers        | Row-Level Multi-Tenant Isolation  |
| (app.request_context)    | (set_config is_local) | (current_app_tenant)        |                                   |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Supabase auth.uid()      | PostgREST (Native)    | Migration 017 legacy RLS    | Replaced by current_app_user_id() |
|                          |                       | (Dropped in 019/021)        | in application FastAPI flow       |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
```

- **`auth.uid()` Repository Verification:** Static search across repository migrations confirmed that `auth.uid()` appears **only** in `database/migrations/017_row_level_security_policies.sql` (lines 35, 56, 69, 78, 90) [VERIFIED FROM REPOSITORY SOURCE]. Migrations `019` and `021` explicitly drop those policies and replace them with `public.current_app_user_id()` [VERIFIED FROM REPOSITORY SOURCE]. It does not appear in `backend/` source code.
- **`session_user` Call-Site Inventory:** A static search of all repository SQL and Python code confirms that `session_user` is **not referenced** in any application query, trigger, or policy [VERIFIED FROM REPOSITORY SOURCE]. The only role-checking trigger (`public.prevent_user_privilege_self_change()`, line 372) checks `current_user <> 'postgres'`. `session_user` serves exclusively as the connection authentication identity.

### 8.2 Distinct Roles in Test Architecture

To validate database security without granting `LOGIN` to production capability roles [PROPOSED DESIGN]:
1. **Direct Login (Authorized Runtime):** Tests the actual connection string, credentials, and connection defaults of login roles.
2. **LOGIN Test Harness (`college_test_harness`):** An unprivileged test role with `LOGIN` and `NOINHERIT`, granted `SET-only` membership on capability roles:
   ```sql
   GRANT college_app_user TO college_test_harness WITH INHERIT FALSE, SET TRUE;
   ```
3. **`SET ROLE` into NOLOGIN Capability Role:** Executes `SET ROLE college_app_user;`. Changes `current_user` to evaluate effective table privileges and RLS, while preserving `session_user = college_test_harness`.
4. **Unprivileged Test Login (`college_test_unprivileged`):** A role with `LOGIN`, zero memberships, and zero table grants to verify Tier A ACL rejections.
5. **Zero-Tenant Principal:** A role with table privileges but no valid signed context to verify Tier B RLS rejections.

---

## 9. D-09: Multi-Tiered Negative Security Test Matrix

Negative testing must validate four distinct failure domains [PROPOSED DESIGN]:

```
+--------------------+----------------------------+-------------------------+---------------------+------------------------------------------+
| Tier & Focus Area  | Connecting Role / Principal| Active Context / State  | Target Operation    | Expected Precise Outcome                 |
+--------------------+----------------------------+-------------------------+---------------------+------------------------------------------+
| Tier A: ACL Denial | college_test_unprivileged  | No signed context       | SELECT ON users     | ERROR 42501 (permission denied for table)|
|                    | (Zero table grants)        |                         | INSERT ON chat_sess | ERROR 42501 (permission denied for table)|
+--------------------+----------------------------+-------------------------+---------------------+------------------------------------------+
| Tier B: RLS Denial | college_test_harness       | No signed context       | SELECT ON documents | Returns exactly 0 rows (empty set).      |
| (No Tenant Context)| (SET ROLE college_app_user)| (or invalid signature)  | INSERT ON documents | ERROR (RLS policy WITH CHECK violation). |
|                    |                            |                         | UPDATE ON documents | Affects exactly 0 rows.                  |
+--------------------+----------------------------+-------------------------+---------------------+------------------------------------------+
| Tier C: Cross-     | college_test_harness       | Valid signed context for| SELECT ON documents | Returns 0 rows for Tenant B records.     |
| Tenant Denial      | (SET ROLE college_app_user)| Tenant A (AIT)          | UPDATE Tenant B row | Affects 0 rows.                          |
|                    |                            |                         | INSERT Tenant B row | ERROR (RLS policy WITH CHECK violation). |
+--------------------+----------------------------+-------------------------+---------------------+------------------------------------------+
| Tier D: Privilege  | college_test_harness       | Active session          | SET ROLE postgres;  | ERROR 42501 (permission denied for role) |
| Escalation Denial  | (SET ROLE college_app_user)|                         | ALTER ROLE ...      | ERROR 42501 (must be superuser)          |
|                    |                            |                         | SELECT * FROM rls_context_keys; | ERROR 42501 (permission denied)  |
+--------------------+----------------------------+-------------------------+---------------------+------------------------------------------+
```

*Status:* All negative test fixtures remain **PROPOSED DESIGN / NOT VERIFIED** until executed against an authorized, isolated test database.

---

## 10. D-03: Worker Trust Model and Tenant Binding

### 10.1 Vulnerability in Current State

In the current codebase, background tasks receive `college_id: uuid.UUID` and `job_id: uuid.UUID` via Celery JSON messages (`backend/app/tasks/celery_app.py`, `document_tasks.py`). Tasks open sessions via `tenant_session(college_id=college_id)`, which sets the ambient GUC without database validation [VERIFIED FROM REPOSITORY SOURCE]. A compromised worker or corrupted queue message could assert an arbitrary `college_id`.

### 10.2 Ten-Stage Required Trust Chain [PROPOSED DESIGN]

1. **Authenticated Worker Principal:** Worker connects using dedicated service account credentials (`college_worker_user`).
2. **Capability Role:** Assumes `NOLOGIN` capability role `college_worker_role` holding table permissions for documents, chunks, and crawl jobs, but zero access to web user credentials or billing.
3. **Database-Validated Job Claim:** Invokes atomic function `claim_job(p_job_id, p_worker_id, p_lease_seconds)`.
4. **Database-Bound Tenant Identity:** The database verifies that `job_id` exists, is in `PENDING` status, and retrieves the genuine `college_id` from the database row.
5. **Lease Ownership and Expiration:** Updates job row with `worker_id`, `lease_expires_at = now() + p_lease_seconds`, and status `PROCESSING`.
6. **Lease Token Verification:** Returns a cryptographic lease token hash. Subsequent updates (e.g., chunk insertion) require passing this lease token.
7. **Tenant-Scoped Database Access:** Database session context is bound strictly to the retrieved `college_id`.
8. **Idempotent Task Execution:** Document chunk upserts use deterministic UUIDs (`uuid5(college_id, chunk_hash)`).
9. **Retry and Crash Recovery:** Unacknowledged jobs with `lease_expires_at < now()` are reclaimed after 3 attempts and dead-lettered.
10. **Cross-Tenant Prevention:** Worker cannot claim a job belonging to Tenant B while operating in a transaction bound to Tenant A.

---

## 11. D-10: Signing Key Rotation and Lifecycle Analysis

### 11.1 Reconciled Key Lifecycle Parameters [PROPOSED DESIGN]

Relying on a static 5-minute or 15-minute overlap without empirical derivation is unsafe. The dual-key overlap window must be calculated dynamically based on operational parameters:

$$\text{Overlap Window} = \text{Context Token TTL (300s)} + \text{Max Deployment Duration (600s)} + \text{Clock Skew Allowance (60s)} + \text{Cache TTL (120s)} = 1080\text{s} \approx 18\text{ minutes}$$

```
+--------------------------------------------------------------------------------------------------------------------+
| KEY LIFECYCLE STATE MACHINE                                                                                       |
+-------------------+------------------------------------------------------------------------------------------------+
| State             | Functional Behavior across Backend and Database                                                |
+-------------------+------------------------------------------------------------------------------------------------+
| ACTIVE            | The single current key used by FastAPI backend instances to sign outgoing request contexts.    |
|                   | Database verifier accepts signatures produced by this key.                                     |
+-------------------+------------------------------------------------------------------------------------------------+
| PREVIOUS          | Transitional key retained during rotation. Database verifier accepts signatures matching this  |
|                   | key ONLY IF statement_timestamp() < expires_at. Backend never signs new contexts with it.      |
+-------------------+------------------------------------------------------------------------------------------------+
| EXPIRED           | Transitioned automatically or via maintenance task once statement_timestamp() >= expires_at.  |
|                   | Verifier rejects all signatures produced by this key.                                          |
+-------------------+------------------------------------------------------------------------------------------------+
| REVOKED           | Emergency state set immediately via administrative UPDATE. Verifier immediately purges and      |
|                   | rejects this key, regardless of timestamps.                                                    |
+-------------------+------------------------------------------------------------------------------------------------+
```

### 11.2 In-Flight Transactions and Cache Invalidation Realities

1. **Database Revocation Effect:** Updating a key to `REVOKED` in `auth_private.rls_context_keys` immediately causes subsequent calls to `auth_private.is_request_context_valid()` to fail. However, it does **not** terminate an already-executing long-running SQL query that validated its context earlier in the transaction.
2. **Application Cache Propagation:** In a multi-instance deployment, backend instances caching `RLS_CONTEXT_SECRET` in memory must subscribe to Redis pub/sub rotation notices or enforce a short cache TTL (e.g., 60 seconds) to ensure rapid adoption of new keys.

---

## 12. D-19: Visitor-Token Authorization Analysis

### 12.1 Reconciled Lifecycle Across Code and Database

1. **Token Generation:** `backend/app/api/v1/chat.py` line 138 generates `secrets.token_urlsafe(32)` (256-bit entropy) [VERIFIED FROM REPOSITORY SOURCE].
2. **Digest Persistence:** Line 146 computes `hashlib.sha256(token).hexdigest()` and stores it in `chat_sessions.visitor_token_hash` [VERIFIED FROM REPOSITORY SOURCE].
3. **Application Verification:** `backend/app/api/v1/chat.py` lines 45–59 (`_assert_session_ownership`) validates presented bearer tokens via `hmac.compare_digest` before returning session messages [VERIFIED FROM REPOSITORY SOURCE].
4. **Current Database Consumption:** Migration `021` lines 455–462 evaluates `chat_sessions.visitor_token_hash = encode(digest(current_setting('app.chat_visitor_token', true), 'sha256'), 'hex')` [VERIFIED FROM REPOSITORY SOURCE].
5. **Signed Context Reality:** The visitor token is **not included** in the HMAC-signed request context payload in migration `021` (which signs `v1|user_id|college_id|...`) [VERIFIED FROM REPOSITORY SOURCE].

### 12.2 Security Status of Unsigned GUC

The unsigned GUC `app.chat_visitor_token` represents an architectural defense-in-depth gap, not an unauthenticated remote exploit:
- An attacker cannot access another college's sessions because `college_id = public.current_app_tenant()` is cryptographically verified by the HMAC context.
- Within a tenant, an attacker cannot access a victim's session without knowing the 256-bit pre-image token.
- However, because the GUC is unsigned, the database cannot independently verify that the application layer validated the bearer token.
- *Status:* Proposed context payload `v2` (incorporating `visitor_token_hash`) remains a **PROPOSED DESIGN**. Authorization resilience remains **NOT VERIFIED** until negative tests are executed in an authorized test database.

---

## 13. D-12: Privacy and Retention Disentanglement

To ensure compliance rigor, statutory frameworks and institutional policies are strictly separated:

```
+------------------------------------+---------------------------------------------------------------------------------+
| Governance Dimension               | Legal & Operational Reality                                                     |
+------------------------------------+---------------------------------------------------------------------------------+
| Legal Requirements (FERPA / GDPR)  | FERPA (34 CFR Part 99) mandates protecting educational records; it specifies no |
|                                    | 30-day purge rule. GDPR Article 5(1)(e) requires purpose-limited storage, not   |
|                                    | a universal 30-day calendar cutoff. [VERIFIED FROM DOCUMENTATION]               |
+------------------------------------+---------------------------------------------------------------------------------+
| Institutional Policy               | Academic institutions establish record retention schedules (frequently 3–7     |
|                                    | years for official records; shorter for operational logs).                      |
+------------------------------------+---------------------------------------------------------------------------------+
| Data Minimization Recommendation   | Recommending 30-day purge of notification logs and stripping email bodies/tokens|
|                                    | is an engineering best practice to minimize incident blast radius.              |
+------------------------------------+---------------------------------------------------------------------------------+
| Proposed 30-Day Retention Schedule | Engineering proposal in Step 6. NOT IMPLEMENTED.                                |
+------------------------------------+---------------------------------------------------------------------------------+
| Actual Approved Retention Schedule | UNAPPROVED / REQUIRES HUMAN DECISION. Blocked on formal written sign-off from   |
|                                    | Project Owner and Data Privacy Officer.                                         |
+------------------------------------+---------------------------------------------------------------------------------+
```

---

## 14. Final D-01 through D-22 Decision Register

Every decision remains **PENDING HUMAN DECISION**. No decision has been marked approved.

```
Status Legend:
[REC] = Recommended Technical Position
[EVI] = Repository Evidence Available
[UNV] = Database Evidence Unverified
[DEP] = Unresolved Dependencies
[PO]  = Project Owner Approval Required
[SPE] = Specialist Approval Required
[BLK] = Blocks Gate A
```

---

### D-01: Migration History and Branch Selection
- **[REC]:** Branch B (Forward-Only Corrective Migration `023_...`).
- **[EVI]:** Migrations 001–022 present in repository; CI runs in-memory SQLite; manual Supabase SQL instructions in README.
- **[UNV]:** Live database migration execution history (`schema_migrations`) is unverified.
- **[PO]:** Yes. Must formally authorize Branch B forward remediation.
- **[SPE]:** Database Release Engineer.
- **[DEP]:** Authoritative written confirmation of whether 001–022 were ever run in any environment.
- **[BLK]:** **YES**.

---

### D-02: Shared vs. Tenant-Isolated Worker Architecture
- **[REC]:** Mandatory database job claims and unprivileged worker role; operational choice between dedicated worker processes vs. shared pool with subprocess sandboxing.
- **[EVI]:** Shared Celery queue and Redis URL in `celery_app.py`; PyMuPDF document extraction in `document_tasks.py`.
- **[UNV]:** Worker queue memory footprint and performance under isolated execution unverified.
- **[PO]:** Yes. Budget and infrastructure complexity trade-off sign-off.
- **[SPE]:** Security Architect & Worker Platform Engineer.
- **[DEP]:** Finalization of worker deployment topology specification.
- **[BLK]:** **YES**.

---

### D-03: Worker Authentication and Claim Authorization
- **[REC]:** Worker connects with authenticated login principal, assumes `NOLOGIN` capability role `college_worker_role`, and calls `claim_job()` to obtain time-bounded cryptographic lease token bound to tenant.
- **[EVI]:** Tasks currently receive raw `college_id` via Celery JSON kwargs; session sets ambient GUC without database validation.
- **[UNV]:** Claim function and lease verification logic do not exist in live database catalog.
- **[PO]:** No.
- **[SPE]:** Database Security Architect.
- **[DEP]:** SQL definition and grant matrix for `claim_job()`.
- **[BLK]:** **YES**.

---

### D-04: Job Lease, Heartbeat, Retry, Duplicate, and Crash Handling
- **[REC]:** 5-minute initial lease, 60-second heartbeat, max 3 retries with exponential backoff, 1-hour hard dead-letter timeout, idempotent database upserts.
- **[EVI]:** `crawl_jobs` and `documents` have basic status columns, but lack lease expiration, heartbeat timestamps, and dead-letter queues.
- **[UNV]:** Database schema columns for lease tracking unverified in live catalog.
- **[PO]:** Yes. Acceptance of job recovery latency SLA.
- **[SPE]:** Distributed Systems Engineer.
- **[DEP]:** Agreement on heartbeat intervals and retry ceilings.
- **[BLK]:** **YES**.

---

### D-05: SECURITY DEFINER Ownership, Grants, search_path, and RLS
- **[REC]:** Dedicated `NOLOGIN` definer capability roles; strict `SET search_path = pg_catalog`; fully schema-qualified references; revoke `PUBLIC` execute; zero superuser ownership.
- **[EVI]:** 13 active functions across migrations 021 and 022; 9 definer functions in 021 set `search_path = pg_catalog, public, auth_private`; 022 sets `pg_catalog`.
- **[UNV]:** Live catalog `pg_proc.proowner` and `proacl` remain unverified.
- **[PO]:** No.
- **[SPE]:** PostgreSQL Security Architect.
- **[DEP]:** Migration script creating definer capability roles.
- **[BLK]:** **YES**.

---

### D-06: Identity Consumers: session_user, current_user, and Signed Context
- **[REC]:** Explicitly document consumers: `session_user` for connection auth/pooling; `current_user` for table ACLs; HMAC signed context for RLS. Prohibit RLS dependence on `session_user`.
- **[EVI]:** `session.py` sets HMAC GUCs; migration 021 checks signature; migration 021 trigger checks `current_user <> 'postgres'`. `session_user` is not referenced in repository SQL.
- **[UNV]:** Live database views, triggers, and procedures unverified for hidden `session_user` calls.
- **[PO]:** No.
- **[SPE]:** Application Security Engineer & Database Architect.
- **[DEP]:** Identity consumer verification report from isolated database.
- **[BLK]:** **YES**.

---

### D-07: Direct-Login Testing Requirement
- **[REC]:** Dedicated unprivileged test harness login (`college_test_harness`) executing `SET ROLE college_app_user` for RLS testing. Direct-login testing reserved for connection auth verification. Capability roles remain `NOLOGIN`.
- **[EVI]:** Tests currently run against SQLite in CI or connect via superuser in local scripts.
- **[UNV]:** Test harness credentials and role grants unverified in test catalog.
- **[PO]:** No.
- **[SPE]:** Security Test Engineer.
- **[DEP]:** Approval of test principal definition and `SET ROLE` harness.
- **[BLK]:** **YES**.

---

### D-08: PostgreSQL 17 Role-Membership Closure and Protected-Role Allowlist
- **[REC]:** Enforce protected-role allowlist; execute recursive cycle-safe CTE checking `set_option`, `inherit_option`, and `admin_option` in `pg_auth_members` to prove zero paths to superuser.
- **[EVI]:** Step 4 recursive query specification; migration 018 role creation.
- **[UNV]:** Live `pg_auth_members` catalog state unverified.
- **[PO]:** No.
- **[SPE]:** PostgreSQL Database Administrator.
- **[DEP]:** Execution of role recursion query on authorized test stack.
- **[BLK]:** **YES**.

---

### D-09: Unprivileged Negative-Test Principal
- **[REC]:** Four distinct negative test cases (ACL Denial, RLS Denial, Cross-Tenant Denial, Privilege Escalation) using separate test principals.
- **[EVI]:** Existing tests test tenant switching within single connection; lack separate unprivileged login principal.
- **[UNV]:** Negative test fixtures unverified in database catalog.
- **[PO]:** No.
- **[SPE]:** QA / Security Test Engineer.
- **[DEP]:** Specification of negative test fixtures and assertion suites.
- **[BLK]:** **YES**.

---

### D-10: Signing-Key Storage, Access, and Rotation
- **[REC]:** External secret store; dual-key schema (`ACTIVE` and `PREVIOUS`) in `auth_private.rls_context_keys`; calibrated overlap window; multi-instance cache invalidation; emergency `REVOKED` state.
- **[EVI]:** Migration 021 has unique partial index preventing dual active keys; `session.py` requires 32-byte secret.
- **[UNV]:** Contents of `auth_private.rls_context_keys` unverified in live catalog.
- **[PO]:** Yes. Key custody policy approval.
- **[SPE]:** Key Management Specialist & Application Security Engineer.
- **[DEP]:** Key management runbook and migration dropping partial unique index.
- **[BLK]:** **YES**.

---

### D-11: Password-Reset Email Delivery Provider or Deferral
- **[REC]:** Formally defer and disable self-service password reset in production until a contracted transactional email provider with verified SPF/DKIM/DMARC is integrated.
- **[EVI]:** `email_transport.py` implements mock/logging transport; reset tokens are discarded or logged.
- **[UNV]:** N/A (application service layer).
- **[PO]:** Yes. Product decision to disable feature vs contract provider.
- **[SPE]:** Communications Privacy & Security Specialist.
- **[DEP]:** Provider contract or pull-request disabling public reset endpoint.
- **[BLK]:** **YES**.

---

### D-12: Notification Email Retention and Data Minimization
- **[REC]:** Institutional 30-day retention schedule for notification delivery logs; automated scrubbing of recipient email addresses, tokens, and bodies after dispatch; Celery purge task.
- **[EVI]:** `notification.py` model; no automated pruning task in repository.
- **[UNV]:** Live notification table records unverified.
- **[PO]:** Yes. Written approval of 30-day retention schedule.
- **[SPE]:** Data Privacy & Compliance Officer.
- **[DEP]:** Written policy approval from Project Owner and DPO.
- **[BLK]:** **YES**.

---

### D-13: Public College Registration versus Super Admin-Only Registration
- **[REC]:** Public registration creates records in `college_registrations` with status `PENDING` only. Provisioning active tenants in `colleges` and creating admin accounts is strictly restricted to Super Admin approval.
- **[EVI]:** Public registration page in `apps/admin-frontend`; migration 021 defines `submit_public_college_registration()`.
- **[UNV]:** Registration table RLS policies unverified in live catalog.
- **[PO]:** Yes. Onboarding workflow business approval.
- **[SPE]:** Application Security Engineer.
- **[DEP]:** Registration approval workflow specification.
- **[BLK]:** **YES**.

---

### D-14: EDITOR and VIEWER Permission Matrix
- **[REC]:** Fail-closed RBAC: `VIEWER` is strict read-only; `EDITOR` can upload documents and edit drafts but cannot publish knowledge chunks or delete documents; `COLLEGE_ADMIN` holds publish/delete authority.
- **[EVI]:** Role enums in migration 003 define basic roles; intermediate dashboard roles lack database-level grants.
- **[UNV]:** Enum types and table grants unverified in live catalog.
- **[PO]:** Yes. Product RBAC matrix sign-off.
- **[SPE]:** Application Security Architect.
- **[DEP]:** Formal RBAC permission matrix document.
- **[BLK]:** **YES**.

---

### D-15: Audit Payload and AI Telemetry Allowlists and Redaction
- **[REC]:** Strict key allowlist for audit JSONB payloads; PII/credential scrubber; AI telemetry restricted to aggregate metrics (`tokens`, `latency_ms`) and error codes; raw prompts and stack traces prohibited.
- **[EVI]:** Migration 008 creates `audit_logs` and `ai_provider_events`; `_log_telemetry` logs API metrics.
- **[UNV]:** Live telemetry table rows unverified for unredacted data.
- **[PO]:** Yes. Telemetry data governance sign-off.
- **[SPE]:** AI Operations Lead & Privacy Officer.
- **[DEP]:** Approved telemetry schema filter specification.
- **[BLK]:** **YES**.

---

### D-16: Creation of a New Disposable Supabase-Compatible Test Environment
- **[REC]:** Provision fresh, isolated local Supabase CLI stack on loopback interface; enforce fail-closed connection guards on all test URLs; strictly prohibit cloud connections.
- **[EVI]:** `tests/config.py` loads `.env` targeting remote cloud Supabase; Step 2 vanilla PostgreSQL container lacked Supabase `auth` schemas.
- **[UNV]:** Local Supabase test stack not yet provisioned.
- **[PO]:** No.
- **[SPE]:** DevOps / Platform Engineer & Security Architect.
- **[DEP]:** Local Supabase Docker Compose manifest and teardown runbook.
- **[BLK]:** **YES**.

---

### D-17: Implementation Authorization and Separate Production Approval
- **[REC]:** Enforce strict 4-stage gate separation: Gate A (Design Approval) $\to$ Gate B (Test Implementation) $\to$ Gate C (Database Validation) $\to$ Production Approval.
- **[EVI]:** All audit reports record zero implementation authorization.
- **[UNV]:** N/A (governance control).
- **[PO]:** Yes. Formal delegation of authority sign-off.
- **[SPE]:** Lead System Architect.
- **[DEP]:** Written designation of accountable authorizers.
- **[BLK]:** **YES**.

---

### D-18: Application Identity Model and Supabase auth.uid() Boundary
- **[REC]:** Standardize on custom HMAC-signed application context (`public.current_app_user_id()`); deprecate and remove application dependencies on Supabase `auth.uid()`.
- **[EVI]:** FastAPI issues custom JWTs; migration 021 implements context functions.
- **[UNV]:** Live catalog unverified for lingering `auth.uid()` references.
- **[PO]:** No.
- **[SPE]:** Identity & Auth Architect.
- **[DEP]:** Architectural Decision Record (ADR) sign-off.
- **[BLK]:** **YES**.

---

### D-19: Visitor Token Lifetime and Anonymous Feedback
- **[REC]:** 32-byte visitor bearer token; 24-hour absolute non-sliding expiration; matching token required for chat feedback; adopt `v2` context payload binding `visitor_token_hash`.
- **[EVI]:** `chat.py` generates visitor tokens; migration 021 checks `app.chat_visitor_token` GUC.
- **[UNV]:** Live chat session rows and token expiration state unverified.
- **[PO]:** Yes. Student user experience policy sign-off.
- **[SPE]:** Application Security Engineer.
- **[DEP]:** Context payload `v2` specification.
- **[BLK]:** **YES**.

---

### D-20: Guest Support-Ticket Permissions
- **[REC]:** Guest support tickets are strictly create-only; zero database read/update/reply permissions; staff follow up exclusively via email.
- **[EVI]:** `support_service.py` allows unauthenticated creation; `SupportTicket` model permits nullable `user_id`.
- **[UNV]:** RLS policies on `support_tickets` unverified in live catalog.
- **[PO]:** Yes. Support workflow policy approval.
- **[SPE]:** Security Architect.
- **[DEP]:** Support workflow policy document.
- **[BLK]:** **YES**.

---

### D-21: College Chat Analytics and Raw Conversation Access
- **[REC]:** College Admins receive aggregate metrics only; zero direct browse access to raw student chat logs or transcripts unless escalated to a ticket.
- **[EVI]:** `analytics_service.py` provides aggregated queries; `college-admin/analytics/page.tsx` displays charts.
- **[UNV]:** Analytics views and RLS policies unverified in live catalog.
- **[PO]:** Yes. Student privacy policy approval.
- **[SPE]:** Data Privacy Officer.
- **[DEP]:** Analytics data governance policy document.
- **[BLK]:** **YES**.

---

### D-22: Sensitive User-Column Access and Authentication Lookup Contract
- **[REC]:** Enforce minimal 7-field projection via `public.lookup_user_by_email_for_auth(CAST(:email AS text))`; zero direct `SELECT` on `users.hashed_password` for runtime application roles; restrict function execution to authentication service role.
- **[EVI]:** Migration 022 implements 7-field projection; `UserRepository` executes function; test logs show `lookup_user_by_email_for_auth(unknown) does not exist`.
- **[UNV]:** Live database function existence, parameter types, return projection, and catalog grants remain unverified.
- **[PO]:** No.
- **[SPE]:** Application Security Engineer & Database Security Architect.
- **[DEP]:** Verification of function resolution on authorized test stack.
- **[BLK]:** **YES**.

---

## 15. Accountable-Owner and Specialist-Approval Matrix

```
+-----+-----------------------------------+------------------------+------------------------------------+-----------------------+
| ID  | Decision Focus Area               | Project Owner Approval | Specialist Domain Required         | Current Status        |
+-----+-----------------------------------+------------------------+------------------------------------+-----------------------+
| D-01| Migration History & Branch B      | REQUIRED               | Database Release Engineer          | PENDING HUMAN DECISION|
| D-02| Worker Process Isolation Model    | REQUIRED               | Security Architect & Systems Eng.  | PENDING HUMAN DECISION|
| D-03| Worker Claim Authentication       | NOT REQUIRED           | Database Security Architect        | PENDING HUMAN DECISION|
| D-04| Job Lease & Retry Thresholds      | REQUIRED               | Distributed Systems Engineer       | PENDING HUMAN DECISION|
| D-05| SECURITY DEFINER & search_path    | NOT REQUIRED           | PostgreSQL Security Architect      | PENDING HUMAN DECISION|
| D-06| Identity Layer Consumer Boundary  | NOT REQUIRED           | AppSec & Database Architect        | PENDING HUMAN DECISION|
| D-07| Direct-Login vs SET ROLE Testing  | NOT REQUIRED           | Security Test Engineer             | PENDING HUMAN DECISION|
| D-08| PG 17 Role Membership Closure     | NOT REQUIRED           | PostgreSQL Database Administrator  | PENDING HUMAN DECISION|
| D-09| Negative Principal Testing Tier   | NOT REQUIRED           | QA / Security Test Engineer        | PENDING HUMAN DECISION|
| D-10| Key Rotation & Dual Verification  | REQUIRED               | Key Management Specialist & AppSec | PENDING HUMAN DECISION|
| D-11| Password-Reset Email Deferral     | REQUIRED               | Communications Privacy Specialist  | PENDING HUMAN DECISION|
| D-12| Notification Data Retention Limit | REQUIRED               | Data Privacy & Compliance Officer  | PENDING HUMAN DECISION|
| D-13| College Registration Flow Boundary| REQUIRED               | Application Security Engineer      | PENDING HUMAN DECISION|
| D-14| Staff RBAC Matrix (Editor/Viewer) | REQUIRED               | Application Security Architect     | PENDING HUMAN DECISION|
| D-15| Audit & Telemetry Redaction Filter| REQUIRED               | AI Operations Lead & Privacy Off.  | PENDING HUMAN DECISION|
| D-16| Disposable Test Stack Isolation   | NOT REQUIRED           | DevOps / Platform Engineer         | PENDING HUMAN DECISION|
| D-17| Staged Gate Authorization Model   | REQUIRED               | Lead System Architect              | PENDING HUMAN DECISION|
| D-18| Application Identity Model        | NOT REQUIRED           | Identity & Auth Architect          | PENDING HUMAN DECISION|
| D-19| Visitor Token 24h Expiration      | REQUIRED               | Application Security Engineer      | PENDING HUMAN DECISION|
| D-20| Guest Support Ticket Create-Only  | REQUIRED               | Security Architect                 | PENDING HUMAN DECISION|
| D-21| Chat Analytics Aggregate-Only     | REQUIRED               | Data Privacy Officer               | PENDING HUMAN DECISION|
| D-22| Auth Lookup 7-Field Projection    | NOT REQUIRED           | AppSec & DB Security Architect     | PENDING HUMAN DECISION|
+-----+-----------------------------------+------------------------+------------------------------------+-----------------------+
```

---

## 16. Six Evidence-Package Status

```
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| #  | Evidence Package Name                                         | Status       | Detailed Status Assessment                            |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 1  | Migration History and Deployment Ledger                       | MISSING      | No signed deployment ledger or migration tracking     |
|    |                                                               |              | records exist for cloud/staging environments.          |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 2  | Key Management and Rotation Runbook                           | MISSING      | Operational runbook for KMS custody, dual-key         |
|    |                                                               |              | rotation, and secret generation is not authored.      |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 3  | Worker Authentication and Isolation Architecture              | INCOMPLETE   | Conceptual architecture defined in Step 6.2/6.3.2;    |
|    |                                                               |              | Celery queue routing and claim SQL remain unauthored. |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 4  | Data Retention and Privacy Schedule                           | MISSING      | Institutional policy document signed by DPO and PO    |
|    |                                                               |              | has not been submitted.                               |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 5  | Local Supabase-Compatible Disposable Stack Specification      | INCOMPLETE   | Guard rules and port specifications defined; Docker   |
|    |                                                               |              | Compose manifest and startup script not implemented.  |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 6  | Delegation of Authority and Approval Ownership Document       | MISSING      | Formal corporate delegation naming individual human   |
|    |                                                               |              | decision-makers is not recorded in repository.        |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
```

---

## 17. Gate A Readiness Checklist

To complete Gate A and enable subsequent implementation authorization (Gate B):

- [ ] **Documentary Evidence Packages:**
  - [ ] Package 1: Authoritative Migration History Ledger submitted.
  - [ ] Package 2: Key Management Runbook submitted.
  - [ ] Package 3: Worker Isolation Architecture Specification submitted.
  - [ ] Package 4: Data Retention & Privacy Schedule signed by DPO.
  - [ ] Package 5: Disposable Local Supabase Container Manifest submitted.
  - [ ] Package 6: Formal Delegation of Authority Document submitted.
- [ ] **Project Owner Approvals (13 Items):**
  - [ ] D-01 (Branch B Selection), D-02 (Worker Model), D-04 (Lease SLA), D-10 (Key Custody), D-11 (Password Reset Deferral), D-12 (30-day Retention), D-13 (Registration Review), D-14 (Staff RBAC), D-15 (Telemetry Redaction), D-17 (Staged Gates), D-19 (Visitor Token 24h Expiry), D-20 (Guest Ticket Create-Only), D-21 (Analytics Privacy).
- [ ] **Specialist Sign-Offs (13 Domains):**
  - [ ] Database Release Engineer, Database Security Architect, Distributed Systems Engineer, PostgreSQL Security Architect, Application Security Engineer, Security Test Engineer, PostgreSQL DBA, Key Management Specialist, Communications Privacy Specialist, Data Privacy Officer, DevOps Engineer, Lead System Architect, Identity Architect.
- [ ] **Gate A Formally Certified:** Written closure recorded in repository.

---

## 18. Unresolved Risks and Contradictions

1. **Migration State Ambiguity (D-01):** If the release owner cannot certify that migrations 001–022 were never applied in hosted Supabase, selecting Branch A would cause irreversible catalog corruption. Branch B remains the only safe operational position.
2. **Password Hash Retrieval Scope (D-22):** The function `public.lookup_user_by_email_for_auth(text)` returns `hashed_password` and is granted to `college_app_user`. Because `college_app_user` is the single shared application role, any web endpoint on the pool has access to execute the function. Resolving this requires architectural separation via a dedicated authentication connection pool role (`college_auth_user`).
3. **search_path in Migration 021 (D-05):** 9 `SECURITY DEFINER` functions in migration `021` retain `public` in their search path. If any unprivileged user or compromised role acquires `CREATE` privileges on schema `public`, operator-shadowing vulnerabilities become viable.
4. **Single Active Key Index (D-10):** Migration `021` lines 16–18 enforce `uq_rls_context_single_active_key`, preventing dual-key overlap during key rotation and causing in-flight requests to fail signature verification.
5. **Worker Tenant Assertion (D-03):** Background tasks currently rely on client-asserted `college_id` GUCs rather than database-enforced job claims, risking cross-tenant data corruption if a worker process is compromised.

---

## 19. Recommended Next Action

The technical documentation review, source reconciliation, and consistency audits are complete. All documentation-level discrepancies have been resolved.

**The recommended next action is:**
1. **Submit Review Package to Project Owner:** Deliver this Step 6.3.2 document alongside the Step 6 Decision Register to the Project Owner.
2. **Execute Formal Gate A Human Decision-Making:** Record formal written selections for the 13 Project Owner items and specialist sign-offs across all 13 technical domains.
3. **Compile the Six Missing Evidence Packages:** Request the accountable owners to author and submit the six missing documentary packages.
4. **Declare Gate A Complete:** Once all sign-offs and artifacts are archived, formally record Gate A as **COMPLETE**.
5. **Prepare Isolated Gate B Plan:** Following Gate A closure, formulate the isolated test implementation plan (Step 7) exclusively targeting the local disposable Supabase test stack.

---

## 20. Explicit Authorization Boundaries

```
================================================================================
EXPLICIT GOVERNANCE DECLARATION:
- ZERO IMPLEMENTATION IS AUTHORIZED BY THIS DOCUMENT.
- ZERO APPLICATION OR MIGRATION CODE WAS MODIFIED.
- ZERO DATABASE CONNECTIONS OR QUERIES WERE EXECUTED.
- ZERO REDIS CONNECTIONS OR MODIFICATIONS WERE PERFORMED.
- ZERO DOCKER CONTAINERS OR VOLUMES WERE ALTERED.
- GATE A REMAINS NOT COMPLETE (Awaiting Human Sign-Offs).
- GATE B REMAINS NOT AUTHORIZED (Implementation Prohibited).
- GATE C REMAINS NOT VALIDATED (Database Testing Prohibited).
- PRODUCTION DEPLOYMENT REMAINS NOT APPROVED.
================================================================================
```

---

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR FORMAL HUMAN GATE A DECISIONS
================================================================================
```

*Report compiled under strict read-only audit constraints. Zero application modifications, database queries, migration executions, or credential exposures were performed.*
