import asyncio, os
from dotenv import load_dotenv
import asyncpg
load_dotenv()
APP_URL = os.environ.get("DATABASE_APP_ROLE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def test_user_rls():
    conn = await asyncpg.connect(APP_URL)
    print("=== LIVE RLS TEST: USERS & MEMBERSHIPS (college_app_user) ===")
    
    # 1. Anonymous (no GUCs set)
    await conn.execute("SELECT set_config('app.current_college_id', '', true)")
    await conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
    await conn.execute("SELECT set_config('app.current_user_id', '', true)")
    users = await conn.fetch("SELECT email FROM users")
    print(f"1. Anonymous context: visible users = {[u['email'] for u in users]} (expected: [])")
    assert len(users) == 0, f"Expected 0 users, got {len(users)}"
    
    # 2. Student context (user_id = ccc...)
    student_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    await conn.execute(f"SELECT set_config('app.current_user_id', '{student_id}', true)")
    await conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
    await conn.execute("SELECT set_config('app.current_college_id', '', true)")
    users = await conn.fetch("SELECT email FROM users")
    print(f"2. Student context (student@gmail.com): visible users = {[u['email'] for u in users]} (expected: ['student@gmail.com'])")
    assert len(users) == 1 and users[0]['email'] == 'student@gmail.com', f"Expected only student, got {users}"
    
    # 3. Student reading memberships
    mems = await conn.fetch("SELECT * FROM college_memberships")
    print(f"   Student reading memberships: visible = {len(mems)} (expected: 0 because student has no memberships)")
    assert len(mems) == 0
    
    # 4. AIT Admin context (user_id = bbb..., college_id = 111...)
    ait_admin_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    ait_id = "11111111-1111-1111-1111-111111111111"
    await conn.execute(f"SELECT set_config('app.current_user_id', '{ait_admin_id}', true)")
    await conn.execute(f"SELECT set_config('app.current_college_id', '{ait_id}', true)")
    await conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
    users = await conn.fetch("SELECT email FROM users")
    print(f"3. AIT Admin context (admin@aitindia.in): visible users = {[u['email'] for u in users]} (expected: ['admin@aitindia.in'])")
    assert 'admin@aitindia.in' in [u['email'] for u in users]
    assert 'student@gmail.com' not in [u['email'] for u in users], "LEAK! AIT admin can see student"
    assert 'superadmin@platform.com' not in [u['email'] for u in users], "LEAK! AIT admin can see super admin"
    
    # 5. AIT Admin reading memberships
    mems = await conn.fetch("SELECT college_id, user_id FROM college_memberships")
    print(f"   AIT Admin reading memberships: visible = {len(mems)} (expected: 1 AIT membership)")
    assert len(mems) == 1 and str(mems[0]['college_id']) == ait_id
    
    # 6. RCTI Admin context (college_id = 222... - different tenant)
    rcti_id = "22222222-2222-2222-2222-222222222222"
    # An admin assigned to RCTI (let's say student ID is used as an arbitrary user for test)
    await conn.execute(f"SELECT set_config('app.current_user_id', '{student_id}', true)")
    await conn.execute(f"SELECT set_config('app.current_college_id', '{rcti_id}', true)")
    await conn.execute("SELECT set_config('app.is_super_admin', 'false', true)")
    mems = await conn.fetch("SELECT college_id, user_id FROM college_memberships")
    print(f"4. RCTI Admin reading memberships: visible = {len(mems)} (expected: 0 - cannot see AIT membership)")
    assert len(mems) == 0, f"LEAK! RCTI admin can see AIT memberships: {mems}"
    
    # 7. Super Admin context (is_super_admin = true)
    super_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    await conn.execute(f"SELECT set_config('app.current_user_id', '{super_id}', true)")
    await conn.execute("SELECT set_config('app.is_super_admin', 'true', true)")
    await conn.execute("SELECT set_config('app.current_college_id', '', true)")
    users = await conn.fetch("SELECT email FROM users")
    print(f"5. Super Admin context: visible users = {len(users)} (expected: 3 users)")
    assert len(users) == 3, f"Expected 3 users, got {len(users)}"
    
    mems = await conn.fetch("SELECT college_id, user_id FROM college_memberships")
    print(f"   Super Admin reading memberships: visible = {len(mems)} (expected: 1 membership)")
    assert len(mems) == 1
    
    await conn.close()
    print("\n>>> ALL LIVE USER & MEMBERSHIP RLS TESTS PASSED STOLIDLY! <<<")

asyncio.run(test_user_rls())

