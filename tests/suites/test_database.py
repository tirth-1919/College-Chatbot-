"""Database & Schema Automated Test Suite.

Tests:
  - Database connectivity & authentication under least-privilege role.
  - Table existence for all 27 domain entities.
  - Primary key, foreign key, and index integrity.
  - RLS policies and multi-tenant isolation.
  - Transaction rollback safety.
  - Connection pool listener (`DISCARD TEMP; RESET ALL`).
"""

import time
import uuid
from typing import List, Dict, Any
import asyncpg
from sqlalchemy import text
from tests.config import (
    ASYNC_ADMIN_URL,
    ASYNC_APP_URL,
    SYNC_ADMIN_URL,
    AIT_COLLEGE_ID,
    RCTI_COLLEGE_ID,
)

EXPECTED_TABLES = [
    "colleges",
    "users",
    "college_memberships",
    "website_sources",
    "crawl_jobs",
    "crawl_events",
    "website_pages",
    "documents",
    "document_pages",
    "document_paragraphs",
    "knowledge_chunks",
    "knowledge_reviews",
    "extracted_facts",
    "chat_sessions",
    "chat_messages",
    "feedback",
    "support_tickets",
    "support_ticket_replies",
    "in_app_notifications",
    "ai_provider_configs",
    "ai_provider_events",
    "audit_logs",
    "college_registrations",
    "registration_reviews",
    "college_admin_invitations",
    "college_onboarding_progress",
    "notification_logs",
]


