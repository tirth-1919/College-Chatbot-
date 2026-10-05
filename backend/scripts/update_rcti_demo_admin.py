# Controlled local/demo-only RCTI College Admin credential update.

# This script intentionally does not alter global password validation or any
# production account. The password is supplied through the process environment
# and is hashed with the application's normal bcrypt utility before persistence.
import os
from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.college import College
from backend.app.models.user import User
EMAIL = "rc@gmail.com"
LEGACY_EMAIL = "4@gmail.com"


def update_rcti_demo_admin() -> None:
    if os.getenv("ENVIRONMENT", "production").lower() in {"production", "prod"}:
        raise RuntimeError("This controlled account update is local/demo-only.")
    password = os.environ.get("RCTI_ADMIN_PASSWORD")
    if password != "rc":
        raise RuntimeError("Set RCTI_ADMIN_PASSWORD=rc for this local/demo update.")

    db = SessionLocal()
    try:
        college = db.query(College).filter(
            College.name == "R.C. Technical Institute",
            College.code == "RCTI",
        ).one()
        target = db.query(User).filter(User.email == EMAIL).one_or_none()
        if target is None:
            target = db.query(User).filter(
                User.email == LEGACY_EMAIL,
                User.college_id == college.id,
                User.role == "COLLEGE_ADMIN",
            ).one()
            target.email = EMAIL
        if target.college_id != college.id or target.role != "COLLEGE_ADMIN":
            raise RuntimeError("Refusing to modify a non-RCTI or non-college-admin account.")

        # Remove only the known duplicate RCTI identity, never AIT or super-admin rows.
        duplicate = db.query(User).filter(
            User.email == LEGACY_EMAIL,
            User.college_id == college.id,
            User.role == "COLLEGE_ADMIN",
            User.id != target.id,
        ).one_or_none()
        if duplicate:
            db.delete(duplicate)

        target.hashed_password = get_password_hash(password)
        target.role = "COLLEGE_ADMIN"
        target.college_id = college.id
        target.is_active = True
        target.must_change_password = False
        permissions = list(target.permissions) if isinstance(target.permissions, list) else []
        if "website.sync" not in permissions:
            permissions.append("website.sync")
        target.permissions = permissions
        db.commit()
        print(f"updated_user_id={target.id}")
        print(f"college_id={college.id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_rcti_demo_admin()
