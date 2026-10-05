# Non-destructive tenant-aware uniqueness migration for website snapshots.
# This migration is explicit and is not run automatically at import or startup.
# Existing rows, including NULL-tenant legacy rows, are preserved.
# Operators must review duplicates before applying it in a maintenance window.
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
INDEX_NAME = "uq_website_snapshots_college_url"


def inspect_snapshot_duplicates(db: Session):
    # Return duplicate (college_id, url) groups for operator review.
    return db.execute(text("""
        SELECT college_id, url, COUNT(*) AS row_count
        FROM website_snapshots
        GROUP BY college_id, url
        HAVING COUNT(*) > 1
        ORDER BY college_id, url
    """)).mappings().all()


def apply_snapshot_uniqueness(db: Session) -> None:
    # Create the composite unique index without deleting or merging rows.
    # Raise on duplicates so an operator can resolve them explicitly rather
    # than silently changing production data.
    duplicates = inspect_snapshot_duplicates(db)
    if duplicates:
        raise RuntimeError(
            "Cannot apply website snapshot uniqueness: duplicate tenant/url "
            "rows require explicit review before migration."
        )

    dialect = db.bind.dialect.name
    if dialect == "sqlite":
        db.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} "
            "ON website_snapshots (college_id, url)"
        ))
    elif dialect == "postgresql":
        db.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} "
            "ON website_snapshots (college_id, url)"
        ))
    else:
        raise RuntimeError(f"Unsupported database dialect: {dialect}")
    db.commit()


def migration_status(db: Session) -> dict:
    inspector = inspect(db.bind)
    indexes = inspector.get_indexes("website_snapshots")
    constraints = inspector.get_unique_constraints("website_snapshots")
    return {
        "composite_index_present": any(i.get("name") == INDEX_NAME for i in indexes),
        "composite_constraint_present": any(c.get("name") == INDEX_NAME for c in constraints),
        "duplicate_groups": [dict(row) for row in inspect_snapshot_duplicates(db)],
    }
