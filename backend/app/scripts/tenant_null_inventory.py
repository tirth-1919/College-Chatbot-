"""Read-only tenant NULL inventory and deterministic ownership report.

This command never assigns ownership. It reports NULL rows as AMBIGUOUS unless
there is an explicit, reviewable parent relationship proving a tenant.
"""
import json
from sqlalchemy import text
from backend.app.core.database import SessionLocal, engine
TABLES = [
    "ait_entities", "ait_knowledge_versions", "website_snapshots", "knowledge_gaps",
    "message_feedback", "documents", "document_chunks", "conversations", "ait_images",
    "knowledge_conflicts", "security_events", "ai_usage_logs",
]

def inventory():
    db = SessionLocal()
    try:
        result = {}
        for table in TABLES:
            names = {row[0] for row in db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))} if engine.dialect.name == "sqlite" else set()
            if engine.dialect.name == "sqlite" and table not in names:
                continue
            total = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            null_count = db.execute(text(f"SELECT COUNT(*) FROM {table} WHERE college_id IS NULL")).scalar_one()
            by_tenant = db.execute(text(f"SELECT college_id, COUNT(*) FROM {table} WHERE college_id IS NOT NULL GROUP BY college_id")).all()
            result[table] = {"total": total, "null_tenant": null_count, "tenants": {str(row[0]): row[1] for row in by_tenant}, "null_classification": "AMBIGUOUS" if null_count else "NONE"}
        return result
    finally:
        db.close()

if __name__ == "__main__":
    print(json.dumps(inventory(), indent=2, default=str))
