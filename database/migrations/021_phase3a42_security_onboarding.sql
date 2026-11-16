-- Phase 3A.4.2: authenticated RLS context, invitation-gated onboarding,
-- privacy-preserving public registration access, and anonymous chat ownership.
-- Apply only after review and isolated-database validation.

BEGIN;

CREATE SCHEMA IF NOT EXISTS auth_private;
REVOKE ALL ON SCHEMA auth_private FROM PUBLIC, college_app_user;

CREATE TABLE auth_private.rls_context_keys (
    key_id text PRIMARY KEY,
    secret bytea NOT NULL CHECK (octet_length(secret) >= 32),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_rls_context_single_active_key
    ON auth_private.rls_context_keys (is_active)
    WHERE is_active;
REVOKE ALL ON TABLE auth_private.rls_context_keys FROM PUBLIC, college_app_user;

CREATE OR REPLACE FUNCTION auth_private.is_request_context_valid()
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, auth_private
AS $function$
DECLARE
    v_user_id text;
    v_college_id text;
    v_super_admin text;
    v_email_verified text;
    v_expires_at text;
    v_secret bytea;
    v_payload text;
    v_expected text;
    v_actual text;
BEGIN
    v_user_id := COALESCE(current_setting('app.current_user_id', true), '');
    v_college_id := COALESCE(current_setting('app.current_college_id', true), '');
    v_super_admin := COALESCE(current_setting('app.is_super_admin', true), '0');
    v_email_verified := COALESCE(current_setting('app.email_verification_authorized', true), '0');
    v_expires_at := COALESCE(current_setting('app.request_context_expires_at', true), '');
    v_actual := COALESCE(current_setting('app.request_context_signature', true), '');

    IF v_expires_at !~ '^[0-9]{1,12}$'
       OR v_super_admin NOT IN ('0', '1')
       OR v_email_verified NOT IN ('0', '1')
       OR v_actual = ''
       THEN
        RETURN false;
    END IF;

    IF v_expires_at::bigint < extract(epoch FROM statement_timestamp())::bigint
       OR v_expires_at::bigint > extract(epoch FROM statement_timestamp())::bigint + 300 THEN
        RETURN false;
    END IF;

    SELECT key.secret
      INTO v_secret
      FROM auth_private.rls_context_keys AS key
     WHERE key.is_active
     ORDER BY key.created_at DESC
     LIMIT 1;
    IF v_secret IS NULL THEN
        RETURN false;
    END IF;

    v_payload := 'v1|' || v_user_id || '|' || v_college_id || '|'
        || v_super_admin || '|' || v_email_verified || '|' || v_expires_at;
    v_expected := rtrim(
        translate(
            replace(encode(public.hmac(convert_to(v_payload, 'UTF8'), v_secret, 'sha256'), 'base64'), E'\n', ''),
            '+/',
            '-_'
        ),
        '='
    );
    RETURN v_actual = v_expected;
EXCEPTION WHEN OTHERS THEN
    RETURN false;
END;
$function$;

CREATE OR REPLACE FUNCTION public.current_app_user_id()
RETURNS uuid
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, auth_private
AS $function$
BEGIN
    IF NOT auth_private.is_request_context_valid() THEN
        RETURN NULL;
    END IF;
    RETURN NULLIF(current_setting('app.current_user_id', true), '')::uuid;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$function$;

CREATE OR REPLACE FUNCTION public.current_app_tenant()
RETURNS uuid
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, auth_private
AS $function$
BEGIN
    IF NOT auth_private.is_request_context_valid() THEN
        RETURN NULL;
    END IF;
    RETURN NULLIF(current_setting('app.current_college_id', true), '')::uuid;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$function$;

CREATE OR REPLACE FUNCTION public.is_platform_super_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, auth_private
AS $function$
    SELECT auth_private.is_request_context_valid()
       AND NULLIF(current_setting('app.current_user_id', true), '') IS NOT NULL
       AND current_setting('app.is_super_admin', true) = '1';
$function$;

CREATE OR REPLACE FUNCTION public.is_current_college_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
    SELECT EXISTS (
        SELECT 1
          FROM public.college_memberships AS membership
          JOIN public.users AS account ON account.id = membership.user_id
         WHERE membership.college_id = public.current_app_tenant()
           AND membership.user_id = public.current_app_user_id()
           AND membership.role_in_college::text = 'ADMIN'
           AND account.role::text = 'COLLEGE_ADMIN'
           AND account.is_active
    );
$function$;

CREATE OR REPLACE FUNCTION public.user_belongs_to_tenant(p_user_id uuid, p_college_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
    SELECT EXISTS (
        SELECT 1
          FROM public.college_memberships AS membership
         WHERE membership.user_id = p_user_id
           AND membership.college_id = p_college_id
    );
$function$;

CREATE OR REPLACE FUNCTION public.lookup_user_by_email_for_auth(p_email text)
RETURNS SETOF public.users
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
    SELECT account.*
      FROM public.users AS account
     WHERE lower(account.email) = lower(btrim(p_email))
     LIMIT 1;
$function$;

ALTER TABLE public.college_admin_invitations
    ADD COLUMN invitation_token_hash text;
UPDATE public.college_admin_invitations
   SET invitation_token_hash = encode(public.digest(invitation_token, 'sha256'), 'hex')
 WHERE invitation_token_hash IS NULL;
ALTER TABLE public.college_admin_invitations
    ALTER COLUMN invitation_token_hash SET NOT NULL,
    DROP COLUMN invitation_token;
ALTER TABLE public.college_registrations
    DROP COLUMN initial_admin_password_hash;
CREATE UNIQUE INDEX uq_college_admin_invitation_token_hash
    ON public.college_admin_invitations (invitation_token_hash);

ALTER TABLE public.chat_sessions
    ADD COLUMN visitor_token_hash text;

CREATE OR REPLACE FUNCTION public.lookup_college_invitation_by_token(p_token text)
RETURNS TABLE (
    id uuid,
    college_id uuid,
    invited_by_user_id uuid,
    email text,
    full_name text,
    role_in_college text,
    status text,
    expires_at timestamptz,
    created_at timestamptz,
    updated_at timestamptz,
    accepted_at timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
    SELECT invitation.id,
           invitation.college_id,
           invitation.invited_by_user_id,
           invitation.email,
           invitation.full_name,
           invitation.role_in_college::text,
           invitation.status::text,
           invitation.expires_at,
           invitation.created_at,
           invitation.updated_at,
           invitation.accepted_at
      FROM public.college_admin_invitations AS invitation
     WHERE invitation.invitation_token_hash =
           encode(public.digest(COALESCE(p_token, ''), 'sha256'), 'hex')
       AND invitation.status = 'PENDING'
       AND invitation.expires_at > statement_timestamp()
     LIMIT 1;
$function$;

CREATE OR REPLACE FUNCTION public.accept_college_admin_invitation(
    p_token text,
    p_full_name text,
    p_password_hash text,
    p_authenticated_user_id uuid
)
RETURNS TABLE (accepted_user_id uuid, accepted_college_id uuid, accepted_email text, is_existing_user boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
DECLARE
    v_invitation public.college_admin_invitations%ROWTYPE;
    v_account public.users%ROWTYPE;
    v_user_id uuid;
    v_existing boolean := false;
BEGIN
    IF p_authenticated_user_id IS NOT NULL
       AND p_authenticated_user_id IS DISTINCT FROM public.current_app_user_id() THEN
        RAISE EXCEPTION 'Authenticated invitation identity does not match the verified request context'
            USING ERRCODE = '42501';
    END IF;

    SELECT invitation.*
      INTO v_invitation
      FROM public.college_admin_invitations AS invitation
     WHERE invitation.invitation_token_hash =
           encode(public.digest(COALESCE(p_token, ''), 'sha256'), 'hex')
     FOR UPDATE;

    IF NOT FOUND OR v_invitation.status <> 'PENDING'
       OR v_invitation.expires_at <= statement_timestamp() THEN
        RAISE EXCEPTION 'Invitation is invalid, expired, or already used'
            USING ERRCODE = '22023';
    END IF;

    PERFORM 1
      FROM public.colleges AS college
     WHERE college.id = v_invitation.college_id
       AND college.status = 'APPROVED'
       AND college.is_active
     FOR SHARE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'The college is not approved for administrator activation'
            USING ERRCODE = '42501';
    END IF;

    SELECT account.*
      INTO v_account
      FROM public.users AS account
     WHERE lower(account.email) = lower(v_invitation.email)
     FOR UPDATE;

    IF FOUND THEN
        v_user_id := v_account.id;
        v_existing := true;
        IF v_account.role = 'SUPER_ADMIN' THEN
            RAISE EXCEPTION 'Platform administrator accounts cannot accept college invitations'
                USING ERRCODE = '42501';
        END IF;
        IF v_account.is_active AND p_authenticated_user_id IS DISTINCT FROM v_account.id THEN
            RAISE EXCEPTION 'Sign in to the invited account before accepting this invitation'
                USING ERRCODE = '42501';
        END IF;
        IF NOT v_account.is_active THEN
            RAISE EXCEPTION 'A disabled account cannot be reactivated through an invitation'
                USING ERRCODE = '42501';
        END IF;
        IF p_authenticated_user_id IS DISTINCT FROM v_account.id THEN
            RAISE EXCEPTION 'Sign in to the invited account before accepting this invitation'
                USING ERRCODE = '42501';
        END IF;

        UPDATE public.users
           SET role = 'COLLEGE_ADMIN',
               full_name = v_account.full_name,
               updated_at = statement_timestamp()
         WHERE id = v_user_id;
    ELSE
        IF p_authenticated_user_id IS NOT NULL
           OR p_password_hash IS NULL
           OR length(p_password_hash) < 20 THEN
            RAISE EXCEPTION 'A new invited account requires a password'
                USING ERRCODE = '22023';
        END IF;
        v_user_id := gen_random_uuid();
        INSERT INTO public.users (
            id, email, hashed_password, full_name, role, is_verified, is_active, created_at, updated_at
        ) VALUES (
            v_user_id,
            lower(v_invitation.email),
            p_password_hash,
            COALESCE(NULLIF(btrim(p_full_name), ''), v_invitation.full_name),
            'COLLEGE_ADMIN',
            TRUE,
            TRUE,
            statement_timestamp(),
            statement_timestamp()
        );
    END IF;

    INSERT INTO public.college_memberships (
        id, college_id, user_id, role_in_college, is_primary, created_at
    ) VALUES (
        gen_random_uuid(),
        v_invitation.college_id,
        v_user_id,
        v_invitation.role_in_college,
        TRUE,
        statement_timestamp()
    )
    ON CONFLICT (college_id, user_id) DO UPDATE
       SET role_in_college = EXCLUDED.role_in_college,
           is_primary = TRUE;

    UPDATE public.college_admin_invitations
       SET status = 'ACCEPTED',
           accepted_at = statement_timestamp(),
           updated_at = statement_timestamp()
     WHERE id = v_invitation.id;

    UPDATE public.college_onboarding_progress
       SET admin_assigned = TRUE,
           updated_at = statement_timestamp()
     WHERE college_id = v_invitation.college_id;

    RETURN QUERY SELECT v_user_id, v_invitation.college_id, lower(v_invitation.email), v_existing;
END;
$function$;

CREATE OR REPLACE FUNCTION public.prevent_user_privilege_self_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public, auth_private
AS $function$
BEGIN
    IF (
        NEW.role IS DISTINCT FROM OLD.role
        OR NEW.is_active IS DISTINCT FROM OLD.is_active
    )
    AND current_user <> 'postgres'
    AND NOT public.is_platform_super_admin() THEN
        RAISE EXCEPTION 'User privilege and activation fields require trusted administrative authorization'
            USING ERRCODE = '42501';
    END IF;
    IF NEW.is_verified IS DISTINCT FROM OLD.is_verified
       AND current_user <> 'postgres'
       AND NOT public.is_platform_super_admin()
       AND NOT (
           OLD.id = public.current_app_user_id()
           AND current_setting('app.email_verification_authorized', true) = '1'
       ) THEN
        RAISE EXCEPTION 'Email verification requires its signed verification context'
            USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS trg_prevent_user_privilege_self_change ON public.users;
CREATE TRIGGER trg_prevent_user_privilege_self_change
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.prevent_user_privilege_self_change();

DROP POLICY IF EXISTS p_users_read ON public.users;
DROP POLICY IF EXISTS p_users_college_admin_read ON public.users;
DROP POLICY IF EXISTS p_users_insert ON public.users;
DROP POLICY IF EXISTS p_users_update ON public.users;
DROP POLICY IF EXISTS p_users_delete ON public.users;

CREATE POLICY p_users_read ON public.users
    FOR SELECT
    USING (id = public.current_app_user_id() OR public.is_platform_super_admin());
CREATE POLICY p_users_college_admin_read ON public.users
    FOR SELECT
    USING (
        public.is_current_college_admin()
        AND public.user_belongs_to_tenant(id, public.current_app_tenant())
    );
CREATE POLICY p_users_insert ON public.users
    FOR INSERT
    WITH CHECK (
        role::text = 'STUDENT'
        AND id = public.current_app_user_id()
        AND is_verified = FALSE
        AND is_active = TRUE
    );
CREATE POLICY p_users_update ON public.users
    FOR UPDATE
    USING (id = public.current_app_user_id() OR public.is_platform_super_admin())
    WITH CHECK (id = public.current_app_user_id() OR public.is_platform_super_admin());
CREATE POLICY p_users_delete ON public.users
    FOR DELETE
    USING (public.is_platform_super_admin());

DROP POLICY IF EXISTS p_memberships_read ON public.college_memberships;
DROP POLICY IF EXISTS p_memberships_write ON public.college_memberships;
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
CREATE POLICY p_memberships_write ON public.college_memberships
    FOR ALL
    USING (public.is_platform_super_admin())
    WITH CHECK (public.is_platform_super_admin());

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
            AND visitor_token_hash IS NOT NULL
            AND visitor_token_hash = encode(
                public.digest(COALESCE(current_setting('app.chat_visitor_token', true), ''), 'sha256'),
                'hex'
            )
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
            AND visitor_token_hash IS NOT NULL
            AND visitor_token_hash = encode(
                public.digest(COALESCE(current_setting('app.chat_visitor_token', true), ''), 'sha256'),
                'hex'
            )
        )
        OR public.is_platform_super_admin()
    );

DROP POLICY IF EXISTS p_chat_messages_tenant ON public.chat_messages;
CREATE POLICY p_chat_messages_tenant ON public.chat_messages
    FOR ALL
    USING (
        EXISTS (
            SELECT 1
              FROM public.chat_sessions AS chat_session
             WHERE chat_session.id = chat_messages.session_id
               AND chat_session.college_id = public.current_app_tenant()
               AND (
                   chat_session.user_id = public.current_app_user_id()
                   OR (
                       chat_session.user_id IS NULL
                       AND public.current_app_user_id() IS NULL
                       AND chat_session.visitor_token_hash = encode(
                           public.digest(COALESCE(current_setting('app.chat_visitor_token', true), ''), 'sha256'),
                           'hex'
                       )
                   )
               )
        )
        OR public.is_platform_super_admin()
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
              FROM public.chat_sessions AS chat_session
             WHERE chat_session.id = chat_messages.session_id
               AND chat_session.college_id = public.current_app_tenant()
               AND (
                   chat_session.user_id = public.current_app_user_id()
                   OR (
                       chat_session.user_id IS NULL
                       AND public.current_app_user_id() IS NULL
                       AND chat_session.visitor_token_hash = encode(
                           public.digest(COALESCE(current_setting('app.chat_visitor_token', true), ''), 'sha256'),
                           'hex'
                       )
                   )
               )
        )
        OR public.is_platform_super_admin()
    );

CREATE OR REPLACE FUNCTION public.submit_public_college_registration(p_payload jsonb)
RETURNS TABLE (registration_id uuid, college_id uuid, tracking_code text, created_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
DECLARE
    v_college_id uuid := gen_random_uuid();
    v_registration_id uuid := gen_random_uuid();
    v_slug text := lower(btrim(p_payload->>'slug'));
    v_domain text := lower(regexp_replace(btrim(p_payload->>'official_domain'), '^www\.', ''));
    v_tracking_code text := 'APP-' || upper(encode(gen_random_bytes(24), 'hex'));
    v_now timestamptz := statement_timestamp();
BEGIN
    IF p_payload IS NULL
       OR length(COALESCE(p_payload->>'college_name', '')) < 3
       OR length(COALESCE(v_slug, '')) < 2
       OR v_slug !~ '^[a-z0-9-]+$'
       OR length(COALESCE(v_domain, '')) < 3
       OR p_payload->>'initial_admin_email' IS NULL
       OR p_payload->>'initial_admin_name' IS NULL THEN
        RAISE EXCEPTION 'Registration payload is incomplete or invalid'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_advisory_xact_lock(hashtextextended('slug:' || v_slug, 0));
    PERFORM pg_advisory_xact_lock(hashtextextended('domain:' || v_domain, 0));

    IF EXISTS (SELECT 1 FROM public.colleges c WHERE c.slug = v_slug OR lower(c.official_domain) = v_domain)
       OR EXISTS (
           SELECT 1 FROM public.college_registrations r
            WHERE r.slug = v_slug OR lower(r.official_domain) = v_domain
       ) THEN
        RAISE EXCEPTION 'Registration could not be accepted'
            USING ERRCODE = '23505';
    END IF;

    INSERT INTO public.colleges (
        id, name, slug, official_domain, logo_url, contact_email, contact_phone,
        status, is_active, created_at, updated_at
    ) VALUES (
        v_college_id,
        btrim(p_payload->>'college_name'),
        v_slug,
        v_domain,
        NULLIF(btrim(p_payload->>'logo_url'), ''),
        lower(btrim(p_payload->>'official_email')),
        NULLIF(btrim(p_payload->>'contact_phone'), ''),
        'PENDING',
        FALSE,
        v_now,
        v_now
    );

    INSERT INTO public.college_registrations (
        id, college_id, college_name, college_code, slug, official_domain,
        contact_email, contact_phone, contact_person_name, contact_person_email,
        address, city, state, country, description, accreditation_details,
        website_url, logo_url, supporting_documents, status, tracking_code,
        initial_admin_name, initial_admin_email, initial_admin_designation,
        created_at, updated_at
    ) VALUES (
        v_registration_id,
        v_college_id,
        btrim(p_payload->>'college_name'),
        NULLIF(btrim(p_payload->>'college_code'), ''),
        v_slug,
        v_domain,
        lower(btrim(p_payload->>'official_email')),
        NULLIF(btrim(p_payload->>'contact_phone'), ''),
        btrim(p_payload->>'contact_person_name'),
        lower(btrim(p_payload->>'contact_person_email')),
        NULLIF(btrim(p_payload->>'address'), ''),
        NULLIF(btrim(p_payload->>'city'), ''),
        NULLIF(btrim(p_payload->>'state'), ''),
        COALESCE(NULLIF(btrim(p_payload->>'country'), ''), 'India'),
        NULLIF(btrim(p_payload->>'description'), ''),
        NULLIF(btrim(p_payload->>'accreditation_details'), ''),
        NULLIF(btrim(p_payload->>'website_url'), ''),
        NULLIF(btrim(p_payload->>'logo_url'), ''),
        COALESCE(p_payload->'supporting_documents', '[]'::jsonb),
        'PENDING',
        v_tracking_code,
        btrim(p_payload->>'initial_admin_name'),
        lower(btrim(p_payload->>'initial_admin_email')),
        COALESCE(NULLIF(btrim(p_payload->>'initial_admin_designation'), ''), 'College Administrator'),
        v_now,
        v_now
    );

    INSERT INTO public.registration_reviews (
        id, registration_id, reviewer_user_id, previous_status, new_status,
        comments, action_type, created_at
    ) VALUES (
        gen_random_uuid(), v_registration_id, NULL, 'PENDING', 'PENDING',
        'Application submitted via public onboarding portal.', 'SUBMITTED', v_now
    );

    RETURN QUERY SELECT v_registration_id, v_college_id, v_tracking_code, v_now;
END;
$function$;

CREATE OR REPLACE FUNCTION public.check_public_registration_availability(p_slug text, p_domain text DEFAULT NULL)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
    SELECT NOT EXISTS (
        SELECT 1
          FROM public.colleges college
         WHERE college.slug = lower(btrim(p_slug))
            OR (p_domain IS NOT NULL AND lower(college.official_domain) = lower(btrim(p_domain)))
    ) AND NOT EXISTS (
        SELECT 1
          FROM public.college_registrations registration
         WHERE registration.slug = lower(btrim(p_slug))
            OR (p_domain IS NOT NULL AND lower(registration.official_domain) = lower(btrim(p_domain)))
    );
$function$;

CREATE OR REPLACE FUNCTION public.get_public_registration_status(p_tracking_code text)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
    SELECT jsonb_build_object(
        'id', registration.id,
        'college_id', registration.college_id,
        'college_name', registration.college_name,
        'slug', registration.slug,
        'official_domain', registration.official_domain,
        'status', registration.status::text,
        'tracking_code', btrim(p_tracking_code),
        'created_at', registration.created_at,
        'updated_at', registration.updated_at,
        'additional_info_requested', registration.additional_info_requested
    )
      FROM public.college_registrations registration
     WHERE upper(registration.tracking_code) = upper(btrim(p_tracking_code))
     LIMIT 1;
$function$;

CREATE OR REPLACE FUNCTION public.submit_public_registration_information(
    p_tracking_code text,
    p_response text,
    p_additional_documents jsonb DEFAULT '[]'::jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, auth_private
AS $function$
DECLARE
    v_registration public.college_registrations%ROWTYPE;
    v_now timestamptz := statement_timestamp();
BEGIN
    SELECT registration.*
      INTO v_registration
      FROM public.college_registrations registration
     WHERE upper(registration.tracking_code) = upper(btrim(p_tracking_code))
     FOR UPDATE;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    IF v_registration.status <> 'ADDITIONAL_INFORMATION_REQUIRED' THEN
        RAISE EXCEPTION 'Additional information is not currently requested'
            USING ERRCODE = '22023';
    END IF;

    UPDATE public.college_registrations
       SET status = 'UNDER_REVIEW',
           additional_info_submitted = p_response,
           supporting_documents = COALESCE(supporting_documents, '[]'::jsonb)
               || COALESCE(p_additional_documents, '[]'::jsonb),
           updated_at = v_now
     WHERE id = v_registration.id;

    INSERT INTO public.registration_reviews (
        id, registration_id, reviewer_user_id, previous_status, new_status,
        comments, action_type, created_at
    ) VALUES (
        gen_random_uuid(), v_registration.id, NULL, v_registration.status, 'UNDER_REVIEW',
        'Applicant submitted additional information.', 'INFO_SUBMITTED', v_now
    );
    RETURN public.get_public_registration_status(p_tracking_code);
END;
$function$;

REVOKE ALL ON FUNCTION auth_private.is_request_context_valid() FROM PUBLIC, college_app_user;
REVOKE ALL ON FUNCTION public.current_app_user_id() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.current_app_tenant() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.is_platform_super_admin() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.is_current_college_admin() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.user_belongs_to_tenant(uuid, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.lookup_user_by_email_for_auth(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.lookup_college_invitation_by_token(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.accept_college_admin_invitation(text, text, text, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.submit_public_college_registration(jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.check_public_registration_availability(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.get_public_registration_status(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.submit_public_registration_information(text, text, jsonb) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.current_app_user_id() TO college_app_user;
GRANT EXECUTE ON FUNCTION public.current_app_tenant() TO college_app_user;
GRANT EXECUTE ON FUNCTION public.is_platform_super_admin() TO college_app_user;
GRANT EXECUTE ON FUNCTION public.is_current_college_admin() TO college_app_user;
GRANT EXECUTE ON FUNCTION public.user_belongs_to_tenant(uuid, uuid) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.lookup_college_invitation_by_token(text) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.accept_college_admin_invitation(text, text, text, uuid) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.submit_public_college_registration(jsonb) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.check_public_registration_availability(text, text) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.get_public_registration_status(text) TO college_app_user;
GRANT EXECUTE ON FUNCTION public.submit_public_registration_information(text, text, jsonb) TO college_app_user;

COMMIT;

-- A trusted database owner must provision the same random 32-byte key used by
-- RLS_CONTEXT_SECRET. Do not commit the key or run this placeholder unchanged:
-- INSERT INTO auth_private.rls_context_keys (key_id, secret)
-- VALUES ('active', decode('<64 hex characters>', 'hex'));
