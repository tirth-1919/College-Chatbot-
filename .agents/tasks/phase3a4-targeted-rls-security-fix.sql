-- PROPOSED ONLY: do not run against production without explicit approval.
-- Apply as the table owner in a reviewed maintenance window after validation
-- against an isolated PostgreSQL database.

BEGIN;

-- A dedicated exact-email lookup preserves login/verification/reset flows
-- without granting direct cross-user SELECT access on public.users.
CREATE OR REPLACE FUNCTION public.lookup_user_by_email_for_auth(p_email text)
RETURNS SETOF public.users
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT u.*
    FROM public.users AS u
    WHERE lower(u.email) = lower(btrim(p_email))
    LIMIT 1;
$function$;

-- Invitation acceptance starts unauthenticated. Resolve only the exact
-- bearer token; subsequent reads/writes run with the validated college/user
-- context established by the application.
CREATE OR REPLACE FUNCTION public.lookup_college_invitation_by_token(p_token text)
RETURNS SETOF public.college_admin_invitations
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT i.*
    FROM public.college_admin_invitations AS i
    WHERE i.invitation_token = p_token
    LIMIT 1;
$function$;

CREATE OR REPLACE FUNCTION public.is_current_college_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT EXISTS (
        SELECT 1
        FROM public.college_memberships AS cm
        JOIN public.users AS u ON u.id = cm.user_id
        WHERE cm.college_id = public.current_app_tenant()
          AND cm.user_id = public.current_app_user_id()
          AND cm.role_in_college::text = 'ADMIN'
          AND u.role::text = 'COLLEGE_ADMIN'
          AND u.is_active = TRUE
    );
$function$;

CREATE OR REPLACE FUNCTION public.can_provision_college_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT COALESCE(
        current_setting('app.pending_admin_provisioning', TRUE) = 'true'
        AND public.current_app_user_id() IS NOT NULL
        AND NULLIF(current_setting('app.pending_admin_email', TRUE), '') IS NOT NULL
        AND (
            EXISTS (
                SELECT 1
                FROM public.colleges AS c
                WHERE c.id = public.current_app_tenant()
                  AND c.status::text = 'PENDING'
                  AND c.is_active = FALSE
            )
            OR EXISTS (
                SELECT 1
                FROM public.college_admin_invitations AS i
                WHERE i.email = NULLIF(current_setting('app.pending_admin_email', TRUE), '')
                  AND i.college_id = public.current_app_tenant()
                  AND i.status::text = 'PENDING'
                  AND i.expires_at > statement_timestamp()
            )
        ),
        FALSE
    );
$function$;

CREATE OR REPLACE FUNCTION public.can_provision_membership_role(p_role text)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $function$
    SELECT COALESCE(
        current_setting('app.pending_admin_provisioning', TRUE) = 'true'
        AND public.current_app_user_id() IS NOT NULL
        AND (
            (
                p_role = 'ADMIN'
                AND EXISTS (
                    SELECT 1
                    FROM public.colleges AS c
                    WHERE c.id = public.current_app_tenant()
                      AND c.status::text = 'PENDING'
                      AND c.is_active = FALSE
                )
            )
            OR EXISTS (
                SELECT 1
                FROM public.college_admin_invitations AS i
                WHERE i.email = NULLIF(current_setting('app.pending_admin_email', TRUE), '')
                  AND i.college_id = public.current_app_tenant()
                  AND i.role_in_college::text = p_role
                  AND i.status::text = 'PENDING'
                  AND i.expires_at > statement_timestamp()
            )
        ),
        FALSE
    );
$function$;

