-- LabelSetu Database Schema for Supabase
-- Run this in the Supabase SQL Editor

-- ============================================================
-- 1. ENUM: User roles
-- ============================================================
CREATE TYPE user_role AS ENUM ('consumer', 'brand', 'regulator', 'admin');

-- ============================================================
-- 2. TABLE: users_profile
-- ============================================================
CREATE TABLE users_profile (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL DEFAULT '',
    role user_role NOT NULL DEFAULT 'consumer',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users_profile (id, full_name, role)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        COALESCE(NEW.raw_user_meta_data->>'role', 'consumer')::user_role
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- 3. TABLE: scans
-- ============================================================
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    image_url TEXT DEFAULT '',
    extracted_text TEXT DEFAULT '',
    compliance_score INTEGER DEFAULT 0 CHECK (compliance_score >= 0 AND compliance_score <= 100),
    missing_fields JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast user lookups
CREATE INDEX idx_scans_user_id ON scans(user_id);
CREATE INDEX idx_scans_created_at ON scans(created_at DESC);
CREATE INDEX idx_scans_compliance_score ON scans(compliance_score);

-- ============================================================
-- 4. TABLE: audit_log
-- ============================================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_id UUID,
    old_value JSONB,
    new_value JSONB,
    timestamp TIMESTAMPTZ DEFAULT now()
);

-- Index for timestamp queries
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_admin_id ON audit_log(admin_id);

-- ============================================================
-- 5. TABLE: api_usage_log
-- ============================================================
CREATE TABLE api_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    month TEXT NOT NULL,  -- Format: "YYYY-MM"
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(provider, month)
);

-- ============================================================
-- 6. ROW LEVEL SECURITY (RLS)
-- ============================================================

-- Enable RLS on all tables
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage_log ENABLE ROW LEVEL SECURITY;

-- --- users_profile policies ---
-- Users can read their own profile
CREATE POLICY "Users can view own profile"
    ON users_profile FOR SELECT
    USING (auth.uid() = id);

-- Users can insert their own profile (used by signup trigger)
CREATE POLICY "Users can insert own profile"
    ON users_profile FOR INSERT
    WITH CHECK (auth.uid() = id OR auth.uid() IS NULL);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON users_profile FOR UPDATE
    USING (auth.uid() = id);

-- Admins can view all profiles
CREATE POLICY "Admins can view all profiles"
    ON users_profile FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Admins can update all profiles
CREATE POLICY "Admins can update all profiles"
    ON users_profile FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Regulators can view all profiles
CREATE POLICY "Regulators can view all profiles"
    ON users_profile FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'regulator'
        )
    );

-- --- scans policies ---
-- Users can view their own scans
CREATE POLICY "Users can view own scans"
    ON scans FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own scans
CREATE POLICY "Users can insert own scans"
    ON scans FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Regulators can view all scans
CREATE POLICY "Regulators can view all scans"
    ON scans FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'regulator'
        )
    );

-- Admins can view all scans
CREATE POLICY "Admins can view all scans"
    ON scans FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Admins can update scans
CREATE POLICY "Admins can update scans"
    ON scans FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Admins can delete scans
CREATE POLICY "Admins can delete scans"
    ON scans FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- --- audit_log policies ---
-- Only admins can access audit logs
CREATE POLICY "Admins can view audit logs"
    ON audit_log FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can insert audit logs"
    ON audit_log FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Admins can delete audit logs
CREATE POLICY "Admins can delete audit logs"
    ON audit_log FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- --- api_usage_log policies ---
-- Only admins can access API usage logs
CREATE POLICY "Admins can view API usage"
    ON api_usage_log FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can update API usage"
    ON api_usage_log FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can insert API usage"
    ON api_usage_log FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- ============================================================
-- 7. TABLE: product_reports
-- ============================================================
CREATE TYPE report_status AS ENUM ('pending', 'forwarded', 'resolved', 'spam');

CREATE TABLE product_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    reporter_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    reason TEXT NOT NULL DEFAULT '',
    status report_status NOT NULL DEFAULT 'pending',
    resolved_by UUID REFERENCES users_profile(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_product_reports_status ON product_reports(status);
CREATE INDEX idx_product_reports_created_at ON product_reports(created_at DESC);
CREATE INDEX idx_product_reports_scan_id ON product_reports(scan_id);

-- Enable RLS
ALTER TABLE product_reports ENABLE ROW LEVEL SECURITY;

-- Consumers can insert their own reports
CREATE POLICY "Users can insert own reports"
    ON product_reports FOR INSERT
    WITH CHECK (auth.uid() = reporter_id);

-- Consumers can view their own reports
CREATE POLICY "Users can view own reports"
    ON product_reports FOR SELECT
    USING (auth.uid() = reporter_id);

-- Admins can view all reports
CREATE POLICY "Admins can view all reports"
    ON product_reports FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Admins can update all reports
CREATE POLICY "Admins can update all reports"
    ON product_reports FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Admins can delete reports
CREATE POLICY "Admins can delete reports"
    ON product_reports FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Regulators can view forwarded reports
CREATE POLICY "Regulators can view forwarded reports"
    ON product_reports FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'regulator'
        )
        AND status = 'forwarded'
    );

-- Regulators can update forwarded reports
CREATE POLICY "Regulators can update forwarded reports"
    ON product_reports FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users_profile
            WHERE id = auth.uid() AND role = 'regulator'
        )
        AND status = 'forwarded'
    );
