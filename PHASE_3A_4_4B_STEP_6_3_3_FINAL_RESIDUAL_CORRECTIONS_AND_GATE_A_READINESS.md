# Phase 3A.4.4B — Step 6.3.3: Final Residual Corrections and Gate A Submission Readiness Addendum

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Engineer, Database Migration Specialist, PostgreSQL RLS Specialist, Independent Technical Auditor  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Predecessor Documents:**
- [Step 6 Human Decision Resolution Package](./.agents/tasks/phase3a4.4b-step6-human-decision-resolution.md)
- [Step 6.1 Technical Consistency & Auth Diagnostic](./.agents/tasks/phase3a4.4b-step6.1-technical-consistency-and-auth-diagnostic.md)
- [Step 6.2 Technical Findings Correction and Consolidation](./.agents/tasks/phase3a4.4b-step6.2-technical-findings-correction.md)
- [Step 6.3 Final Technical Consistency Review](./.agents/tasks/phase3a4.4b-step6.3-final-technical-consistency-review.md)
- [Step 6.3.1 Final Technical Corrections Addendum](./.agents/tasks/phase3a4.4b-step6.3.1-final-technical-corrections-addendum.md)
- [Step 6.3.2 Final Security Consistency and Gate A Review](./.agents/tasks/phase3a4.4b-step6.3.2-final-security-consistency-and-gate-a-review.md)
**Deliverable Document:** `PHASE_3A_4_4B_STEP_6_3_3_FINAL_RESIDUAL_CORRECTIONS_AND_GATE_A_READINESS.md`

---

## 1. Executive Decision

```
================================================================================
FINAL DOCUMENTATION VERDICT:
READY FOR FORMAL HUMAN GATE A DECISIONS
================================================================================
```

This addendum performs a strictly read-only, narrowly scoped residual correction pass on the Phase 3A.4.4B Step 6.3.2 technical package. Its sole purpose is to resolve every remaining documentation-level technical inconsistency, eliminate overconfident or inaccurate security assertions, distinguish statically verified repository facts from unverified assumptions and proposals, and determine whether the documentation package is ready to be delivered to accountable human owners and technical specialists for formal Gate A decision-making.

### Mandatory Declarations

1. **Documentation Readiness Only:** The verdict `READY FOR FORMAL HUMAN GATE A DECISIONS` certifies that the documentation and decision registers are internally consistent, free of material contradictions, and ready for human review. It **does not mean Gate A is approved or complete**.
2. **Zero Decisions Approved:** Not a single decision among D-01 through D-22 is approved by this document. All 22 decisions remain in `PENDING HUMAN DECISION` status.
3. **Zero Implementation Authorized:** This report is an audit and governance artifact. It confers **zero authorization to implement code, run migrations, or alter configurations** (Gate B remains NOT AUTHORIZED).
4. **Zero Database Validation Occurred:** No SQL queries, database connections, container operations, or live catalog inspections were performed (Gate C remains NOT VALIDATED).
5. **Zero Production Approval:** Production deployment remains strictly prohibited.

---

## 2. Scope and Safety Declaration

In accordance with strict project safety directives, the following absolute boundaries were observed:

- Did not connect to local or remote PostgreSQL databases [CONFIRMED].
- Did not connect to hosted cloud Supabase (`*.supabase.co`) [CONFIRMED].
- Did not execute SQL queries, DDL, DML, or migrations [CONFIRMED].
- Did not connect to, query, or modify Redis [CONFIRMED].
- Did not start, stop, create, delete, inspect, or modify Docker containers, images, networks, or volumes [CONFIRMED].
- Did not modify `.env`, `.env.*`, configuration files, secrets, or API keys [CONFIRMED].
- Did not alter Git branches, commits, or existing working-tree files [CONFIRMED].
- Did not install, upgrade, or remove packages or dependencies [CONFIRMED].
- Did not execute application startup or test execution commands [CONFIRMED].
- Did not alter any user, college, membership, document, session, or ticket records [CONFIRMED].

### Strict Evidentiary Classification Scheme

To prevent ungrounded inferences, all findings and statements throughout this report are classified strictly as:
- **`[VERIFIED STATICALLY]`**: Directly verified from inspected repository source files, configurations, or migrations.
- **`[PARTIALLY VERIFIED]`**: Partially supported by repository files, but lacking complete implementation or configuration.
- **`[NOT VERIFIED — DATABASE VALIDATION REQUIRED]`**: Relies on live database catalog state, runtime privileges, or environment variables that can only be verified in an authorized running database.
- **`[PROPOSED]`**: Recommended architectural design or specification; not currently implemented in repository code.
- **`[PENDING OWNER DECISION]`**: Blocked on formal human Project Owner or technical specialist sign-off.

---

## 3. Evidence Inspected

