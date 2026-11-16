import asyncio, sys, uuid
sys.path.insert(0, "backend")
from dotenv import load_dotenv
load_dotenv()

async def test_get_by_id():
    from app.database.session import AsyncSessionFactory
    from app.repositories.user_repository import UserRepository
    
    async with AsyncSessionFactory() as session:
        repo = UserRepository(session)
        # student user id: cccccccc-cccc-cccc-cccc-cccccccccccc
        uid = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
        u = await repo.get_by_id(uid)
        print(f"User retrieved by id BEFORE set_rls_context: {u}")
        
        # Now set rls context and try again
        from app.database.session import set_rls_context
        await set_rls_context(session, college_id=None, user_id=uid, is_super_admin=False)
        u2 = await repo.get_by_id(uid)
        print(f"User retrieved by id AFTER set_rls_context: {u2}")

asyncio.run(test_get_by_id())
