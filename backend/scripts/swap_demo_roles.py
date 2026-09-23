"""One-off: swap roles of demo accounts (1@gmail.com -> STUDENT, 2@gmail.com -> ADMIN)."""
from backend.app.core.database import SessionLocal
from backend.app.models.user import User

db = SessionLocal()
try:
    u1 = db.query(User).filter(User.email == "1@gmail.com").first()
    u2 = db.query(User).filter(User.email == "2@gmail.com").first()
    if u1:
        u1.role = "STUDENT"
        u1.full_name = "Demo User"
    if u2:
        u2.role = "ADMIN"
        u2.full_name = "Demo Admin 2"
    db.commit()
    print("1@gmail.com ->", u1.role if u1 else "NOT FOUND")
    print("2@gmail.com ->", u2.role if u2 else "NOT FOUND")
finally:
    db.close()