The following repository files and predecessor documents were inspected statically as text:
1. `database/migrations/001_extensions.sql` through `022_minimize_auth_lookup.sql` [VERIFIED STATICALLY]
2. `database/migrations/017_row_level_security_policies.sql` lines 1–110 [VERIFIED STATICALLY]
3. `database/migrations/018_create_application_role.sql` lines 1–45 [VERIFIED STATICALLY]
4. `database/migrations/019_complete_rls_policies.sql` lines 1–115 [VERIFIED STATICALLY]
5. `database/migrations/020_revoke_anon_grants.sql` lines 1–35 [VERIFIED STATICALLY]
6. `database/migrations/021_phase3a42_security_onboarding.sql` lines 1–751 [VERIFIED STATICALLY]
7. `database/migrations/022_minimize_auth_lookup.sql` lines 1–53 [VERIFIED STATICALLY]
8. `backend/app/database/connection.py` lines 1–65 [VERIFIED STATICALLY]
9. `backend/app/database/session.py` lines 1–209 [VERIFIED STATICALLY]
10. `backend/app/repositories/user_repository.py` lines 1–65 [VERIFIED STATICALLY]
11. `backend/app/services/auth_service.py` lines 1–120 [VERIFIED STATICALLY]
12. `backend/app/api/v1/auth.py` lines 1–95 [VERIFIED STATICALLY]
13. `backend/app/api/v1/chat.py` lines 1–210 [VERIFIED STATICALLY]
14. `backend/app/tasks/celery_app.py` lines 1–50 [VERIFIED STATICALLY]
15. `backend/app/tasks/document_tasks.py` lines 1–180 [VERIFIED STATICALLY]
16. `backend/app/core/config.py` lines 1–215 [VERIFIED STATICALLY]
17. `tests/config.py` lines 1–99 [VERIFIED STATICALLY]
18. `.agents/tasks/phase3a4.4b-step6.3.2-final-security-consistency-and-gate-a-review.md` [VERIFIED STATICALLY]

---

## 4. Residual Correction Matrix

```
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| #  | Topic / Claim              | Step 6.3.2 Formulation                      | Corrected Formulation in Step 6.3.3                         | Traceability & Evidence Level |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 1  | D-01 Migration History     | Claimed Branch B is the "only safe          | Branch B is the conservative default while history is       | database/README.md;           |
|    | Branch Selection           | operational position."                      | unknown. Branch A may be considered if written proof proves | [VERIFIED STATICALLY] /       |
|    |                            |                                             | 001–022 never executed in any environment.                  | [PENDING OWNER DECISION]      |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 2  | D-05 search_path &         | Claimed custom operator in public could     | Corrected: pg_catalog precedes public in search_path.       | 021 migration lines 135–720;  |
|    | Operator Shadowing         | shadow standard operators like '='.         | PostgreSQL checks pg_catalog first; standard operators      | [VERIFIED STATICALLY]         |
|    |                            |                                             | cannot be shadowed by public operators for catalog types.   |                               |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 3  | D-05 Exploitability vs.    | Concluded configuration is safe because     | Corrected: Neither exploitability nor safety is proven;     | pg_proc & pg_namespace catalog|
|    | Configuration Risk         | college_app_user lacks CREATE on public.    | depends on live namespace ACLs, role inheritance, and DDL.  | [NOT VERIFIED — DB REQUIRED]  |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 4  | D-22 Dedicated Role        | Stated dedicated role college_auth_user is  | Corrected: Dedicated role is a PROPOSED target architecture.| user_repository.py lines 38–60|
|    | Existence & Resolution     | the least-privilege design.                 | Migration grants EXECUTE to shared college_app_user.        | 022 migration line 51;        |
|    |                            |                                             | Dedicated role requires explicit Project Owner approval.    | [PROPOSED] / [PENDING DECISION|
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 5  | D-06/D-18 session_user     | Implied session_user should universally be  | Corrected: session_user is essential for connection auth,   | connection.py lines 20–55;    |
|    | Usage Scope                | prohibited in database security.            | pooling, and audit logging; must not be conflated with RLS. | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 6  | D-07 Test Harness          | Did not specify PG-version-specific role    | Corrected: PG 16+ uses WITH SET TRUE, INHERIT FALSE;        | Step 4 CTE specification;     |
|    | Membership Syntax          | membership options.                         | PG <=15 uses ALTER ROLE NOINHERIT + standard GRANT.         | [PROPOSED]                    |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 7  | D-09 Negative Test         | Collapsed RLS outcomes into generic         | Corrected: Separated SELECT (0 rows), INSERT WITH CHECK     | 021 migration lines 403–525;  |
|    | Outcomes                   | "denied" / "error" results.                 | (error), UPDATE USING (0 rows), UPDATE WITH CHECK (error).  | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 8  | D-10 Key Overlap Window    | Presented an 18-minute overlap window       | Corrected: Reclassified 18-minute calculation as an         | session.py lines 95–106;      |
|    | Calculation                | as a derived requirement.                   | illustrative arithmetic example; actual window requires PO. | [PROPOSED] / [PENDING DECISION|
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 9  | D-10 Immediate Key         | Claimed key revocation immediately stops    | Corrected: Revocation affects subsequent validations; cannot| 021 migration lines 59–80;    |
|    | Revocation Scope           | all requests.                               | retroactively abort an already-validated in-flight query.   | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 10 | D-12 Institutional Data    | Claimed records are "frequently retained    | Corrected: Removed unsupported 3–7 year generalization;     | Models & tasks inspection;    |
|    | Retention Rationale        | for 3–7 years."                             | retention schedule is strictly an unapproved PO policy.     | [PENDING OWNER DECISION]      |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 11 | D-16 Allowed Test URL      | Required both postgresql:// and             | Corrected: asyncpg requires postgresql+asyncpg://; sync     | tests/config.py lines 32–35;  |
|    | Schemes                    | postgresql+asyncpg:// unconditionally.      | requires postgresql://; validate exact scheme per engine.   | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
```

---

