"""Set a known admin password for live verification testing (dev machine only).
Password is taken from env var TEST_ADMIN_PASSWORD and never printed.
"""
import os
import sys

sys.path.insert(0, ".")

from backend.app.core.database import SessionLocal
from backend.app.core.security import get_password_hash
from backend.app.models.user import User

password = os.getenv("TEST_ADMIN_PASSWORD", "")
assert password, "set TEST_ADMIN_PASSWORD env var"

db = SessionLocal()
admin = db.query(User).filter(User.email == "admin@aitindia.in").first()
assert admin, "admin not found"
admin.hashed_password = get_password_hash(password)
db.commit()
print("admin password updated (value not printed)")
db.close()
