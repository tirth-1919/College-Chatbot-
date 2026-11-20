# Phase 3A.4.4B — Step 6.3.1: Final Technical Corrections Addendum

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Engineer, Independent Technical Auditor  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Predecessor Documents:**
- [Step 6 Human Decision Resolution Package](./phase3a4.4b-step6-human-decision-resolution.md)
- [Step 6.1 Technical Consistency & Auth Diagnostic](./phase3a4.4b-step6.1-technical-consistency-and-auth-diagnostic.md)
- [Step 6.2 Technical Findings Correction and Consolidation](./phase3a4.4b-step6.2-technical-findings-correction.md)
- [Step 6.3 Final Technical Consistency and Gate A Readiness Review](./phase3a4.4b-step6.3-final-technical-consistency-review.md)
**Deliverable Document:** `.agents/tasks/phase3a4.4b-step6.3.1-final-technical-corrections-addendum.md`

---

## 1. Executive Status

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR HUMAN DECISION — TECHNICAL CORRECTIONS CONSOLIDATED — NO IMPLEMENTATION AUTHORIZED
================================================================================
```

This addendum performs an independent, strictly read-only technical reconciliation and correction review of Step 6.3 and preceding planning documents. Its primary purpose is to eliminate remaining technical ambiguities, reconcile conflicting repository metrics, and formalize exact testing, identity, and isolation boundaries before the project enters formal human and specialist decision-making.

### Summary of Key Findings Reconciled in This Addendum

1. **SECURITY DEFINER Inventory Reconciled (D-05):** The conflicting counts of 12, 13, and 14 `SECURITY DEFINER` functions reported across prior documents are definitively resolved. Migration `021` defines exactly **13** `SECURITY DEFINER` functions (1 in `auth_private`, 12 in `public`). Migration `022` modifies and replaces **1** existing function (`public.lookup_user_by_email_for_auth`). There are **14 total definitions** in the migration files, resulting in **13 active functions** in a fully applied schema.
2. **Identity Layer Consumers Clarified (D-06 / D-18):** `session_user` is not prohibited or obsolete; it is the vital identity for connection authentication, connection pooling, and connection-level auditing. However, authorization must not confuse `session_user` with effective role identity (`current_user`) or tenant application context (`app.request_context`). Signed context does not replace table ACLs or Supabase engine privileges.
3. **Testing Architecture Disentangled (D-07):** Direct-login testing and `SET ROLE` testing validate entirely different system properties. Runtime capability roles (`college_app_user`, `college_worker_role`) remain `NOLOGIN`. A dedicated unprivileged login principal (`college_test_harness`) executes `SET ROLE` to evaluate effective ACLs and RLS without giving passwords to runtime roles.
4. **Independent Negative Testing Architecture (D-09):** A single role with zero table grants cannot test RLS policies, because PostgreSQL rejects access at the table ACL layer (`42501 permission denied`) before RLS is evaluated. Four distinct negative test fixtures are defined: ACL denial, RLS denial, Cross-tenant denial, and Privilege-escalation denial.
5. **Worker Authentication & Capability Roles (D-03):** The worker architecture is decoupled into: (a) Authenticated worker login principal, (b) `NOLOGIN` worker capability role, (c) Database-level job claim (`claim_job()`), (d) Cryptographic lease token, and (e) Verified tenant/resource binding.
6. **Strict Fail-Closed Connection Guard (D-16):** Every database connection URL (`DATABASE_URL`, `DATABASE_APP_ROLE_URL`, sync/async variants, Celery broker, and Celery result backend) must be independently validated against an explicit local configuration profile. URL scheme mutation (converting non-PostgreSQL schemes) is strictly rejected.
7. **Signing-Key Lifecycle & Cache Invalidation (D-10):** Dual-key overlap must account for application token TTLs and multi-instance cache propagation. Emergency revocation immediately marks a key `'REVOKED'` in the database, but does not alter currently running transactions until the next query statement or application cache refresh.
8. **Visitor-Token Layered Defense (D-19):** Visitor bearer capability, signed tenant context, and database ownership are decoupled. Context payload `v2` is proposed, but tenant isolation remains unverified until negative tests are run in an authorized isolated database.
9. **Authentication Lookup Projection (D-22):** `CAST(:email AS text)` addresses SQLAlchemy parameter typing ambiguity; it does not create a missing database function. The 7-column return projection includes sensitive `hashed_password`, requiring execution to be restricted exclusively to the authentication service role.
10. **Retention Approval Separated from Legal Rationale (D-12):** Correcting the statutory FERPA/GDPR narrative does not approve the 30-day retention schedule. D-12 remains unapproved pending explicit written sign-off from the Project Owner and Data Privacy Officer.

---

## 2. Scope and Read-Only Safety Declaration

In strict compliance with project safety directives, the following operational boundaries were maintained throughout this review:

1. **Zero Application Modifications:** No application source code in `backend/`, `apps/`, or `tests/` was altered.
2. **Zero SQL Modifications:** No SQL files, migration files, or DDL scripts in `database/` were edited.
3. **Zero SQL / Query Execution:** No SQL queries, DDL statements, migrations, or database commands were executed.
4. **Zero Database Connections:** No socket or TCP connection was opened to local PostgreSQL, Docker containers, or remote databases.
5. **Zero Cloud Access:** Hosted cloud Supabase infrastructure (`*.supabase.co`) was neither contacted nor probed.
6. **Zero Container / Volume Alterations:** No Docker containers, networks, or volumes were started, created, stopped, or pruned.
7. **Zero Configuration Changes:** `.env`, `.env.example`, and test configuration files remain unmodified.
8. **Zero Implementation Steps:** No proposed architectural change was implemented.
9. **Zero Automatic Approvals:** No decision in D-01 through D-22 was marked approved.
10. **Zero Gate Authorizations:** Gate B implementation and Gate C validation remain unauthorized.
11. **Static Inspection Only:** All findings and metrics are grounded solely in static file analysis and archived logs.
12. **Single Addendum Document:** Only `.agents/tasks/phase3a4.4b-step6.3.1-final-technical-corrections-addendum.md` was created.

---

## 3. D-05 through D-22 Technical Corrections

### 3.1 D-05: SECURITY DEFINER Inventory and search_path Vulnerability Distinction
- **Count Conflict Resolution:** Conflicting counts in prior reports (12, 13, and 14) arose from counting schemas separately, counting definitions vs. net functions, or overlooking public registration routines. The exact static inventory is established in Section 4 of this addendum.
- **Vulnerability vs. Exploit Distinction:** Migration `021` functions contain `SET search_path = pg_catalog, public, auth_private`. While `public` in the search path of a `SECURITY DEFINER` function is an unsafe configuration pattern (CWE-426), an actionable exploit requires `CREATE` privileges on schema `public`. In this codebase, migrations `018` and `020` execute `REVOKE CREATE ON SCHEMA public FROM PUBLIC`, and runtime role `college_app_user` possesses `USAGE` only. Therefore, this represents an unsafe defense-in-depth architectural vulnerability, not an actively exploitable remote execution path.

### 3.2 D-06 / D-18: Identity Boundaries and Consumer Classification
- **PostgreSQL `session_user`:** The authenticated physical connection user. Used for:
  - *Authentication:* Verified against database credentials by PostgreSQL connection listener.
  - *Connection Management:* Sized and pooled by PgBouncer and SQLAlchemy engine pools.
  - *Auditing:* Recorded in `pg_stat_activity` and server connection logs.
- **PostgreSQL `current_user` / `current_role`:** The effective role for SQL object permissions (table ACLs, view access). Temporarily switches upon `SET ROLE` or when entering `SECURITY DEFINER` routines.
- **Application JWT Identity:** Cryptographic token issued by FastAPI to HTTP clients, identifying the user (`sub`) and role claims.
- **HMAC-Signed Request Context:** Transaction-scoped PostgreSQL GUCs (`app.request_context_signature`, `app.current_college_id`) verified by PL/pgSQL `auth_private.is_request_context_valid()`. Used exclusively for multi-tenant row-level security (RLS).
- **Supabase `auth.uid()`:** Native Supabase Auth function reading JWT claims from PostgREST sessions. Unused and deprecated in this FastAPI-mediated architecture.
- **Boundary Rule:** Signed application context does **not** replace PostgreSQL role permissions. Even with valid signed context, a query fails if `current_user` lacks table-level `SELECT` or `UPDATE` grants.

### 3.3 D-07: Direct-Login versus SET ROLE Testing Architecture
- `SET ROLE target_role` alters `current_user` while preserving `session_user`.
- Production runtime capability roles (`college_app_user`, `college_worker_role`) are `NOLOGIN` capability roles. They cannot authenticate directly via TCP sockets.
- Direct-login tests validate connection authentication, initial role assignment, default search path, and pool cleanup.
- `SET ROLE` tests validate effective table privileges, column grants, and RLS policy execution under that role.
- Giving passwords to production capability roles just to run tests violates least privilege. Testing must use a dedicated login principal (`college_test_harness`) executing `SET ROLE`.

### 3.4 D-09: Multi-Tiered Independent Negative Testing
- A single test user with zero table grants cannot test RLS policies, because PostgreSQL terminates query execution at the table ACL check (`42501 permission denied`) before RLS is evaluated.
- Four distinct negative test cases are required:
  - *Tier A (ACL Denial):* Principal with zero table grants attempting access (verifies table privilege enforcement).
  - *Tier B (RLS Denial):* Principal with table grants but invalid or missing tenant signed context (verifies RLS blocks access when tenant context is absent).
  - *Tier C (Cross-Tenant Denial):* Principal with table grants and valid Tenant A signed context attempting to access Tenant B rows (verifies cross-tenant isolation).
  - *Tier D (Privilege-Escalation Denial):* Principal attempting unauthorized `SET ROLE`, `ALTER ROLE`, or execution of administrative definer routines (verifies role hierarchy security).

### 3.5 D-03: Worker Authentication and Capability Roles
- **Worker Login Principal:** Authenticated service account connecting to PostgreSQL via pooled credentials.
- **Worker Capability Role (`college_worker_role`):** `NOLOGIN` role holding table permissions for background tasks (documents, chunks, crawl jobs) but zero permissions on user passwords, auth keys, or billing.
- **Database Job Claim:** Atomic function call `claim_job(p_job_id, p_lease_duration)` that checks job availability and updates state inside a single transaction.
- **Lease Token:** Cryptographic hash issued upon claiming a job; subsequent task updates must supply this token to prove lease ownership.
- **Tenant/Resource Binding:** The claim function binds the worker session to the job's `college_id`, preventing the worker from operating on another tenant's documents.

### 3.6 D-16: Fail-Closed Test Environment Guard
- Validates every connection URL independently: `DATABASE_URL`, `DATABASE_APP_ROLE_URL`, sync/async derivatives, and Celery Redis URLs (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).
- Validates scheme, hostname, port, database name, and expected role.
- Prohibits string-munging non-PostgreSQL schemes into PostgreSQL URLs.
- Rejects cloud hosts, non-loopback addresses, and unexpected ports before socket creation.
- Rejects silent fallback to SQLite, memory databases, or production `.env`.

### 3.7 D-10: Signing-Key Lifecycle and Cache Invalidation
- Dual-key schema supports `ACTIVE` and `PREVIOUS` states with bounded overlap.
- Overlap window must be calibrated to maximum application token TTL + deployment rollout duration (minimum 15 minutes recommended for zero-downtime rolling deploys).
- Multi-instance deployments require cache invalidation: backend instances caching context keys in memory must subscribe to Redis key-rotation events or poll key state.
- Emergency revocation (`status = 'REVOKED'`) prevents new context validations. Note: revocation does not forcibly kill existing in-flight database transactions already executing inside a committed context check; it takes effect on the next statement or transaction boundary.

### 3.8 D-19: Visitor-Token Security Architecture
- Layer 1: Client presents bearer token (`secrets.token_urlsafe(32)`) to FastAPI.
- Layer 2: FastAPI validates pre-image against stored SHA-256 hash in `chat_sessions`.
- Layer 3: FastAPI sets signed tenant context binding `college_id`.
- Layer 4: Database RLS verifies tenant match and visitor hash.
- Proposed `v2` payload incorporates `visitor_token_hash` into HMAC signature.
- *Status:* Tenant isolation and visitor token security remain **UNVERIFIED** pending execution of negative test suites in an authorized test database.

### 3.9 D-22: Authentication Lookup Function Contract
- Query: `public.lookup_user_by_email_for_auth(CAST(:email AS text))`.
- Explicit ANSI `CAST` prevents SQLAlchemy parameter type ambiguity (`unknown`), but does not fix a missing catalog function.
- The 7-column return projection includes sensitive `hashed_password`.
- Execution must be restricted exclusively to the authentication service role; ordinary application roles must have `EXECUTE` revoked.
- Function existence, signature, and grants in the live database remain **UNVERIFIED**.

### 3.10 D-12: Retention Policy Approval vs. Legal Rationale
- Clarifying that FERPA does not mandate 30-day operational log purges and GDPR Article 5(1)(e) requires purpose-limited storage is a legal rationale correction.
- The actual 30-day retention schedule, scrubbing rules, and automated purge tasks remain **UNAPPROVED**.
- Requires formal written sign-off from the Project Owner and Data Privacy Officer before Gate A can close.

---

## 4. Exact SECURITY DEFINER Function Inventory and Count Reconciliation

### 4.1 Definitive Static Function Inventory

Every `SECURITY DEFINER` function in `database/migrations/` was statically analyzed. All definitions occur exclusively in migrations `021_phase3a42_security_onboarding.sql` and `022_minimize_auth_lookup.sql`:

```
+----+---------------------------------------------------------------+--------------+-------+--------------------+---------------------------------+---------------------+-----------------------+
| #  | Schema & Function Signature                                   | Return Type  | Migr. | Action in Migr.    | search_path                     | PUBLIC Revoked?     | Role Grants           |
+----+---------------------------------------------------------------+--------------+-------+--------------------+---------------------------------+---------------------+-----------------------+
| 1  | auth_private.is_request_context_valid()                       | boolean      | 021   | CREATE NEW         | pg_catalog, auth_private        | Yes (PUBLIC, app)   | None (Internal only)  |
| 2  | public.current_app_user_id()                                  | uuid         | 021   | CREATE NEW         | pg_catalog, auth_private        | Yes (PUBLIC)        | college_app_user      |
| 3  | public.current_app_tenant()                                   | uuid         | 021   | CREATE NEW         | pg_catalog, auth_private        | Yes (PUBLIC)        | college_app_user      |
| 4  | public.is_platform_super_admin()                              | boolean      | 021   | CREATE NEW         | pg_catalog, auth_private        | Yes (PUBLIC)        | college_app_user      |
| 5  | public.is_current_college_admin()                             | boolean      | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 6  | public.user_belongs_to_tenant(uuid, uuid)                     | boolean      | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 7  | public.lookup_user_by_email_for_auth(text)                    | SETOF users  | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 8  | public.lookup_college_invitation_by_token(text)               | TABLE(...)   | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 9  | public.accept_college_admin_invitation(text, text, text, uuid)| TABLE(...)   | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 10 | public.submit_public_college_registration(jsonb)              | TABLE(...)   | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 11 | public.check_public_registration_availability(text, text)     | boolean      | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 12 | public.get_public_registration_status(text)                   | jsonb        | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 13 | public.submit_public_registration_information(text, txt, jsb) | jsonb        | 021   | CREATE NEW         | pg_catalog, public, auth_priv   | Yes (PUBLIC)        | college_app_user      |
| 14 | public.lookup_user_by_email_for_auth(text)                    | TABLE(7 col) | 022   | REPLACES ENTRY #7  | pg_catalog                      | Yes (PUBLIC)        | college_app_user      |
+----+---------------------------------------------------------------+--------------+-------+--------------------+---------------------------------+---------------------+-----------------------+
```

### 4.2 Reconciliation of Reported Counts (12, 13, and 14)

Prior reports referenced conflicting counts. The exact reconciliation is as follows:
- **Count = 14:** The total number of `CREATE [OR REPLACE] FUNCTION ... SECURITY DEFINER` statements written across repository migration files (13 statements in `021` + 1 statement in `022`).
- **Count = 13 (Net Active Functions):** The total number of distinct `SECURITY DEFINER` functions that exist in the PostgreSQL catalog after migrations `021` and `022` are applied sequentially. Function #14 in migration `022` executes `DROP FUNCTION` on Function #7 from migration `021` and recreates it with a 7-column projection, leaving exactly 13 active functions (1 in `auth_private`, 12 in `public`).
- **Count = 12:** The number of `SECURITY DEFINER` functions located strictly within the `public` schema in migration `021` (excluding `auth_private.is_request_context_valid()`), or the number of functions in migration `021` that remain untouched after migration `022` modifies `lookup_user_by_email_for_auth`.

### 4.3 Static Ownership & Privilege Observations
- **Ownership:** In migration `021`, no `ALTER FUNCTION ... OWNER TO` is executed. In PostgreSQL, function ownership defaults to the role running the migration. In migration `022`, lines 9–13 inspect `pg_proc.proowner` of the existing function and reassign ownership to that same role (`v_function_owner`). If migrations are run by a superuser (`postgres` or `supabase_admin`), all 13 functions are owned by a superuser, allowing them to bypass RLS.
- **Live Database Status:** Live catalog ownership, existence, and function OIDs remain **UNVERIFIED** pending authorized testing in a local disposable stack.

---

## 5. Corrected Identity and Testing Architecture

### 5.1 Identity Boundary Model

```
+--------------------------------------------------------------------------------------------------------------------+
| IDENTITY BOUNDARY SPECIFICATION                                                                                    |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Identity Primitive       | Context Scope         | Consumed By                 | Classification                    |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| session_user             | TCP Physical Session  | Connection pooling, PgBouncer| Authentication, Connection Mgmt,  |
|                          |                       | pg_stat_activity, pgaudit   | Audit logging                     |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| current_user             | Transaction / Routine | SQL object privilege checks | Authorization (Table ACLs, DDL)   |
|                          | (Switches on SET ROLE)| (pg_class, pg_proc grants)  |                                   |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Application JWT          | HTTP Request          | FastAPI dependencies        | Client Authentication & RBAC      |
|                          |                       | (get_current_user)          |                                   |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Signed Request Context   | Database Transaction  | PL/pgSQL RLS helpers        | Row-Level Multi-Tenant Isolation  |
| (app.request_context)    | (set_config is_local) | (current_app_tenant)        |                                   |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Supabase auth.uid()      | PostgREST (Native)    | DEPRECATED / UNUSED         | Legacy Supabase Auth Boundary     |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
```

### 5.2 Corrected Testing Principal Architecture

To test the application without compromising least privilege:
1. **Production Capability Roles Remain NOLOGIN:** `college_app_user` and `college_worker_role` must not have passwords or `LOGIN` privileges.
2. **Dedicated Test Connection Principal (`college_test_harness`):**
   - Has `LOGIN` and `NOINHERIT`.
   - Granted membership with `SET-only` privilege: `GRANT college_app_user TO college_test_harness WITH INHERIT FALSE, SET TRUE;`.
   - Connects to the test database and executes `SET ROLE college_app_user;` to evaluate effective ACLs and RLS.
3. **Dedicated Negative Test Principal (`college_test_unprivileged`):**
   - Has `LOGIN` and `NOINHERIT`.
   - Zero memberships in application roles.
   - Zero table grants on application tables.
4. **Testing Matrix:**
   - *Direct-Login Testing:* Required solely for `college_test_harness` and `college_test_unprivileged` to test connection acceptance, password authentication, and search-path assignment.
   - *SET ROLE Testing:* Required for testing `college_app_user` and `college_worker_role` table privileges, column restrictions, and RLS policies.

### 5.3 Independent Negative Testing Matrix

```
+--------------------------+----------------------------+-----------------------------+--------------------------------------+
| Test Tier                | Test Principal             | Database Context            | Expected Result                      |
+--------------------------+----------------------------+-----------------------------+--------------------------------------+
| Tier A: ACL Denial       | college_test_unprivileged  | None                        | ERROR 42501 (permission denied for   |
|                          | (Zero table grants)        |                             | relation users / chat_sessions)      |
+--------------------------+----------------------------+-----------------------------+--------------------------------------+
| Tier B: RLS Denial       | college_test_harness       | None (or invalid HMAC       | 0 rows returned on SELECT;           |
|                          | (SET ROLE college_app_user)| context signature)          | ERROR on INSERT/UPDATE/DELETE        |
+--------------------------+----------------------------+-----------------------------+--------------------------------------+
| Tier C: Cross-Tenant     | college_test_harness       | Valid context signed for    | 0 rows returned for Tenant B data;   |
|         Denial           | (SET ROLE college_app_user)| Tenant A (AIT)              | Tenant B records completely invisible|
+--------------------------+----------------------------+-----------------------------+--------------------------------------+
| Tier D: Privilege        | college_test_harness       | SET ROLE college_app_user;  | ERROR 42501 (permission denied to    |
|         Escalation       | (SET ROLE college_app_user)| SET ROLE postgres;          | set role "postgres")                 |
+--------------------------+----------------------------+-----------------------------+--------------------------------------+
```

---

## 6. Corrected Test-Environment Isolation Specification

### 6.1 Connection Guard Specification (D-16)

The test connection guard must validate all connection strings prior to engine initialization:

```
+--------------------------------------------------------------------------------------------------------------------+
| FAIL-CLOSED TEST CONNECTION GUARD RULES                                                                            |
+--------------------------------------------------------------------------------------------------------------------+
| 1. Independent URL Validation:                                                                                     |
|    - Validate DATABASE_URL, DATABASE_APP_ROLE_URL, ASYNC_APP_URL, ASYNC_ADMIN_URL, SYNC_ADMIN_URL, SYNC_APP_URL.     |
| 2. Scheme Enforcement:                                                                                             |
|    - Reject any non-PostgreSQL scheme (e.g., sqlite://, mysql://). Do not mutate or convert unsupported schemes.  |
|    - Accept only "postgresql://" or "postgresql+asyncpg://".                                                       |
| 3. Hostname Restriction:                                                                                           |
|    - Must parse strictly to "127.0.0.1", "localhost", or "::1".                                                    |
|    - Reject public IPs, 0.0.0.0, LAN addresses, and any domain matching *.supabase.co, *.supabase.in, *.aws.com.    |
| 4. Port Validation:                                                                                                |
|    - Port must match the explicit local disposable test stack port configured in test profile (e.g., 54322).        |
| 5. Database Name Validation:                                                                                       |
|    - Database name must match designated isolated test database (e.g., "postgres_test" or "test_db").             |
|    - Prohibit connecting to default production database names without test suffix.                                 |
| 6. Celery / Redis URL Validation:                                                                                  |
|    - Validate CELERY_BROKER_URL and CELERY_RESULT_BACKEND independently.                                           |
|    - Must parse to "redis://127.0.0.1:6379/<db>" or "redis://localhost:6379/<db>".                                 |
|    - Broker and backend must use isolated test database indices (e.g., /14 and /15).                              |
| 7. Execution Action:                                                                                               |
|    - On any validation failure, abort test run immediately via sys.exit(1). Never fall back silently.             |
+--------------------------------------------------------------------------------------------------------------------+
```

*Note: In accordance with safety restrictions, this guard is specified for design approval; it has not been implemented in repository code.*

---

## 7. Corrected D-01 through D-22 Decision Register

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
- **[EVI]:** 13 active functions across migrations 021 and 022; 10 functions in 021 set `search_path = pg_catalog, public, auth_private`; 022 sets `pg_catalog`.
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

## 8. Outstanding Evidence and Specialist Approvals

### 8.1 Required Documentary Evidence Pending Submission
1. **Authoritative Migration Ledger (D-01):** Certified deployment record documenting whether migrations 001–022 were ever executed in any cloud, staging, or production instance.
2. **Worker Deployment Architecture Specification (D-02, D-03, D-04):** Formal specification of Celery queue routing, process isolation, and database capability role credentials.
3. **Key Management Runbook (D-10):** Operational runbook defining secret generation, KMS custody, multi-instance cache invalidation, and rotation procedures.
4. **Data Retention & Sanitization Policy (D-12, D-15, D-21):** Formal institutional policy signed by the Data Privacy Officer governing log retention, telemetry filtering, and student chat privacy.
5. **Local Disposable Supabase Environment Specification (D-16):** Docker Compose manifest and verification script for the local loopback test container stack.
6. **Delegation of Authority Document (D-17):** Formal corporate designation identifying the named individuals authorized to sign Gate A, Gate B, Gate C, and production release.

### 8.2 Specialist Sign-Off Roster

```
+------------------------------------+-----------------------------+-----------------------+
| Specialist Domain                  | Decision IDs Evaluated      | Sign-Off Status       |
+------------------------------------+-----------------------------+-----------------------+
| Database Release Engineer          | D-01                        | PENDING SIGN-OFF      |
| Database Security Architect        | D-03, D-05, D-06, D-22      | PENDING SIGN-OFF      |
| Distributed Systems Engineer       | D-04                        | PENDING SIGN-OFF      |
| PostgreSQL Security Architect      | D-05, D-08                  | PENDING SIGN-OFF      |
| Application Security Engineer      | D-06, D-13, D-14, D-19, D-22| PENDING SIGN-OFF      |
| Security Test Engineer             | D-07, D-09                  | PENDING SIGN-OFF      |
| PostgreSQL Database Administrator  | D-08                        | PENDING SIGN-OFF      |
| Key Management Specialist          | D-10                        | PENDING SIGN-OFF      |
| Communications Privacy Specialist  | D-11                        | PENDING SIGN-OFF      |
| Data Privacy & Compliance Officer  | D-12, D-15, D-21            | PENDING SIGN-OFF      |
| DevOps / Platform Engineer         | D-16                        | PENDING SIGN-OFF      |
| Lead System Architect              | D-17                        | PENDING SIGN-OFF      |
| Identity & Auth Architect          | D-18                        | PENDING SIGN-OFF      |
+------------------------------------+-----------------------------+-----------------------+
```

---

## 9. Gate A Readiness Checklist

To complete Gate A and transition the project to implementation planning, the following checklist must be fully executed:

- [ ] **Project Owner Written Selections Recorded:**
  - [ ] D-01: Migration history Branch B adoption.
  - [ ] D-02: Worker isolation architecture selection.
  - [ ] D-04: Job lease and retry thresholds approval.
  - [ ] D-10: Context key custody and rotation policy sign-off.
  - [ ] D-11: Password-reset deferral decision.
  - [ ] D-12: Notification data retention policy (30-day schedule).
  - [ ] D-13: College registration workflow approval.
  - [ ] D-14: Staff dashboard RBAC matrix approval.
  - [ ] D-15: AI telemetry redaction allowlist sign-off.
  - [ ] D-17: Staged gate authorization policy sign-off.
  - [ ] D-19: Visitor token 24-hour expiration policy approval.
  - [ ] D-20: Guest support ticket create-only policy approval.
  - [ ] D-21: College chat analytics aggregate-only privacy approval.
- [ ] **Technical Specialist Sign-Offs Collected:**
  - [ ] All 13 designated technical specialist domains reviewed and signed.
- [ ] **Documentary Evidence Archived:**
  - [ ] All 6 required documentary artifacts archived in `.agents/tasks/evidence/`.
- [ ] **Formal Gate A Closure:**
  - [ ] Gate A formally marked **COMPLETE** in project register.

---

## 10. Gate B, Gate C, and Production Authorization Status

```
+--------------------------------------------------------------------------------------------------+
| GATE B: IMPLEMENTATION AUTHORIZATION                                                             |
| Status: NOT AUTHORIZED                                                                           |
| Rationale: Implementation is strictly prohibited until Gate A is formally completed and signed.  |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| GATE C: ISOLATED DATABASE AND SECURITY VALIDATION                                                |
| Status: NOT VALIDATED                                                                            |
| Rationale: No migrations, schema checks, or tests have been executed on an authorized local      |
|            disposable Supabase stack.                                                            |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| PRODUCTION DEPLOYMENT APPROVAL                                                                   |
| Status: NOT APPROVED                                                                             |
| Rationale: Production release remains strictly prohibited. Gate B and Gate C validation do not    |
|            confer production release authorization.                                              |
+--------------------------------------------------------------------------------------------------+
```

---

## 11. Final Next Actions

1. **Submit Review Package to Project Owner:** Deliver this Addendum (`phase3a4.4b-step6.3.1-final-technical-corrections-addendum.md`) alongside Step 6.3 and the Step 6 Decision Register to the Project Owner.
2. **Collect Human Sign-Offs:** Gather formal written decisions on the 13 Project Owner items and specialist signatures across all technical domains.
3. **Declare Gate A Complete:** Once all sign-offs and missing documentary artifacts are archived, formally mark Gate A as Complete.
4. **Draft Gate B Implementation Authorization Request:** Prepare the isolated test implementation plan for execution exclusively inside an authorized local disposable Supabase container equipped with fail-closed URL guards.

---

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR HUMAN DECISION — TECHNICAL CORRECTIONS CONSOLIDATED — NO IMPLEMENTATION AUTHORIZED
================================================================================
```

*Report compiled under strict read-only audit constraints. Zero application modifications, database queries, migration executions, or credential exposures were performed.*
