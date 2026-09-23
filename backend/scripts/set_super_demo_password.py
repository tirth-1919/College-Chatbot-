"""Dev-only helper (mirrors backend/scripts/make_demo_admin.py):

Promotes 3@gmail.com to SUPER_ADMIN and sets its password to the demo
value '3'. Never used in production; matches the demo user scheme
1@gmail.com/'1', 2@gmail.com/'2', 3@gmail.com/'3'.
"""
from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.user import User

EMAIL = "3@gmail.com"
PASSWORD = "3"

db = SessionLocal()
user = db.query(User).filter(User.email == EMAIL).first()
if not user:
    user = User(email=EMAIL, hashed_password=get_password_hash(PASSWORD),
                full_name="Demo Super Admin", role="SUPER_ADMIN",
                college_id=None, is_active=True, is_verified=True)
    db.add(user)
    print(f"{EMAIL} created as SUPER_ADMIN with password '{PASSWORD}'")
else:
    user.role = "SUPER_ADMIN"
    user.college_id = None
    user.hashed_password = get_password_hash(PASSWORD)
    user.is_active = True
    print(f"{EMAIL} is now SUPER_ADMIN with password '{PASSWORD}'")
db.commit()
db.close()
