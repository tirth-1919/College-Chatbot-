-- Narrow the SECURITY DEFINER authentication lookup without changing its
-- existing owner or application-role EXECUTE grant. Apply only after review.
BEGIN;

DO $migration$
DECLARE
    v_function_owner name;
BEGIN
    SELECT pg_catalog.pg_get_userbyid(proc.proowner)
      INTO STRICT v_function_owner
      FROM pg_catalog.pg_proc AS proc
     WHERE proc.oid = 'public.lookup_user_by_email_for_auth(text)'::pg_catalog.regprocedure;

    EXECUTE 'DROP FUNCTION public.lookup_user_by_email_for_auth(text)';
    EXECUTE $ddl$
        CREATE FUNCTION public.lookup_user_by_email_for_auth(p_email text)
        RETURNS TABLE (
            id uuid,
            email text,
            hashed_password text,
            full_name text,
            role text,
            is_verified boolean,
            is_active boolean
        )
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog
        AS $function$
            SELECT account.id,
                   account.email,
                   account.hashed_password,
                   account.full_name,
                   account.role::text,
                   account.is_verified,
                   account.is_active
              FROM public.users AS account
             WHERE pg_catalog.lower(account.email) = pg_catalog.lower(pg_catalog.btrim(p_email))
             LIMIT 1;
        $function$;
    $ddl$;
    EXECUTE pg_catalog.format(
        'ALTER FUNCTION public.lookup_user_by_email_for_auth(text) OWNER TO %I',
        v_function_owner
    );
END;
$migration$;

REVOKE ALL ON FUNCTION public.lookup_user_by_email_for_auth(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.lookup_user_by_email_for_auth(text) TO college_app_user;

COMMIT;