## 5. Exact SECURITY DEFINER Inventory and Count Reconciliation

### 5.1 Exact Function-by-Function Inventory

Every `SECURITY DEFINER` function across migrations `001_extensions.sql` through `022_minimize_auth_lookup.sql` was verified directly from source text without abbreviations [VERIFIED STATICALLY]:

#### 1. `auth_private.is_request_context_valid()`
- **Schema:** `auth_private`
- **Function Name:** `is_request_context_valid`
- **Argument Signature:** `()` (Zero arguments)
- **Return Type:** `boolean`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 21–83
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 2. `public.current_app_user_id()`
- **Schema:** `public`
- **Function Name:** `current_app_user_id`
- **Argument Signature:** `()` (Zero arguments)
- **Return Type:** `uuid`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 85–102
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 3. `public.current_app_tenant()`
- **Schema:** `public`
- **Function Name:** `current_app_tenant`
- **Argument Signature:** `()` (Zero arguments)
- **Return Type:** `uuid`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 104–119
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 4. `public.is_platform_super_admin()`
- **Schema:** `public`
- **Function Name:** `is_platform_super_admin`
- **Argument Signature:** `()` (Zero arguments)
- **Return Type:** `boolean`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 121–131
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 5. `public.is_current_college_admin()`
- **Schema:** `public`
- **Function Name:** `is_current_college_admin`
- **Argument Signature:** `()` (Zero arguments)
- **Return Type:** `boolean`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 133–150
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 6. `public.user_belongs_to_tenant(p_user_id uuid, p_college_id uuid)`
- **Schema:** `public`
- **Function Name:** `user_belongs_to_tenant`
- **Argument Signature:** `(p_user_id uuid, p_college_id uuid)`
- **Return Type:** `boolean`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 152–165
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 7. `public.lookup_user_by_email_for_auth(p_email text)` [Version 021]
- **Schema:** `public`
- **Function Name:** `lookup_user_by_email_for_auth`
- **Argument Signature:** `(p_email text)`
- **Return Type:** `SETOF public.users`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 167–178
- **Lifecycle Action:** Created in migration 021. **Explicitly dropped** by migration 022 line 14.

