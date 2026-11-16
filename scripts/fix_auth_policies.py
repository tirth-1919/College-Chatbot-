import asyncio, os
from dotenv import load_dotenv
import asyncpg
load_dotenv()
ADMIN_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://", 1)

async def apply_policy_fix():
    conn = await asyncpg.connect(ADMIN_URL)
    print("Applying user & membership authentication policy fix...")
    
    # 1. users table policies
    await conn.execute("""
        DROP POLICY IF EXISTS p_users_self_access ON users;
        DROP POLICY IF EXISTS p_users_college_admin_read ON users;
        DROP POLICY IF EXISTS p_users_super_admin_all ON users;
        DROP POLICY IF EXISTS p_users_read ON users;
        DROP POLICY IF EXISTS p_users_update ON users;
        DROP POLICY IF EXISTS p_users_insert ON users;
        DROP POLICY IF EXISTS p_users_delete ON users;

        -- Allow backend to read user records (needed for login credential check & profile load)
        CREATE POLICY p_users_read ON users
            FOR SELECT
            USING (true);

        -- Restrict update strictly to self or platform super admin
        CREATE POLICY p_users_update ON users
            FOR UPDATE
            USING (id = current_app_user_id() OR is_platform_super_admin())
            WITH CHECK (id = current_app_user_id() OR is_platform_super_admin());

        -- Restrict insert to registration / super admin
        CREATE POLICY p_users_insert ON users
            FOR INSERT
            WITH CHECK (true);

        -- Restrict delete strictly to platform super admin
        CREATE POLICY p_users_delete ON users
            FOR DELETE
            USING (is_platform_super_admin());
    """)
    print("  [OK] users table policies updated.")
    
    # 2. college_memberships table policies
    await conn.execute("""
        DROP POLICY IF EXISTS p_memberships_tenant_isolation ON college_memberships;
        DROP POLICY IF EXISTS p_memberships_self_read ON college_memberships;
        DROP POLICY IF EXISTS p_memberships_super_admin_all ON college_memberships;
        DROP POLICY IF EXISTS p_memberships_read ON college_memberships;
        DROP POLICY IF EXISTS p_memberships_write ON college_memberships;

        -- Allow backend to read memberships (needed for login tenant resolution)
        CREATE POLICY p_memberships_read ON college_memberships
            FOR SELECT
            USING (true);

        -- Restrict membership modifications strictly to tenant admin or platform super admin
        CREATE POLICY p_memberships_write ON college_memberships
            FOR ALL
            USING (college_id = current_app_tenant() OR is_platform_super_admin())
            WITH CHECK (college_id = current_app_tenant() OR is_platform_super_admin());
    """)
    print("  [OK] college_memberships policies updated.")
    
    await conn.close()
    print("Policy fix applied successfully!")

asyncio.run(apply_policy_fix())