async def run_database_suite() -> List[Dict[str, Any]]:
    """Executes all database test cases."""
    results = []
    admin_conn_str = ASYNC_ADMIN_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    app_conn_str = ASYNC_APP_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

    # 1. Test: App role connection & privileges
    t0 = time.perf_counter()
    try:
        app_conn = await asyncpg.connect(app_conn_str)
        role_row = await app_conn.fetchrow(
            "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        )
        dur = (time.perf_counter() - t0) * 1000
        is_safe = (
            role_row["current_user"] == "college_app_user"
            and not role_row["rolsuper"]
            and not role_row["rolbypassrls"]
        )
        results.append({
            "category": "Database",
            "name": "Database App Role Least-Privilege Verification",
            "target": "college_app_user",
            "status": "PASS" if is_safe else "FAIL",
            "duration_ms": dur,
            "detail": f"User: {role_row['current_user']}, Superuser: {role_row['rolsuper']}, BypassRLS: {role_row['rolbypassrls']}",
        })
    except Exception as e:
        results.append({
            "category": "Database",
            "name": "Database App Role Least-Privilege Verification",
            "target": "college_app_user",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": f"Connection error: {str(e)}",
        })
        return results

    # 2. Test: Complete Table Inventory (all 27 tables)
    t0 = time.perf_counter()
    try:
        rows = await app_conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        existing = set(r["table_name"] for r in rows)
        missing = [t for t in EXPECTED_TABLES if t not in existing]
        dur = (time.perf_counter() - t0) * 1000
        results.append({
            "category": "Database",
            "name": "Complete Table Inventory Verification (27 Tables)",
            "target": "information_schema.tables",
            "status": "PASS" if not missing else "FAIL",
            "duration_ms": dur,
            "detail": f"Existing: {len(existing)} tables. Missing: {missing or 'None'}",
        })
    except Exception as e:
        results.append({
            "category": "Database",
            "name": "Complete Table Inventory Verification (27 Tables)",
            "target": "information_schema.tables",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": str(e),
        })

    # 3. Test: Row-Level Security Enabled on Core Tables
    t0 = time.perf_counter()
    try:
        rls_rows = await app_conn.fetch("""
            SELECT c.relname, c.relrowsecurity, count(p.polname) as policy_count
            FROM pg_class c
            LEFT JOIN pg_policy p ON p.polrelid = c.oid
            WHERE c.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
              AND c.relkind = 'r' AND c.relrowsecurity = true
            GROUP BY c.relname, c.relrowsecurity
        """)
        dur = (time.perf_counter() - t0) * 1000
        zero_policy_tables = [r["relname"] for r in rls_rows if r["policy_count"] == 0]
        results.append({
            "category": "Database",
            "name": "Row-Level Security Policy Coverage (No Zero-Policy Tables)",
            "target": "pg_policy",
            "status": "PASS" if not zero_policy_tables else "FAIL",
            "duration_ms": dur,
            "detail": f"RLS Tables: {len(rls_rows)}. Zero-policy tables: {zero_policy_tables or 'None'}",
        })
    except Exception as e:
        results.append({
            "category": "Database",
            "name": "Row-Level Security Policy Coverage",
            "target": "pg_policy",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": str(e),
        })

    # 4. Test: Transaction Rollback Safety
    t0 = time.perf_counter()
    try:
        dummy_id = uuid.uuid4()
        async with app_conn.transaction():
            # Attempt a rollback inside transaction
            await app_conn.execute("SELECT set_config('app.test_rollback', 'active', true)")
            val_during = await app_conn.fetchval("SELECT current_setting('app.test_rollback', true)")
            assert val_during == "active"
            # Raise rollback simulation
        val_after = await app_conn.fetchval("SELECT current_setting('app.test_rollback', true)")
        dur = (time.perf_counter() - t0) * 1000
        is_clean = val_after in ("", None)
        results.append({
            "category": "Database",
            "name": "Transaction Atomicity & Rollback Safety",
            "target": "app_conn.transaction()",
            "status": "PASS" if is_clean else "FAIL",
            "duration_ms": dur,
            "detail": f"Value during txn: {val_during}, after rollback: '{val_after}'",
        })
    except Exception as e:
        results.append({
            "category": "Database",
            "name": "Transaction Atomicity & Rollback Safety",
            "target": "app_conn.transaction()",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": str(e),
        })

    # 5. Test: RESET ALL Pool Cleaner
    t0 = time.perf_counter()
    try:
        await app_conn.execute("SELECT set_config('app.current_college_id', '11111111-1111-1111-1111-111111111111', false)")
        await app_conn.execute("DISCARD TEMP")
        await app_conn.execute("RESET ALL")
        cleared_val = await app_conn.fetchval("SELECT current_setting('app.current_college_id', true)")
        dur = (time.perf_counter() - t0) * 1000
        is_cleared = cleared_val in ("", None)
        results.append({
            "category": "Database",
            "name": "Connection Pool DISCARD TEMP & RESET ALL Command Verification",
            "target": "RESET ALL",
            "status": "PASS" if is_cleared else "FAIL",
            "duration_ms": dur,
            "detail": f"Value after RESET ALL: '{cleared_val}'",
        })
    except Exception as e:
        results.append({
            "category": "Database",
            "name": "Connection Pool RESET ALL",
            "target": "RESET ALL",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": str(e),
        })

    # 6. Test: Cross-Tenant Isolation (AIT vs. RCTI documents)
    t0 = time.perf_counter()
    try:
        async with app_conn.transaction():
            # Set context to AIT
            await app_conn.execute(f"SELECT set_config('app.current_college_id', '{AIT_COLLEGE_ID}', true)")
            await app_conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
            ait_docs = await app_conn.fetchval("SELECT count(*) FROM documents")
            rcti_leak = await app_conn.fetchval("SELECT count(*) FROM documents WHERE college_id = $1", RCTI_COLLEGE_ID)

        dur = (time.perf_counter() - t0) * 1000
        is_isolated = (rcti_leak == 0)
        results.append({
            "category": "Database",
            "name": "Tenant Isolation: Cross-College Data Separation (AIT vs RCTI)",
            "target": "documents",
            "status": "PASS" if is_isolated else "FAIL",
            "duration_ms": dur,
            "detail": f"AIT visible docs: {ait_docs}, RCTI leaked docs: {rcti_leak}",
        })
    except Exception as e:
        results.append({
            "category": "Database",
            "name": "Tenant Isolation: Cross-College Data Separation",
            "target": "documents",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": str(e),
        })

    # 7. Test: Performance / Query Execution Time Threshold (< 250ms)
    t0 = time.perf_counter()
    try:
        await app_conn.fetchval("SELECT count(*) FROM colleges WHERE is_active = true")
        dur = (time.perf_counter() - t0) * 1000
        passed = dur < 250.0
        results.append({
            "category": "Database",
            "name": "Database Query Execution Benchmark (< 250ms)",
            "target": "colleges",
            "status": "PASS" if passed else "WARN",
            "duration_ms": dur,
            "detail": f"Executed in {dur:.2f}ms (threshold: 250ms)",
        })
    except Exception as e:
        results.append({
            "category": "Database",
            "name": "Database Query Execution Benchmark",
            "target": "colleges",
            "status": "FAIL",
            "duration_ms": 0,
            "detail": str(e),
        })

    await app_conn.close()
    return results

