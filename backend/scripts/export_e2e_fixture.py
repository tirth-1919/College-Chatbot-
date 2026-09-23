"""Export non-secret, database-derived expectations for the browser acceptance suite."""
import json
import os
import sys
from pathlib import Path

# Allow `python backend/scripts/export_e2e_fixture.py` from the repository root,
# matching the documented E2E command.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def _value(entity, *names):
    details = entity.details or {}
    return next((str(details[name]) for name in names if details.get(name)), None)


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if "ait_e2e" not in database_url.lower():
        raise SystemExit("Refusing fixture export: DATABASE_URL must name a dedicated *ait_e2e* database.")

    from backend.app.core.database import SessionLocal
    from backend.app.models.knowledge import AitEntity

    db = SessionLocal()
    try:
        bca = db.query(AitEntity).filter(AitEntity.code == "BCA", AitEntity.is_verified == True).first()
        faculty = next((item for item in db.query(AitEntity).filter(AitEntity.category == "faculty", AitEntity.is_verified == True).all()
                        if "dbms" in str(item.details).lower()), None)
        entities = db.query(AitEntity).filter(AitEntity.is_verified == True).all()
        if not bca or not faculty:
            raise SystemExit("Verified BCA and DBMS faculty fixtures are required in the E2E database.")
        fixture = {
            "bca_fee": _value(bca, "annual_fees", "sem_fees"),
            "dbms_faculty": faculty.name,
            "has_ai_offering": any("ai" in str(item.details).lower() or "artificial intelligence" in item.name.lower() for item in entities),
        }
        if not fixture["bca_fee"]:
            raise SystemExit("The verified BCA fixture has no fee value.")
        target = Path(os.getenv("AIT_E2E_FIXTURE", "apps/user-web/e2e/.generated-expectations.json"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
        print(f"Wrote database-derived E2E expectations to {target}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
