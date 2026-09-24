"""
Repair migration: fix column-shifted rows in `knowledge_categories`.

Root cause of the bug this repairs
----------------------------------
When the SQLite table was recreated by migrations/fix_category_uniqueness.py
(and by later re-runs of the copy step), the INSERT ... SELECT used a column
list whose order did not match the physical order of the OLD table's columns
in one code path. The result: for the 22 rows that existed at migration time,
`updated_by` ended up holding the old `updated_at` timestamp and `updated_at`
ended up holding the AIT tenant id ("ait-default-tenant-0001").

SQLAlchemy then fails with:
    ValueError: Invalid isoformat string: 'ait-default-tenant-0001'
when any code loads those rows (e.g. admin list_categories), so
GET /api/v1/admin/knowledge-db/categories returned a broken non-JSON response.

This migration is:
- Non-destructive: only rewrites obviously-shifted column values in place,
  never deletes rows or tables.
- Idempotent: the detection predicate matches nothing once repaired, so it is
  a no-op on subsequent runs.
"""
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

TENANT_ID = "ait-default-tenant-0001"


def _is_iso_timestamp(value) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def repair_knowledge_categories(db: Session) -> int:
    engine_dialect = db.bind.dialect.name
    inspector_names = __import__("sqlalchemy").inspect(db.bind).get_table_names()
    if "knowledge_categories" not in inspector_names:
        print("[MIGRATION] knowledge_categories table does not exist, nothing to repair")
        return 0

    rows = db.execute(text(
        "SELECT id, updated_by, updated_at, created_at FROM knowledge_categories"
    )).fetchall()

    fixed = 0
    for row_id, updated_by, updated_at, created_at in rows:
        # Heuristic signature of the column shift:
        #   updated_by holds an ISO timestamp (belongs to updated_at)
        #   updated_at holds the tenant id (NOT a timestamp)
        if not _is_iso_timestamp(updated_by):
            continue
        if _is_iso_timestamp(updated_at) or updated_at is None:
            continue

        db.execute(text(
            "UPDATE knowledge_categories "
            "SET updated_at = :updated_at, updated_by = NULL "
            "WHERE id = :rid"
        ), {"updated_at": updated_by, "rid": row_id})
        fixed += 1

    # If created_at also got shifted for those rows, restore it from
    # updated_at's previous timestamp value when available.
    if fixed:
        rows2 = db.execute(text(
            "SELECT id, created_at, updated_at FROM knowledge_categories"
        )).fetchall()
        for row_id, created_at, updated_at in rows2:
            if created_at is None and updated_at is not None:
                db.execute(text(
                    "UPDATE knowledge_categories SET created_at = :created_at "
                    "WHERE id = :rid"
                ), {"created_at": updated_at, "rid": row_id})

    if fixed:
        db.commit()
        print(f"[MIGRATION] Repaired {fixed} column-shifted rows in knowledge_categories ({engine_dialect})")
    else:
        print("[MIGRATION] knowledge_categories rows are clean, nothing to repair")
    return fixed


if __name__ == "__main__":
    from backend.app.core.database import SessionLocal
    db = SessionLocal()
    try:
        repair_knowledge_categories(db)
    finally:
        db.close()
