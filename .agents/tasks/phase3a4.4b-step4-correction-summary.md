# Step 4 Correction Summary

## Status

**READY FOR HUMAN REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION — NOT DATABASE VALIDATED.** This correction does not grant implementation approval, authorize database work, or claim database validation.

## Four corrections made

1. **Migration 021 transaction safety:** Distinguished preflight checks from assertions that must run inside 021 before its own `COMMIT`. Specified fail-and-rollback conditions for token conversion, destructive hash/column handling, guest-token invariants, final RLS/policy state, and function security. Clarified there is no pause after migration execution but before its internal commit, and documented failure recovery.
2. **Runtime-role tests:** Resolved the `NOLOGIN`/test-connection contradiction. Compared copied-grant test logins, a disposable harness with controlled `SET ROLE`, and enabling LOGIN on runtime roles. Recommended keeping runtime roles `NOLOGIN` and testing through a narrowly scoped disposable harness that switches to the actual runtime role. Updated the test matrix and documented what this does not validate.
3. **SECURITY DEFINER checks:** Expanded the verification plan beyond `pg_proc.proacl`, explicitly accounting for PostgreSQL default function ACLs when `proacl IS NULL`, PUBLIC EXECUTE, effective inherited privileges, owner attributes/rights, schema privileges, `search_path`, nested definer calls, RLS, and actual function behavior. Added proposed read-only catalog query shapes; none were executed.
4. **Worker isolation and job authorization:** Clarified that a job UUID is not authorization. Specified job creation/publishing, tenant/resource binding, authenticated claim, active lease validation, heartbeat/expiry, retries, duplicate delivery, idempotency, crash recovery, audit, cross-tenant controls, and compromise containment. Compared shared and tenant-isolated workers; recommend tenant-isolated workers or explicitly approved trust cohorts, with human approval still required.

The report headings and cross-references were reconciled. The migration sequence, rollback guidance, security test matrix, human decision register, and approval gates were updated to match the four corrections.

## Final clarifications added

1. **`SET ROLE` identity limits:** Documented that `session_user` remains the harness login while `current_user`/`current_role` become the NOLOGIN runtime role. Mapped the identity values to the database connection, grants/RLS/SECURITY DEFINER, role membership, and signed-context paths; required explicit inspection of all identity-consuming policies/functions. The report does not claim `SET ROLE` reproduces direct login. Tests fail on identity mismatches or harness-only authorization.
2. **PostgreSQL 17 membership closure:** Added a cycle-safe recursive `pg_auth_members` traversal carrying each path's `set_option`, `inherit_option`, and `admin_option`; required a protected-role inventory covering superuser, BYPASSRLS, relation/function/migration owners, and other privileged roles. The query is proposed and was not executed.
3. **Independent unprivileged negative principal:** Added a disposable non-owner, non-superuser, non-BYPASSRLS login with no application/worker/owner memberships, no protected EXECUTE, and no unintended schema CREATE. Added synthetic RLS and ACL-denial tests, including forged identity GUCs, cross-tenant access, worker/maintenance calls, and role escalation attempts. Clarified why `anon` alone is not an adequate substitute.
4. **Worker claim trust boundary:** Specified the proposed authenticated per-pool connection principal mapped to a NOLOGIN capability role; claim-function authorization and least-privilege SECURITY DEFINER ownership/grants; DB validation of job, attempt, tenant/resource, and lease state; post-claim scoped context issuance; and heartbeat, retry, duplicate, crash, cross-tenant, and compromise handling. The authentication mechanism, signer placement, function owner/grants, and pool model remain human decisions.

The report's final decision remains **READY FOR HUMAN REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION — NOT DATABASE VALIDATED**.

## Final review corrections

1. **Protected-object ownership inventory:** Expanded the protected-owner list and proposed PostgreSQL catalog query to cover schemas; all relation kinds including sequences, views, materialized views and foreign tables; functions/procedures; types/domains; extensions; and other namespace/global objects including operators, collations, FDWs, languages, text-search objects, publications/subscriptions, database and tablespace owners. Documented exclusions for system/TOAST/temporary schemas and the owning-object treatment for metadata without standalone owner fields. The query remains proposed and unexecuted.
2. **Required test-principal inventory:** Added a required-principal roster for runtime, worker, harness, and independent negative-test principals, with fail-closed behavior for missing/ambiguous principals, unexamined direct/transitive paths, unknown owners, and incomplete effective privilege or schema CREATE checks. Required PostgreSQL 17 membership flags and ownership checks across the expanded object inventory.
3. **Gate 5 session identity:** Clarified that SET ROLE validates the effective capability role but not direct-login `session_user`. Every production path relying on `session_user` remains explicitly **UNVALIDATED** until a separately approved disposable direct-login test is completed; Gate 5 cannot be marked complete for that path before then.

## Unresolved human decisions

- Whether migrations 001–022 have ever been applied, released, or deployed in any environment; select Branch A or B only with accountable written confirmation.
- Shared worker versus tenant-isolated workers/trust cohorts; claim authorization, lease duration, retry, and duplicate-execution policy.
- Exact SECURITY DEFINER owners, grants, search paths, and RLS behavior.
- Which production checks consume `session_user`, `current_user`, `current_role`, role membership, signed identity, or connection identity; whether any require a separately approved direct-login test.
- Protected-role allowlist and PostgreSQL 17 membership closure; the synthetic negative-test principal's minimal table-grant boundary.
- Worker connection authentication, claim/context function ownership and grants, signing-key access, and whether signing occurs in the database or a separately trusted signer.
- Password-reset email delivery; notification email retention and duration.
- Public college registration versus Super Admin-only creation.
- EDITOR/VIEWER permissions.
- Audit payload allowlists, AI telemetry limits, and signing-key overlap/rotation.
- Disposable Supabase-compatible environment, implementation authorization, and later database-validation/release approval.

## Files

**Read or specifically inspected:** the Step 4 report, Step 3 report, Step 3.1 addendum, Step 2 migration-validation report, `database/migrations/021_phase3a42_security_onboarding.sql`, and the repository source/test/workflow/documentation paths listed in Section 3 of the corrected Step 4 report. The 001–022 inventory is carried forward from the prior Step 2 investigation.

**Modified:**
- `.agents/tasks/phase3a4.4b-step4-controlled-implementation-plan.md`
- `.agents/tasks/phase3a4.4b-step4-correction-summary.md`

## Safety confirmation

This was documentation-only. No SQL or migration source file, test, application code, configuration, `.env`, credential, signing key, connection string, database, database role, policy, test data, Docker container, volume, hosted Supabase, or deployment was changed or executed. No shell commands, SQL statements, tests, migrations, or database checks were run. The report contains proposed PostgreSQL 17 catalog queries for human review; none was executed. No implementation or database validation was performed. The report remains **READY FOR HUMAN REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION — NOT DATABASE VALIDATED**.
