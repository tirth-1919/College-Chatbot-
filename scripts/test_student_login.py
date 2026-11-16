import asyncio, sys
sys.path.insert(0, "backend")
from dotenv import load_dotenv
load_dotenv()

async def test_student_login():
    from app.services.auth_service import AuthService
    from app.database.session import AsyncSessionFactory
    from app.schemas.auth import LoginRequest
    
    async with AsyncSessionFactory() as session:
        auth_service = AuthService(session)
        print("Testing student login on backend...")
        try:
            token_response = await auth_service.authenticate(
                LoginRequest(email="student@gmail.com", password="Admin@12345")
            )
            print(f"Login success! Access token: {token_response.access_token[:20]}... Role: {token_response.role}")
            
            # Now test get_current_user / auth/me dependency with this token
            from app.dependencies.auth import get_current_user
            from fastapi.security import HTTPAuthorizationCredentials
            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_response.access_token)
            
            user = await get_current_user(auth_credentials=creds, session=session)
            print(f"User from get_current_user: {user.email} (role: {user.role}, is_verified: {user.is_verified})")
        except Exception as e:
            print(f"ERROR: {e}")

asyncio.run(test_student_login())