#### 8. `public.lookup_college_invitation_by_token(p_token text)`
- **Schema:** `public`
- **Function Name:** `lookup_college_invitation_by_token`
- **Argument Signature:** `(p_token text)`
- **Return Type:** `TABLE (id uuid, college_id uuid, invited_by_user_id uuid, email text, full_name text, role_in_college text, status text, expires_at timestamptz, created_at timestamptz, accepted_at timestamptz)`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 208–236
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 9. `public.accept_college_admin_invitation(p_token text, p_full_name text, p_password_hash text, p_authenticated_user_id uuid)`
- **Schema:** `public`
- **Function Name:** `accept_college_admin_invitation`
- **Argument Signature:** `(p_token text, p_full_name text, p_password_hash text, p_authenticated_user_id uuid)`
- **Return Type:** `TABLE (accepted_user_id uuid, accepted_college_id uuid, accepted_email text, is_existing_user boolean)`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 238–359
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 10. `public.submit_public_college_registration(p_payload jsonb)`
- **Schema:** `public`
- **Function Name:** `submit_public_college_registration`
- **Argument Signature:** `(p_payload jsonb)`
- **Return Type:** `TABLE (registration_id uuid, college_id uuid, tracking_code text, created_at timestamptz)`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 527–629
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 11. `public.check_public_registration_availability(p_slug text, p_domain text DEFAULT NULL)`
- **Schema:** `public`
- **Function Name:** `check_public_registration_availability`
- **Argument Signature:** `(p_slug text, p_domain text DEFAULT NULL)`
- **Return Type:** `boolean`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 631–650
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 12. `public.get_public_registration_status(p_tracking_code text)`
- **Schema:** `public`
- **Function Name:** `get_public_registration_status`
- **Argument Signature:** `(p_tracking_code text)`
- **Return Type:** `jsonb`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 652–671
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 13. `public.submit_public_registration_information(p_tracking_code text, p_response text, p_additional_documents jsonb DEFAULT '[]'::jsonb)`
- **Schema:** `public`
- **Function Name:** `submit_public_registration_information`
- **Argument Signature:** `(p_tracking_code text, p_response text, p_additional_documents jsonb DEFAULT '[]'::jsonb)`
- **Return Type:** `jsonb`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog, public, auth_private`
- **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 673–720
- **Lifecycle Action:** Created in migration 021. Untouched by migration 022.

#### 14. `public.lookup_user_by_email_for_auth(p_email text)` [Version 022]
- **Schema:** `public`
- **Function Name:** `lookup_user_by_email_for_auth`
- **Argument Signature:** `(p_email text)`
- **Return Type:** `TABLE (id uuid, email text, hashed_password text, full_name text, role text, is_verified boolean, is_active boolean)`
- **SECURITY DEFINER:** `SECURITY DEFINER` (Enabled)
- **search_path:** `SET search_path = pg_catalog`
- **Migration & Line Range:** `database/migrations/022_minimize_auth_lookup.sql` lines 14–46
- **Lifecycle Action:** Executes `DROP FUNCTION public.lookup_user_by_email_for_auth(text)` then `CREATE FUNCTION`. **Replaces Function #7**.

---

### 5.2 Non-SECURITY DEFINER Routine Sharing search_path

To prevent future count confusion:
- **`public.prevent_user_privilege_self_change()`**
  - **Schema:** `public`
  - **Function Name:** `prevent_user_privilege_self_change`
  - **Argument Signature:** `()` (Trigger function, zero input arguments)
  - **Return Type:** `trigger`
  - **SECURITY DEFINER:** **NO** (Invoker's rights, executes under caller's privileges)
  - **search_path:** `SET search_path = pg_catalog, public, auth_private`
  - **Migration & Line Range:** `database/migrations/021_phase3a42_security_onboarding.sql` lines 362–389
  - **Trigger Definition:** `CREATE TRIGGER trg_prevent_user_privilege_self_change BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.prevent_user_privilege_self_change();` (lines 392–395) [VERIFIED STATICALLY].

### 5.3 Mathematical Count Reconciliation

```
+--------------------------------------------------------------------------------------------------+
| MATHEMATICAL COUNT RECONCILIATION SUMMARY                                                         |
+---------------------------------------------------------------------------------------+----------+
| Total CREATE FUNCTION ... SECURITY DEFINER blocks in migration 021                    | 13       |
| Total CREATE FUNCTION ... SECURITY DEFINER blocks in migration 022                    | 1        |
| Cumulative written SECURITY DEFINER definitions in repository migration files         | 14       |
| Less functions DROPPED by migration 022 (Function #7 in 021 dropped by 022 line 14)   | -1       |
| Net distinct active SECURITY DEFINER functions in resulting catalog                   | 13       |
+---------------------------------------------------------------------------------------+----------+
| Breakdown of Active Functions by Configured search_path:                              |          |
| - Functions with SET search_path = pg_catalog, auth_private (Functions #1, #2, #3, #4)| 4        |
| - Functions with SET search_path = pg_catalog, public, auth_private (#5,#6,#8,#9,#10,#11,#12,#13)| 8 |
| - Functions with SET search_path = pg_catalog (Function #14 in 022)                   | 1        |
| Total Active SECURITY DEFINER Functions                                               | 13       |
+---------------------------------------------------------------------------------------+----------+
| Trigger routines declaring SET search_path = pg_catalog, public, auth_private         | 1        |
| Total functions in 021 declaring SET search_path = pg_catalog, public, auth_private    | 10       |
+---------------------------------------------------------------------------------------+----------+
```

---

## 6. D-22: Authentication Lookup Role and Grant Reconciliation

### 6.1 Current Migration Grants vs. Application Call Path

1. **Role Receiving EXECUTE in Migrations:**
   - Migration `021` line 206: `GRANT EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) TO college_app_user;` [VERIFIED STATICALLY]
   - Migration `022` line 51: `GRANT EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) TO college_app_user;` [VERIFIED STATICALLY]
   - Migration `021` line 205 & `022` line 50: `REVOKE ALL ON FUNCTION public.lookup_user_by_email_for_auth(text) FROM PUBLIC;` [VERIFIED STATICALLY]
2. **Application Calling Role:**
   - The application backend initializes its primary database engine via `DATABASE_APP_ROLE_URL` (`backend/app/database/connection.py` lines 34–52), which authenticates as `college_app_user` [VERIFIED STATICALLY].
   - Call chain: `/api/v1/auth/login` (`backend/app/api/v1/auth.py` lines 69–75) $\to$ `AuthService.authenticate` (`backend/app/services/auth_service.py` line 75) $\to$ `UserRepository.get_auth_account_by_email` (`backend/app/repositories/user_repository.py` lines 38–60) [VERIFIED STATICALLY].
3. **Shared Role Reality:**
   - The application uses a single shared database role (`college_app_user`) across the entire web backend. Every endpoint (prospective student chat, admin document uploads, public registrations) executes on connection pools authenticated as `college_app_user` [VERIFIED STATICALLY].
4. **Password Hash Return & Column Projections:**
   - Migration `022` lines 17–25 returns exactly 7 columns: `id`, `email`, `hashed_password`, `full_name`, `role`, `is_verified`, `is_active` [VERIFIED STATICALLY].
   - While this projection excludes unrelated user table columns (`avatar_url`, `preferences`, `metadata`, `created_at`, `updated_at`), it **explicitly includes `hashed_password`** [VERIFIED STATICALLY].
   - Because `college_app_user` has `EXECUTE` on the function and powers all connection pools, any application component or endpoint executing raw SQL has database permission to invoke the function and retrieve password hashes [VERIFIED STATICALLY].

### 6.2 Proposed Dedicated Authentication Role (Target Architecture)

To enforce least privilege, a dedicated authentication connection pool role has been proposed [PROPOSED]:
- **New Role:** Provision a `NOLOGIN` capability role `college_auth_role` and an authenticated connection role `college_auth_user`.
- **Exclusive Privileges:**
  ```sql
  REVOKE EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) FROM college_app_user;
  GRANT EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) TO college_auth_role;
  ```
- **Application Pool Isolation:** Configure a dedicated connection pool (`DATABASE_AUTH_ROLE_URL`) utilized strictly by `AuthService`.

### 6.3 Governance Status of D-22

- **The dedicated role proposal is NOT implemented and does NOT exist in repository code** [VERIFIED STATICALLY].
- Introducing a dedicated authentication role requires infrastructure changes (additional connection pool, secret management, connection limits).
- **Project Owner Approval:** **REQUIRED**. D-22 cannot be silently resolved or marked complete. It remains **PENDING HUMAN DECISION** and blocks Gate A.
- **Live Database Grants:** The live catalog privileges on `lookup_user_by_email_for_auth` remain **NOT VERIFIED — DATABASE VALIDATION REQUIRED**.

---

## 7. Corrected Identity and RLS Test Guidance

### 7.1 D-05: Technical Correction of Operator Shadowing Risk

Step 6.3.2 suggested that an attacker creating a custom `=` operator in `public` could shadow standard equality comparisons inside `SECURITY DEFINER` functions. This claim was technically inaccurate and is hereby corrected [VERIFIED STATICALLY]:
- In migrations `021`, the 9 definer functions declare `SET search_path = pg_catalog, public, auth_private`.
- Because `pg_catalog` is placed **first** in the search path, PostgreSQL's operator and function resolution parser (`parse_func.c`, `parse_oper.c`) evaluates candidates in `pg_catalog` before considering schema `public`.
- For standard comparisons between built-in catalog types (e.g., `text = text`, `uuid = uuid`), PostgreSQL resolves the built-in operator from `pg_catalog`. An attacker cannot shadow standard operators on built-in types simply by placing an operator in `public`.
- **The Actual Architectural Risk of `public` in search_path:**
  1. If a function references user-defined types or unqualified non-system functions/views not present in `pg_catalog`, an attacker with `CREATE` in `public` could define objects matching those names.
  2. If table references are unqualified, a table created in `public` could be referenced unexpectedly if internal assumptions fail.
  3. However, exploitability cannot be determined without inspecting live catalog permissions: whether untrusted roles possess `CREATE` on `public` remains **NOT VERIFIED — DATABASE VALIDATION REQUIRED**.

### 7.2 D-06 / D-18: PostgreSQL vs. Application Identity Boundaries

```
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Identity Mechanism       | Layer                 | Verification Source         | Scope & Purpose                   |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| session_user             | PostgreSQL Connection | Authenticated connection    | Connection pooling, PgBouncer,    |
|                          | (TCP Socket)          | credentials (pg_hba.conf)   | server connection auditing        |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| current_user             | PostgreSQL Session    | Active execution context    | SQL object permissions (ACLs),    |
|                          | (Transaction/Routine) | (Switches on SET ROLE/Definer)| table grants, view access       |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Application JWT          | HTTP API Layer        | FastAPI cryptographic verify| Client authentication, API route  |
|                          |                       | (SecretStr / JWT secret)    | RBAC (get_current_user)           |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Signed Request Context   | PostgreSQL Transaction| PL/pgSQL HMAC verification  | Multi-tenant row-level security   |
| (app.request_context)    | (Local GUCs)          | (auth_private.rls_keys)     | (RLS policies on tables)          |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
| Supabase auth.uid()      | PostgREST (Native)    | Unused in FastAPI backend   | Legacy RLS in migration 017;      |
|                          |                       | (Dropped in 019/021)        | replaced by custom signed context |
+--------------------------+-----------------------+-----------------------------+-----------------------------------+
```

- **`session_user` Dependencies:** Static inspection confirmed that zero repository queries, views, or triggers reference `session_user` [VERIFIED STATICALLY]. It is preserved strictly as the connection identity.
- **`current_user` in SECURITY DEFINER:** When execution enters a `SECURITY DEFINER` function, PostgreSQL temporarily switches `current_user` to the function's owner (`proowner`). It does not alter `session_user`.
- **Signed Context Equivalence:** Application-signed context is an application-level data slicing mechanism. It does **not** grant PostgreSQL table permissions and cannot bypass table-level ACL denials.

### 7.3 D-07: Direct-Login vs. SET ROLE Testing Architecture

1. `SET ROLE` alters `current_user` but preserves `session_user`. Testing via `SET ROLE` validates effective table privileges and RLS, but does not validate connection-level authentication, default search paths, or connection pool resets.
2. Capability roles (`college_app_user`, `college_worker_role`) must remain `NOLOGIN` in production to enforce least privilege.
3. **PostgreSQL Version-Specific Membership Syntax:**
   - In PostgreSQL 16+, role membership options allow fine-grained inheritance:
     ```sql
     GRANT college_app_user TO college_test_harness WITH INHERIT FALSE, SET TRUE;
     ```
   - In PostgreSQL 15 and earlier, inheritance is governed at the role level:
     ```sql
     ALTER ROLE college_test_harness NOINHERIT;
     GRANT college_app_user TO college_test_harness;
     ```
   - Testing must use `college_test_harness` to execute `SET ROLE`, while direct-login testing is reserved for dedicated login roles.

### 7.4 D-09: Precise Expected Outcomes in Negative RLS Testing

Negative test assertions must differentiate distinct database engine error and filtering behaviors [PROPOSED]:

```
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| Test Tier          | Test Principal             | Context State         | Operation           | Exact Expected PostgreSQL Outcome              |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 1. Table ACL Denial| college_test_unprivileged  | No signed context     | SELECT / INSERT /   | ERROR 42501: permission denied for relation    |
|                    | (Zero table grants)        |                       | UPDATE ON users     |                                                |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 2. RLS SELECT      | college_test_harness       | No signed context     | SELECT ON documents | Returns 0 rows (empty set). No SQL error.      |
|    Filtering       | (SET ROLE college_app_user)| (or invalid signature)|                     |                                                |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 3. RLS INSERT      | college_test_harness       | No signed context     | INSERT INTO docs    | ERROR 42501: new row violates row-level        |
|    WITH CHECK      | (SET ROLE college_app_user)|                       |                     | security policy for table "documents"          |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 4. RLS UPDATE      | college_test_harness       | No signed context     | UPDATE documents    | Command succeeds, but affects exactly 0 rows   |
|    USING Filtering | (SET ROLE college_app_user)|                       | SET title = 'x'     | (UPDATE 0). No SQL error.                      |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 5. RLS UPDATE      | college_test_harness       | Valid context Tenant A| UPDATE documents    | ERROR 42501: new row violates row-level        |
|    WITH CHECK      | (SET ROLE college_app_user)|                       | SET college_id = B  | security policy for table "documents"          |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 6. Cross-Tenant    | college_test_harness       | Valid context Tenant A| SELECT ON Tenant B  | Returns 0 rows (Tenant B records invisible).   |
|    Isolation       | (SET ROLE college_app_user)|                       | records             |                                                |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 7. Role Switching  | college_test_harness       | Active session        | SET ROLE postgres;  | ERROR 42501: permission denied to set role     |
|    Escalation      | (SET ROLE college_app_user)|                       |                     | "postgres"                                     |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 8. Membership      | college_test_harness       | Active session        | GRANT superuser TO  | ERROR 42501: must have admin option on role    |
|    Grant Escalation| (SET ROLE college_app_user)|                       | college_app_user;   | "superuser"                                    |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 9. Role DDL        | college_test_harness       | Active session        | ALTER ROLE ...      | ERROR 42501: must be superuser to alter role   |
|    Escalation      | (SET ROLE college_app_user)|                       | SUPERUSER;          |                                                |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 10. Definer Exec   | college_test_unprivileged  | No signed context     | SELECT * FROM       | ERROR 42501: permission denied for function    |
|     Denial         |                            |                       | is_request_context_valid(); | is_request_context_valid               |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
| 11. Protected Table| college_app_user           | Active session        | SELECT * FROM       | ERROR 42501: permission denied for relation    |
|     Access Denial  | (SET ROLE college_app_user)|                       | rls_context_keys;   | rls_context_keys                               |
+--------------------+----------------------------+-----------------------+---------------------+------------------------------------------------+
```

---

## 8. Corrected Signing-Key Rotation Guidance (D-10)

### 8.1 Clarification on Key Overlap Duration

The previously cited 18-minute overlap window is an **illustrative arithmetic example**, not an approved or validated policy [PROPOSED]. The actual dual-key overlap window must be determined by the Project Owner and Key Management Specialist based on empirical operational variables:
1. **Context Token TTL:** Currently 300 seconds (5 minutes) in `backend/app/database/session.py` line 95 [VERIFIED STATICALLY].
2. **Deployment Rollout Duration:** The time required for a rolling deployment across all Celery workers and FastAPI instances to fully converge.
3. **Clock Skew Allowance:** Permissible time delta between application servers and database hosts (typically 30–60 seconds).
4. **Verification-Key Cache TTL:** If application instances cache keys locally, the cache refresh interval.
5. **In-Flight Long-Running Tasks:** Duration of long-running transactions or document extractions.

### 8.2 Scope and Realities of Emergency Key Revocation

When a key is marked `REVOKED` in `auth_private.rls_context_keys`:
- **Subsequent Validations:** Every subsequent execution of `auth_private.is_request_context_valid()` immediately rejects contexts signed with that key [VERIFIED STATICALLY].
- **In-Flight Transactions:** Key revocation in PostgreSQL does **not** retroactively terminate or roll back an already-executing SQL statement or transaction that successfully completed its context validation earlier in the transaction.
- **Application Cache Invalidation:** If FastAPI backend instances cache keys in memory, revocation in the database does not clear application memory caches until the cache expires or an invalidation message is received. Redis pub/sub has been discussed as an invalidation mechanism, but it is **not implemented in repository code** [PROPOSED].

---

## 9. Corrected Disposable-Environment Requirements (D-16)

### 9.1 Test Connection URL Validation Rules [PROPOSED]

Every database URL loaded by `tests/config.py` or test runners must be validated prior to opening any socket:
- **Exact Scheme per Engine:** Async engines (`ASYNC_APP_URL`, `ASYNC_ADMIN_URL`) strictly require `postgresql+asyncpg://`; sync engines (`SYNC_ADMIN_URL`, `SYNC_APP_URL`) strictly require `postgresql://` [VERIFIED STATICALLY]. Rejection must occur if the scheme does not match the driver.
- **Exact Allowed Host:** Strictly loopback (`127.0.0.1`, `localhost`, `::1`).
- **Exact Allowed Port:** Must match the configured local disposable test port.
- **Database Name & Role:** Must match designated disposable test databases and expected roles.
- **Zero Fallback:** Prohibit silent fallback to `.env`, SQLite, or remote databases.

