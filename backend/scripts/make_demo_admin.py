"""One-off: promote 1@gmail.com to ADMIN and set its password to the demo value '1'."""
import sys
sys.path.insert(0, ".")

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.user import User

db = SessionLocal()
user = db.query(User).filter(User.email == "1@gmail.com").first()
if not user:
    user = User(email="1@gmail.com", hashed_password=get_password_hash("1"), full_name="Demo Admin", role="ADMIN", is_active=True, is_verified=True)
    db.add(user)
else:
    user.role = "ADMIN"
    user.hashed_password = get_password_hash("1")
    user.is_active = True
    user.failed_login_attempts = 0
    user.locked_until = None
    user.mfa_enabled = False
db.commit()
print("1@gmail.com is now ADMIN with password '1'")
db.close()