REVOKE ALL ON FUNCTION public.is_current_college_admin() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.can_provision_college_admin() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.can_provision_membership_role(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.lookup_user_by_email_for_auth(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.lookup_college_invitation_by_token(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_current_college_admin() TO college_app_user;
GRANT EXECUTE ON FUNCTION public.can_provision_college_admin() TO college_app_user;
GRANT EXECUTE ON FUNCTION public.can_provision_membership_role(text) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.lookup_college_invitation_by_token(text) TO college_app_user;

-- users: authentication may read exactly the email currently being checked;
-- authenticated users may read themselves; verified platform admins may read all.
DROP POLICY IF EXISTS p_users_read ON public.users;
CREATE POLICY p_users_read ON public.users
    FOR SELECT
    USING (
        id = public.current_app_user_id()
        OR public.is_platform_super_admin()
    );

-- Registration can create only a self-owned student row. College admin
-- provisioning is limited to the validated pending-onboarding/invitation flow.
DROP POLICY IF EXISTS p_users_insert ON public.users;
CREATE POLICY p_users_insert ON public.users
    FOR INSERT
    WITH CHECK (
        (
            role::text = 'STUDENT'
            AND id = public.current_app_user_id()
            AND is_verified = FALSE
            AND is_active = TRUE
        )
        OR (
            role::text = 'COLLEGE_ADMIN'
            AND id = public.current_app_user_id()
            AND email = NULLIF(current_setting('app.pending_admin_email', TRUE), '')
            AND public.can_provision_college_admin()
        )
        OR public.is_platform_super_admin()
    );

-- The trigger prevents self-service role or activation changes while allowing
-- verified Super Admin actions and the narrowly scoped invitation promotion.
CREATE OR REPLACE FUNCTION public.prevent_user_privilege_self_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, pg_temp
AS $function$
BEGIN
    IF OLD.id = public.current_app_user_id()
       AND NOT public.is_platform_super_admin() THEN
        IF NEW.is_active IS DISTINCT FROM OLD.is_active THEN
            RAISE EXCEPTION 'Users cannot change their own activation state'
                USING ERRCODE = '42501';
        END IF;

        IF NEW.is_verified IS DISTINCT FROM OLD.is_verified
           AND current_setting('app.email_verification_authorized', TRUE)
               IS DISTINCT FROM 'true'
           AND NOT public.can_provision_college_admin() THEN
            RAISE EXCEPTION 'Email verification must use the validated verification flow'
                USING ERRCODE = '42501';
        END IF;

        IF NEW.role IS DISTINCT FROM OLD.role THEN
            IF NOT (
                OLD.role::text = 'STUDENT'
                AND NEW.role::text = 'COLLEGE_ADMIN'
                AND NEW.email = NULLIF(current_setting('app.pending_admin_email', TRUE), '')
                AND public.can_provision_college_admin()
            ) THEN
                RAISE EXCEPTION 'Users cannot change their own role'
                    USING ERRCODE = '42501';
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS trg_prevent_user_privilege_self_change ON public.users;
CREATE TRIGGER trg_prevent_user_privilege_self_change
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.prevent_user_privilege_self_change();

DROP POLICY IF EXISTS p_users_update ON public.users;
CREATE POLICY p_users_update ON public.users
    FOR UPDATE
    USING (
        id = public.current_app_user_id()
        OR public.is_platform_super_admin()
    )
    WITH CHECK (
        id = public.current_app_user_id()
        OR public.is_platform_super_admin()
    );

-- college_memberships: self reads, validated same-college admin reads, or
-- trusted platform-admin reads. No membership-based helper queries RLS as the
-- invoker, avoiding a recursive users <-> memberships policy dependency.
DROP POLICY IF EXISTS p_memberships_read ON public.college_memberships;
CREATE POLICY p_memberships_read ON public.college_memberships
    FOR SELECT
    USING (
        user_id = public.current_app_user_id()
        OR (
            college_id = public.current_app_tenant()
            AND public.is_current_college_admin()
        )
        OR public.is_platform_super_admin()
    );

DROP POLICY IF EXISTS p_memberships_write ON public.college_memberships;
CREATE POLICY p_memberships_write ON public.college_memberships
    FOR ALL
    USING (public.is_platform_super_admin())
    WITH CHECK (public.is_platform_super_admin());

DROP POLICY IF EXISTS p_memberships_onboarding_insert ON public.college_memberships;
CREATE POLICY p_memberships_onboarding_insert ON public.college_memberships
    FOR INSERT
    WITH CHECK (
        user_id = public.current_app_user_id()
        AND college_id = public.current_app_tenant()
        AND public.can_provision_membership_role(role_in_college::text)
    );

-- chat_sessions: user and tenant ownership are both required. Anonymous
-- sessions remain available only in the selected tenant; super-admin access
-- remains gated by the server-verified context.
DROP POLICY IF EXISTS p_chat_sessions_tenant ON public.chat_sessions;
CREATE POLICY p_chat_sessions_tenant ON public.chat_sessions
    FOR ALL
    USING (
        (
            user_id = public.current_app_user_id()
            AND college_id = public.current_app_tenant()
        )
        OR (
            user_id IS NULL
            AND public.current_app_user_id() IS NULL
            AND college_id = public.current_app_tenant()
        )
        OR public.is_platform_super_admin()
    )
    WITH CHECK (
        (
            user_id = public.current_app_user_id()
            AND college_id = public.current_app_tenant()
        )
        OR (
            user_id IS NULL
            AND public.current_app_user_id() IS NULL
            AND college_id = public.current_app_tenant()
        )
        OR public.is_platform_super_admin()
    );

-- Keep chat_messages aligned with the parent session ownership policy.
DROP POLICY IF EXISTS p_chat_messages_tenant ON public.chat_messages;
CREATE POLICY p_chat_messages_tenant ON public.chat_messages
    FOR ALL
    USING (
        EXISTS (
            SELECT 1
            FROM public.chat_sessions AS cs
            WHERE cs.id = chat_messages.session_id
              AND cs.college_id = public.current_app_tenant()
              AND (
                  cs.user_id = public.current_app_user_id()
                  OR (
                      cs.user_id IS NULL
                      AND public.current_app_user_id() IS NULL
                  )
              )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM public.chat_sessions AS cs
            WHERE cs.id = chat_messages.session_id
              AND cs.college_id = public.current_app_tenant()
              AND (
                  cs.user_id = public.current_app_user_id()
                  OR (
                      cs.user_id IS NULL
                      AND public.current_app_user_id() IS NULL
                  )
              )
        )
    );

COMMIT;

-- ROLLBACK (run only if this patch has been approved and applied):
-- BEGIN;
-- DROP TRIGGER IF EXISTS trg_prevent_user_privilege_self_change ON public.users;
-- DROP FUNCTION IF EXISTS public.prevent_user_privilege_self_change();
-- DROP POLICY IF EXISTS p_users_read ON public.users;
-- CREATE POLICY p_users_read ON public.users FOR SELECT USING (TRUE);
-- DROP POLICY IF EXISTS p_users_insert ON public.users;
-- CREATE POLICY p_users_insert ON public.users FOR INSERT WITH CHECK (TRUE);
-- DROP POLICY IF EXISTS p_users_update ON public.users;
-- CREATE POLICY p_users_update ON public.users FOR UPDATE
--     USING (id = public.current_app_user_id() OR public.is_platform_super_admin())
--     WITH CHECK (id = public.current_app_user_id() OR public.is_platform_super_admin());
-- DROP POLICY IF EXISTS p_memberships_read ON public.college_memberships;
-- CREATE POLICY p_memberships_read ON public.college_memberships FOR SELECT USING (TRUE);
-- DROP POLICY IF EXISTS p_memberships_write ON public.college_memberships;
-- CREATE POLICY p_memberships_write ON public.college_memberships FOR ALL
--     USING (college_id = public.current_app_tenant() OR public.is_platform_super_admin())
--     WITH CHECK (college_id = public.current_app_tenant() OR public.is_platform_super_admin());
-- DROP POLICY IF EXISTS p_memberships_onboarding_insert ON public.college_memberships;
-- DROP POLICY IF EXISTS p_chat_sessions_tenant ON public.chat_sessions;
-- CREATE POLICY p_chat_sessions_tenant ON public.chat_sessions
--     FOR ALL USING (college_id = public.current_app_tenant() OR public.is_platform_super_admin());
-- DROP POLICY IF EXISTS p_chat_messages_tenant ON public.chat_messages;
-- CREATE POLICY p_chat_messages_tenant ON public.chat_messages FOR ALL
--     USING (EXISTS (
--         SELECT 1 FROM public.chat_sessions AS cs
--         WHERE cs.id = chat_messages.session_id
--           AND cs.college_id = public.current_app_tenant()
--     ))
--     WITH CHECK (EXISTS (
--         SELECT 1 FROM public.chat_sessions AS cs
--         WHERE cs.id = chat_messages.session_id
--           AND cs.college_id = public.current_app_tenant()
--     ));
-- REVOKE ALL ON FUNCTION public.is_current_college_admin() FROM college_app_user;
-- REVOKE ALL ON FUNCTION public.can_provision_college_admin() FROM college_app_user;
-- REVOKE ALL ON FUNCTION public.can_provision_membership_role(text) FROM college_app_user;
-- REVOKE ALL ON FUNCTION public.lookup_user_by_email_for_auth(text) FROM college_app_user;
-- REVOKE ALL ON FUNCTION public.lookup_college_invitation_by_token(text) FROM college_app_user;
-- DROP FUNCTION IF EXISTS public.is_current_college_admin();
-- DROP FUNCTION IF EXISTS public.can_provision_college_admin();
-- DROP FUNCTION IF EXISTS public.can_provision_membership_role(text);
-- DROP FUNCTION IF EXISTS public.lookup_user_by_email_for_auth(text);
-- DROP FUNCTION IF EXISTS public.lookup_college_invitation_by_token(text);
-- COMMIT;