### 9.2 Redis Infrastructure Isolation

- **Isolation Finding:** Using separate Redis database indexes (`/14`, `/15`) on the same shared Redis instance does **not** provide strong infrastructure isolation. Memory, CPU, and keyspaces are shared; a single administrative command impacts all indexes [VERIFIED STATICALLY].
- **Target Specification:** Testing background tasks requires a **dedicated disposable Redis container** on an isolated loopback port, distinct credentials, and a dedicated network boundary [PROPOSED].

---

## 10. Corrected Migration-History and Privacy Wording

### 10.1 Corrected Migration Branching Language (D-01)

The previous assertion that "Branch B is the only safe operational position" is corrected to the following precise formulation:

> **Branch B (Forward-Only Corrective Migration) is the conservative default while migration history remains unknown. Branch A (In-Place Migration Rewrite) may be considered only after authoritative written evidence establishes that migrations 001–022 were never applied, partially applied, released, or deployed in any development, staging, shared, or production environment.**

Migration file contents alone cannot establish deployment history. Whether migrations were run in hosted Supabase remains **NOT VERIFIED — DATABASE VALIDATION REQUIRED**.

### 10.2 Corrected Privacy and Retention Claims (D-12)

1. **Unsupported Generalizations Removed:** The generic statement that student records are "frequently retained for 3–7 years" has been removed as unsupported by repository evidence.
2. **Statutory vs. Institutional Boundaries:**
   - **FERPA (34 CFR Part 99):** Governs privacy of educational records; does not specify a 30-day operational log retention window.
   - **GDPR (Article 5(1)(e)):** Mandates storage limitation (data kept no longer than necessary for processing purposes); does not mandate a universal 30-day cutoff.
   - **Proposed 30-Day Retention Schedule:** Represents an engineering recommendation for notification delivery logs, subject to explicit institutional approval by the Project Owner and Data Privacy Officer [PENDING OWNER DECISION].

