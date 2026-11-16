import asyncio, sys
sys.path.insert(0, "backend")
from dotenv import load_dotenv
load_dotenv()

async def test_all_logins():
    from app.services.auth_service import AuthService
    from app.database.session import AsyncSessionFactory
    from app.schemas.auth import LoginRequest
    
    users_to_test = [
        ("student@gmail.com", "Admin@12345", "STUDENT"),
        ("admin@aitindia.in", "Admin@12345", "COLLEGE_ADMIN"),
        ("superadmin@platform.com", "Admin@12345", "SUPER_ADMIN"),
    ]
    
    async with AsyncSessionFactory() as session:
        auth_service = AuthService(session)
        for email, pwd, expected_role in users_to_test:
            res = await auth_service.authenticate(LoginRequest(email=email, password=pwd))
            print(f"[PASS] {email} logged in -> role={res.role} college_id={res.college_id}")
            assert res.role == expected_role

asyncio.run(test_all_logins())
