"""Remove only generated E2E student data from an explicitly named E2E database."""
import os
import sys
from pathlib import Path

# Support the documented `python backend/scripts/cleanup_e2e_data.py` command
# from the repository root as well as Playwright global teardown.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if os.getenv("AIT_E2E_CLEANUP") != "1" or "ait_e2e" not in database_url.lower():
        raise SystemExit("Refusing cleanup: set AIT_E2E_CLEANUP=1 and use a dedicated *ait_e2e* database URL.")

    from backend.app.core.database import SessionLocal
    from backend.app.models.user import User

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.email.like("e2e-student-%@example.test")).all()
        for user in users:
            db.delete(user)
        db.commit()
        print(f"Removed {len(users)} generated E2E student account(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