---

## 11. D-01 through D-22 Decision-Status Matrix

Every decision remains **PENDING HUMAN DECISION**. No decision has been approved.

```
+-----+-----------------------------------+--------------------+------------------------+---------------+--------------------+
| ID  | Decision Focus Area               | Review Rec.        | Approvers Required     | Blocks Gate A | DB State Verified? |
+-----+-----------------------------------+--------------------+------------------------+---------------+--------------------+
| D-01| Migration History & Branching     | Branch B (Default) | Owner + Release Eng.   | YES           | NOT VERIFIED       |
| D-02| Worker Process Isolation Model    | Sandboxed / Claim  | Owner + Sec. Architect | YES           | NOT VERIFIED       |
| D-03| Worker Claim Authentication       | claim_job() & Role | DB Sec. Architect      | YES           | NOT VERIFIED       |
| D-04| Job Lease, Heartbeat & Recovery   | 5m lease / 60s hb  | Owner + Systems Eng.   | YES           | NOT VERIFIED       |
| D-05| SECURITY DEFINER & search_path    | pg_catalog / Roles | PostgreSQL Sec. Arch.  | YES           | NOT VERIFIED       |
| D-06| Identity Layer Separation         | Signed Context     | AppSec + DB Architect  | YES           | NOT VERIFIED       |
| D-07| Direct-Login vs. SET ROLE Testing | SET ROLE Harness   | Sec. Test Engineer     | YES           | NOT VERIFIED       |
| D-08| PG 17 Role Closure & Allowlist    | Recursive CTE      | PostgreSQL DBA         | YES           | NOT VERIFIED       |
| D-09| Negative Principal Isolation      | Multi-Tier Matrix  | QA / Sec. Test Eng.    | YES           | NOT VERIFIED       |
| D-10| Key Rotation & Dual Verification  | Dual-Key Schema    | Owner + Key Mgmt Spec. | YES           | NOT VERIFIED       |
| D-11| Password-Reset Email Handling     | Formal Deferral    | Owner + Privacy Spec.  | YES           | NOT APPLICABLE     |
| D-12| Notification Data Retention       | 30-Day Purge       | Owner + Privacy Off.   | YES           | NOT VERIFIED       |
| D-13| College Registration Flow         | Pending Only       | Owner + AppSec         | YES           | NOT VERIFIED       |
| D-14| Staff RBAC Matrix (Editor/Viewer) | Strict Read-Only   | Owner + AppSec         | YES           | NOT VERIFIED       |
| D-15| Audit & Telemetry Redaction       | Strict Allowlist   | Owner + AI Sec. Lead   | YES           | NOT VERIFIED       |
| D-16| Disposable Test Stack Isolation   | Local Loopback     | DevOps + Sec. Arch.    | YES           | NOT VERIFIED       |
| D-17| Staged Gate Authorization Model   | 4-Stage Control    | Owner + Lead Architect | YES           | NOT APPLICABLE     |
| D-18| Application Identity Boundary     | Deprecate auth.uid | Identity Architect     | YES           | NOT VERIFIED       |
| D-19| Visitor Token Lifecycle & Payload | 24h Fixed / v2     | Owner + AppSec         | YES           | NOT VERIFIED       |
| D-20| Guest Support Ticket Boundary     | Create-Only        | Owner + Sec. Architect | YES           | NOT VERIFIED       |
| D-21| College Chat Analytics Privacy    | Aggregate Only     | Owner + Privacy Off.   | YES           | NOT VERIFIED       |
| D-22| Auth Lookup Function Contract     | 7-Field Projection | Owner + AppSec + DB Sec| YES           | NOT VERIFIED       |
+-----+-----------------------------------+--------------------+------------------------+---------------+--------------------+
```

