-- Tenant scoped academic catalogue, fee schedules, gallery assets, and audit history.
-- This migration is additive and intentionally contains no production seed data.

CREATE TABLE IF NOT EXISTS academic_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    course_name VARCHAR(255) NOT NULL,
    course_code VARCHAR(80),
    course_abbreviation VARCHAR(80),
    course_category VARCHAR(100) NOT NULL DEFAULT 'OTHER',
    branch_name VARCHAR(255),
    program_level VARCHAR(80),
    duration VARCHAR(100),
    total_semesters SMALLINT CHECK (total_semesters IS NULL OR total_semesters BETWEEN 1 AND 16),
    eligibility TEXT,
    admission_information TEXT,
    syllabus_information TEXT,
    active_status BOOLEAN NOT NULL DEFAULT FALSE,
    verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    source_document UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_academic_course_college_name UNIQUE (college_id, course_name)
);
CREATE INDEX IF NOT EXISTS ix_academic_courses_college_active ON academic_courses(college_id, active_status);
CREATE UNIQUE INDEX IF NOT EXISTS uq_academic_courses_id_college ON academic_courses(id, college_id);

CREATE TABLE IF NOT EXISTS academic_fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES academic_courses(id) ON DELETE CASCADE,
    semester_number SMALLINT CHECK (semester_number IS NULL OR semester_number BETWEEN 1 AND 16),
    fee_amount NUMERIC(12,2) NOT NULL CHECK (fee_amount >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    fee_type VARCHAR(80) NOT NULL DEFAULT 'SEMESTER',
    academic_year VARCHAR(20),
    effective_from DATE,
    effective_until DATE,
    verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    source_document UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_academic_fee_semester_type CHECK ((fee_type = 'SEMESTER' AND semester_number IS NOT NULL) OR fee_type <> 'SEMESTER'),
    CONSTRAINT fk_academic_fee_course_tenant FOREIGN KEY (course_id, college_id)
        REFERENCES academic_courses(id, college_id) DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS ix_academic_fees_lookup ON academic_fees(college_id, course_id, academic_year, semester_number);

CREATE TABLE IF NOT EXISTS college_gallery_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    image_title VARCHAR(255) NOT NULL,
    image_description TEXT,
    image_category VARCHAR(100) NOT NULL DEFAULT 'OTHER',
    facility_name VARCHAR(255),
    event_name VARCHAR(255),
    event_date DATE,
    source_url TEXT,
    source_document UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    verification_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    content_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_gallery_college_hash UNIQUE (college_id, content_hash)
);
CREATE INDEX IF NOT EXISTS ix_gallery_college_category ON college_gallery_images(college_id, image_category, is_active);

CREATE TABLE IF NOT EXISTS academic_change_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    entity_type VARCHAR(40) NOT NULL,
    entity_id UUID NOT NULL,
    changed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    change_action VARCHAR(40) NOT NULL,
    change_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$ DECLARE t TEXT; BEGIN
  FOREACH t IN ARRAY ARRAY['academic_courses','academic_fees','college_gallery_images','academic_change_history'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_tenant_select', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_tenant_write', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_tenant_insert', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_tenant_update', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_tenant_delete', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR SELECT USING (college_id = current_app_tenant() OR is_platform_super_admin())', t || '_tenant_select', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR INSERT WITH CHECK (is_platform_super_admin() OR (college_id = current_app_tenant() AND EXISTS (SELECT 1 FROM users u WHERE u.id = current_app_user_id() AND u.role = ''COLLEGE_ADMIN'')))', t || '_tenant_insert', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR UPDATE USING (is_platform_super_admin() OR (college_id = current_app_tenant() AND EXISTS (SELECT 1 FROM users u WHERE u.id = current_app_user_id() AND u.role = ''COLLEGE_ADMIN''))) WITH CHECK (is_platform_super_admin() OR (college_id = current_app_tenant() AND EXISTS (SELECT 1 FROM users u WHERE u.id = current_app_user_id() AND u.role = ''COLLEGE_ADMIN'')))', t || '_tenant_update', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR DELETE USING (is_platform_super_admin() OR (college_id = current_app_tenant() AND EXISTS (SELECT 1 FROM users u WHERE u.id = current_app_user_id() AND u.role = ''COLLEGE_ADMIN'')))', t || '_tenant_delete', t);
  END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON academic_courses, academic_fees, college_gallery_images, academic_change_history TO college_app_user;
