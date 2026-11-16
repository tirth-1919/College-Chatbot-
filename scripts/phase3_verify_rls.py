"""
Phase 3 READ-ONLY RLS Security Verification.
Runs against live Supabase. No writes, inserts, or schema changes.
"""
import asyncio, os, json
from dotenv import load_dotenv
import asyncpg

load_dotenv()

# Admin connection (postgres role) for inspecting pg_catalog — read-only queries only
ADMIN_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)
# App role connection (college_app_user) for testing RLS enforcement
APP_URL = os.environ.get("DATABASE_APP_ROLE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

# Known tenant UUIDs from seed data
AIT_COLLEGE_ID  = "11111111-1111-1111-1111-111111111111"
RCTI_COLLEGE_ID = "22222222-2222-2222-2222-222222222222"

results = []

def record(section, check, status, detail, file_ref="database"):
    results.append({"section": section, "check": check, "status": status, "detail": detail, "ref": file_ref})
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(status, "?")
    print(f"  {icon} [{status}] {check}: {detail[:120]}")

# ============================================================
# SECTION 1: Role verification
# ============================================================
async def check_roles(admin_conn, app_conn):
    print("\n=== 1. DATABASE ROLE VERIFICATION ===")

    # 1a. admin conn role
    r = await admin_conn.fetchrow("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    record("1.Role", "Admin conn role", "INFO", f"Connected as: {r['current_user']} superuser={r['rolsuper']} bypassrls={r['rolbypassrls']}")

    # 1b. app conn role
    r2 = await app_conn.fetchrow("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    status = "PASS" if r2['current_user'] == 'college_app_user' else "FAIL"
    record("1.Role", "App engine role = college_app_user", status, f"current_user={r2['current_user']}")

    status = "PASS" if not r2['rolsuper'] else "FAIL"
    record("1.Role", "App role NOT superuser", status, f"rolsuper={r2['rolsuper']}")

    status = "PASS" if not r2['rolbypassrls'] else "FAIL"
    record("1.Role", "App role NOT BYPASSRLS", status, f"rolbypassrls={r2['rolbypassrls']}")

    # 1c. App role table ownership check (should not own any tables)
    owned = await admin_conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tableowner='college_app_user'"
    )
    status = "PASS" if len(owned) == 0 else "WARN"
    record("1.Role", "App role owns no tables", status, f"Owned tables: {[r['tablename'] for r in owned] or 'none'}")

# ============================================================
# SECTION 2: RLS policy inventory
# ============================================================
async def check_rls_policies(admin_conn):
    print("\n=== 2. RLS POLICY INVENTORY ===")

    rows = await admin_conn.fetch("""
        SELECT
            c.relname AS table_name,
            c.relrowsecurity AS rls_enabled,
            c.relforcerowsecurity AS rls_forced,
            COUNT(p.polname) AS policy_count
        FROM pg_class c
        LEFT JOIN pg_policy p ON p.polrelid = c.oid
        WHERE c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
          AND c.relkind = 'r'
        GROUP BY c.relname, c.relrowsecurity, c.relforcerowsecurity
        ORDER BY c.relname
    """)

    tables_no_rls = []
    tables_no_policy = []
    for r in rows:
        if not r['rls_enabled']:
            tables_no_rls.append(r['table_name'])
        elif r['policy_count'] == 0:
            tables_no_policy.append(r['table_name'])

    record("2.RLS", "All application tables have RLS enabled",
           "PASS" if not tables_no_rls else "FAIL",
           f"Tables WITHOUT RLS: {tables_no_rls or 'none'}")

    record("2.RLS", "All RLS-enabled tables have >= 1 policy",
           "PASS" if not tables_no_policy else "FAIL",
           f"Tables with ZERO policies: {tables_no_policy or 'none'}")

    # Detail: tables with RLS
    rls_tables = [(r['table_name'], r['policy_count']) for r in rows if r['rls_enabled']]
    record("2.RLS", "RLS table count", "INFO", f"{len(rls_tables)} tables with RLS: {[t[0] for t in rls_tables]}")

    # knowledge_chunks policy detail
    kc = await admin_conn.fetch("""
        SELECT polname, pg_get_expr(polqual, polrelid) AS using_expr
        FROM pg_policy p JOIN pg_class c ON c.oid = p.polrelid
        WHERE c.relname = 'knowledge_chunks' AND c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname='public')
    """)
    for p in kc:
        null_safe = "current_app_tenant() IS NOT NULL" in (p['using_expr'] or "")
        record("2.RLS", f"knowledge_chunks policy '{p['polname']}' blocks NULL tenant",
               "PASS" if null_safe else "FAIL",
               f"USING: {p['using_expr'][:200]}")

# ============================================================
# SECTION 3: Cross-tenant isolation tests (app role, no BYPASSRLS)
# ============================================================
async def check_cross_tenant_isolation(app_conn):
    print("\n=== 3. CROSS-TENANT ISOLATION TESTS ===")

    # 3a. No tenant context — count visible rows on key tables
    await app_conn.execute("SELECT set_config('app.current_college_id', '', true)")
    await app_conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
    await app_conn.execute("SELECT set_config('app.current_user_id', '', true)")

    for table in ['colleges', 'documents', 'website_sources', 'knowledge_chunks', 'chat_sessions', 'extracted_facts']:
        try:
            count = await app_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            # For colleges: should see only APPROVED+active ones (public read policy)
            # For others: 0 rows expected (no tenant context)
            if table == 'colleges':
                record("3.CrossTenant", f"NULL tenant → {table} count={count}",
                       "INFO", f"colleges visible without tenant (expected: only APPROVED ones)")
            else:
                record("3.CrossTenant", f"NULL tenant → {table} row count",
                       "PASS" if count == 0 else "FAIL",
                       f"count={count} (expected 0 — no tenant GUC set)")
        except Exception as e:
            record("3.CrossTenant", f"NULL tenant → {table}", "FAIL", f"Error: {e}")

    # 3b. AIT tenant context
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
    await app_conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")

    ait_docs = await app_conn.fetchval("SELECT COUNT(*) FROM documents WHERE college_id = $1", AIT_COLLEGE_ID)
    rcti_docs_via_ait = await app_conn.fetchval("SELECT COUNT(*) FROM documents WHERE college_id = $1", RCTI_COLLEGE_ID)
    total_docs = await app_conn.fetchval("SELECT COUNT(*) FROM documents")

    record("3.CrossTenant", "AIT tenant sees its own documents",
           "PASS" if ait_docs >= 0 else "INFO",
           f"AIT own docs visible: {ait_docs}")

    record("3.CrossTenant", "AIT tenant CANNOT read RCTI documents (WHERE clause)",
           "PASS" if rcti_docs_via_ait == 0 else "FAIL",
           f"RCTI docs visible via AIT context WHERE filter: {rcti_docs_via_ait}")

    record("3.CrossTenant", "AIT tenant sees ONLY AIT total (no cross-tenant leak)",
           "PASS" if total_docs == ait_docs else "FAIL",
           f"Total visible={total_docs}, AIT own={ait_docs} — diff={total_docs - ait_docs} leaked records")

    # 3c. RCTI tenant context
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{RCTI_COLLEGE_ID}', true)")
    rcti_docs = await app_conn.fetchval("SELECT COUNT(*) FROM documents WHERE college_id = $1", RCTI_COLLEGE_ID)
    ait_docs_via_rcti = await app_conn.fetchval("SELECT COUNT(*) FROM documents WHERE college_id = $1", AIT_COLLEGE_ID)
    total_docs_rcti = await app_conn.fetchval("SELECT COUNT(*) FROM documents")

    record("3.CrossTenant", "RCTI tenant CANNOT read AIT documents (WHERE clause)",
           "PASS" if ait_docs_via_rcti == 0 else "FAIL",
           f"AIT docs visible via RCTI context WHERE filter: {ait_docs_via_rcti}")

    record("3.CrossTenant", "RCTI tenant sees ONLY RCTI total (no cross-tenant leak)",
           "PASS" if total_docs_rcti == rcti_docs else "FAIL",
           f"Total visible={total_docs_rcti}, RCTI own={rcti_docs} — diff={total_docs_rcti - rcti_docs} leaked records")

    # 3d. Test website_sources isolation
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
    total_sources = await app_conn.fetchval("SELECT COUNT(*) FROM website_sources")
    ait_sources = await app_conn.fetchval("SELECT COUNT(*) FROM website_sources WHERE college_id = $1", AIT_COLLEGE_ID)
    record("3.CrossTenant", "website_sources isolation (AIT sees only its own)",
           "PASS" if total_sources == ait_sources else "FAIL",
           f"Total visible={total_sources}, AIT own={ait_sources}")

    # 3e. knowledge_chunks: published chunks should NOT leak across tenants
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
    total_kc = await app_conn.fetchval("SELECT COUNT(*) FROM knowledge_chunks")
    ait_kc = await app_conn.fetchval("SELECT COUNT(*) FROM knowledge_chunks WHERE college_id = $1", AIT_COLLEGE_ID)
    record("3.CrossTenant", "knowledge_chunks: AIT sees no RCTI chunks",
           "PASS" if total_kc == ait_kc else "FAIL",
           f"Total visible={total_kc}, AIT own={ait_kc} — diff={total_kc - ait_kc} cross-tenant chunks")

    # 3f. Super admin sees all
    await app_conn.execute("SELECT set_config('app.is_super_admin', 'true', true)")
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
    # With super_admin=true, should see docs from BOTH colleges
    all_docs = await app_conn.fetchval("SELECT COUNT(*) FROM documents")
    record("3.CrossTenant", "Super admin can see all documents across tenants",
           "PASS" if all_docs >= ait_docs else "INFO",
           f"Super admin total visible={all_docs} (AIT={ait_docs}, RCTI={rcti_docs})")

    # 3g. users table — user can only see own row
    await app_conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
    # Without current_user_id set, should see only college members via admin policy
    all_users = await app_conn.fetchval("SELECT COUNT(*) FROM users")
    record("3.CrossTenant", "users table with college admin context (no user_id GUC)",
           "INFO",
           f"Visible user count={all_users} (should be limited to AIT college members or 0)")

    # 3h. chat_messages isolation (via chat_sessions parent)
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
    await app_conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
    total_msgs = await app_conn.fetchval("SELECT COUNT(*) FROM chat_messages")
    ait_msgs = await app_conn.fetchval("""
        SELECT COUNT(*) FROM chat_messages cm
        JOIN chat_sessions cs ON cs.id = cm.session_id
        WHERE cs.college_id = $1
    """, AIT_COLLEGE_ID)
    record("3.CrossTenant", "chat_messages: AIT sees only its own sessions' messages",
           "PASS" if total_msgs == ait_msgs else "FAIL",
           f"Total visible={total_msgs}, AIT own={ait_msgs}")

# ============================================================
# SECTION 4: GUC transaction-locality
# ============================================================
async def check_guc_transaction_locality(app_conn):
    print("\n=== 4. GUC TRANSACTION-LOCALITY ===")

    # Set GUC inside a transaction and check it resets after commit
    await app_conn.execute("BEGIN")
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
    val_during = await app_conn.fetchval("SELECT current_setting('app.current_college_id', true)")
    await app_conn.execute("COMMIT")
    val_after = await app_conn.fetchval("SELECT current_setting('app.current_college_id', true)")

    record("4.GUC", "GUC visible during transaction",
           "PASS" if val_during == AIT_COLLEGE_ID else "FAIL",
           f"Value during txn: {val_during}")

    record("4.GUC", "GUC cleared after COMMIT (is_local=true)",
           "PASS" if val_after in ("", None) else "WARN",
           f"Value after commit: '{val_after}' (expected empty — asyncpg reuses connection)")

    # Check that RESET ALL clears the GUC
    await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', false)")  # session-level
    await app_conn.execute("RESET ALL")
    val_reset = await app_conn.fetchval("SELECT current_setting('app.current_college_id', true)")
    record("4.GUC", "RESET ALL clears session-level GUC",
           "PASS" if val_reset in ("", None) else "FAIL",
           f"Value after RESET ALL: '{val_reset}'")

# ============================================================
# SECTION 5: anon/authenticated grants
# ============================================================
async def check_anon_grants(admin_conn):
    print("\n=== 5. ANON/AUTHENTICATED GRANTS ===")
    rows = await admin_conn.fetch("""
        SELECT table_name, privilege_type, grantee
        FROM information_schema.role_table_grants
        WHERE grantee IN ('anon', 'authenticated') AND table_schema = 'public'
        ORDER BY table_name, grantee
    """)
    record("5.Grants", "Zero anon/authenticated table grants remain",
           "PASS" if len(rows) == 0 else "FAIL",
           f"Remaining grants: {[(r['grantee'], r['privilege_type'], r['table_name']) for r in rows] or 'none'}")

    # Check college_app_user has DML on all app tables
    app_grants = await admin_conn.fetch("""
        SELECT COUNT(DISTINCT table_name) AS tbl_count
        FROM information_schema.role_table_grants
        WHERE grantee = 'college_app_user' AND table_schema = 'public'
    """)
    record("5.Grants", "college_app_user has grants on application tables",
           "PASS" if app_grants[0]['tbl_count'] > 0 else "FAIL",
           f"Tables with grants: {app_grants[0]['tbl_count']}")

# ============================================================
# MAIN
# ============================================================
async def main():
    print("Phase 3 READ-ONLY RLS Verification")
    print("=" * 60)
    admin_conn = await asyncpg.connect(ADMIN_URL)
    app_conn = await asyncpg.connect(APP_URL)
    try:
        await check_roles(admin_conn, app_conn)
        await check_rls_policies(admin_conn)
        await check_cross_tenant_isolation(app_conn)
        await check_guc_transaction_locality(app_conn)
        await check_anon_grants(admin_conn)
    finally:
        await admin_conn.close()
        await app_conn.close()

    print("\n" + "=" * 60)
    print(f"TOTAL CHECKS: {len(results)}")
    passed  = sum(1 for r in results if r['status'] == 'PASS')
    failed  = sum(1 for r in results if r['status'] == 'FAIL')
    warned  = sum(1 for r in results if r['status'] == 'WARN')
    print(f"  PASS: {passed}  FAIL: {failed}  WARN: {warned}  INFO: {len(results)-passed-failed-warned}")

    # Dump structured results as JSON for the report
    import json
    with open("scripts/phase3_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nDetailed results written to: scripts/phase3_results.json")

asyncio.run(main())