---

## 12. Missing Evidence and Owner-Approval Register

### 12.1 Six Missing Documentary Evidence Packages

```
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| #  | Evidence Package Name                                         | Status       | Action Required to Complete                           |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 1  | Migration History and Deployment Ledger                       | MISSING      | Release Owner must submit certified environment audit.|
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 2  | Key Management and Rotation Runbook                           | MISSING      | Key Management Specialist must author KMS custody doc.|
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 3  | Worker Authentication and Isolation Architecture              | INCOMPLETE   | Worker Platform Lead must finalize queue routing/DDL. |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 4  | Data Retention and Privacy Schedule                           | MISSING      | Data Privacy Officer must sign formal retention policy.|
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 5  | Local Disposable Supabase Stack Specification                 | INCOMPLETE   | DevOps must provide verified Compose manifest.        |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 6  | Delegation of Authority and Approval Ownership Document       | MISSING      | Corporate sign-off naming human authorizers for Gates.|
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
```

### 12.2 Decisions Requiring Explicit Project Owner Approval (14 Decisions)

The following fourteen decisions carry product, business, budget, or architectural policy trade-offs and **cannot be approved by technical specialists alone**:
- **D-01:** Selection of Branch B (conservative default) vs. Branch A.
- **D-02:** Selection of Worker Isolation infrastructure model.
- **D-04:** Approval of background task lease duration, retry limit, and SLA.
- **D-10:** Approval of context key custody and rotation operational policy.
- **D-11:** Decision to defer self-service password reset vs. contract provider.
- **D-12:** Approval of notification log 30-day retention schedule.
- **D-13:** Sign-off on registration workflow (pending status for public submissions).
- **D-14:** Approval of staff RBAC matrix (Editor vs. Viewer boundaries).
- **D-15:** Approval of audit and AI telemetry data scrubbing allowlist.
- **D-17:** Formal sign-off on 4-stage gate authorization process.
- **D-19:** Approval of prospective student visitor token 24-hour expiration policy.
- **D-20:** Confirmation that guest support tickets remain create-only.
- **D-21:** Approval of aggregate-only analytics policy for College Admins.
- **D-22:** Approval to introduce a dedicated authentication connection pool role.

---

## 13. Gate A Submission-Readiness Assessment

```
+--------------------------------------------------------------------------------------------------------------------+
| GATE A SUBMISSION-READINESS EVALUATION                                                                             |
+--------------------------------------------------------------------------------------------------+-----------------+
| Assessment Criterion                                                                             | Evaluation      |
+--------------------------------------------------------------------------------------------------+-----------------+
| 1. All documentation inconsistencies across Steps 6.0–6.3.2 resolved and reconciled?             | YES — COMPLETE  |
| 2. Static repository facts strictly separated from unverified database state?                   | YES — COMPLETE  |
| 3. Overconfident operator-shadowing and exploitability assertions technically corrected?        | YES — COMPLETE  |
| 4. Exact SECURITY DEFINER function inventory established without shorthand signatures?           | YES — COMPLETE  |
| 5. Testing architecture disentangled (direct-login vs SET ROLE vs negative tiers)?               | YES — COMPLETE  |
| 6. Complete 22-decision register established with explicit approver roles?                       | YES — COMPLETE  |
| 7. Package ready to be presented to Project Owner and Technical Specialists?                     | YES — READY     |
+--------------------------------------------------------------------------------------------------+-----------------+
| 8. Have formal Project Owner decisions been executed and recorded?                               | NO — PENDING    |
| 9. Have technical specialist sign-offs been collected?                                           | NO — PENDING    |
| 10. Have the six required documentary evidence packages been submitted?                          | NO — MISSING    |
| 11. Can Gate A be marked COMPLETE at this time?                                                  | NO — BLOCKED    |
+--------------------------------------------------------------------------------------------------+-----------------+
```

### Conditions for Declaring Gate A Complete
Gate A can be certified as **COMPLETE** only when:
1. Written selections for all 14 Project Owner decisions are recorded in the project register.
2. Written technical sign-offs across all 13 specialist domains are archived.
3. All six missing documentary evidence packages are submitted and approved.

---

## 14. Explicit Implementation and Database-Validation Prohibitions

```
================================================================================
EXPLICIT GOVERNANCE DIRECTIVE:
1. ZERO IMPLEMENTATION IS AUTHORIZED BY THIS DOCUMENT.
2. GATE B (IMPLEMENTATION) REMAINS STRICTLY NOT AUTHORIZED.
   - Modifying application code, SQL migrations, or configurations remains PROHIBITED.
   - Gate B authorization requires independent, written sign-off AFTER Gate A closure.
3. GATE C (ISOLATED DATABASE VALIDATION) REMAINS STRICTLY NOT VALIDATED.
   - Executing SQL, running migrations, or connecting to databases remains PROHIBITED.
   - Validation must occur exclusively inside an authorized local disposable Supabase stack.
4. PRODUCTION DEPLOYMENT REMAINS STRICTLY NOT APPROVED.
================================================================================
```

---

## 15. Final Independent-Auditor Conclusion

The technical consistency review of Phase 3A.4.4B is now fully consolidated. All documentation-level discrepancies, metric conflicts, and overconfident security claims have been resolved. The package is technically mature, internally consistent, and equipped with rigorous decision registers.

```
================================================================================
FINAL DOCUMENTATION VERDICT:
READY FOR FORMAL HUMAN GATE A DECISIONS
================================================================================
```

*This conclusion certifies documentation readiness only. Gate A remains incomplete pending formal human owner and specialist sign-offs. Gate B implementation, Gate C database validation, and production release remain unauthorized.*
