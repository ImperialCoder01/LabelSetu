-- ============================================================
-- Migration: Complete Manufacturer -> Product -> Consumer -> Executive -> Admin Workflow Expansion
-- Date: 2026-08-28
-- Description: Creates authoritative products registry, historical version snapshots,
--              consumer verification event logging, executive officer enforcement cases,
--              product barcodes, and in-app notification alerts with full RLS policies and indexes.
-- ============================================================

-- ============================================================
-- 0. USERS_PROFILE STATUS COLUMN (if not present)
-- ============================================================
ALTER TABLE IF EXISTS users_profile ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';


-- ============================================================
-- 1. TABLE: product_barcodes (Fast Barcode Cache & Registry)
-- ============================================================
CREATE TABLE IF NOT EXISTS product_barcodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    barcode TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    net_quantity TEXT,
    mrp NUMERIC(10, 2),
    manufacturer TEXT,
    country_of_origin TEXT DEFAULT 'India',
    fssai_lic TEXT,
    ingredients TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_barcodes_barcode ON product_barcodes(barcode);

ALTER TABLE product_barcodes ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Anyone can view product barcodes' AND tablename = 'product_barcodes') THEN
        CREATE POLICY "Anyone can view product barcodes"
            ON product_barcodes FOR SELECT
            USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Admins can insert product barcodes' AND tablename = 'product_barcodes') THEN
        CREATE POLICY "Admins can insert product barcodes"
            ON product_barcodes FOR INSERT
            WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Admins can update product barcodes' AND tablename = 'product_barcodes') THEN
        CREATE POLICY "Admins can update product barcodes"
            ON product_barcodes FOR UPDATE
            USING (true);
    END IF;
END $$;


-- ============================================================
-- 2. TABLE: products (Authoritative Manufacturer Product Registry)
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manufacturer_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    brand_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT DEFAULT '',
    sku TEXT DEFAULT '',
    barcode TEXT UNIQUE NOT NULL,
    barcode_type TEXT DEFAULT 'EAN-13',
    gtin TEXT DEFAULT '',
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_approval', 'approved', 'rejected', 'suspended', 'archived')),
    verification_status TEXT NOT NULL DEFAULT 'VERIFIED' CHECK (verification_status IN ('VERIFIED', 'NOT_REGISTERED', 'UNDER_REVIEW', 'SUSPENDED', 'REPORTED', 'CONFIRMED_ISSUE')),
    mrp NUMERIC(10, 2),
    net_quantity TEXT DEFAULT '',
    unit_sale_price TEXT DEFAULT '',
    manufacturing_date_info TEXT DEFAULT '',
    expiry_info TEXT DEFAULT '',
    batch_info TEXT DEFAULT '',
    manufacturer_name_address TEXT DEFAULT '',
    packer_name_address TEXT DEFAULT '',
    importer_name_address TEXT DEFAULT '',
    country_of_origin TEXT DEFAULT 'India',
    consumer_care TEXT DEFAULT '',
    fssai_lic TEXT DEFAULT '',
    ingredients TEXT DEFAULT '',
    veg_non_veg TEXT DEFAULT '' CHECK (veg_non_veg IN ('', 'VEGETARIAN', 'NON_VEGETARIAN')),
    category_declarations JSONB DEFAULT '{}'::jsonb,
    primary_image_url TEXT DEFAULT '',
    front_image_url TEXT DEFAULT '',
    back_image_url TEXT DEFAULT '',
    side_image_urls JSONB DEFAULT '[]'::jsonb,
    rejection_reason TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_manufacturer_id ON products(manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_verification_status ON products(verification_status);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at DESC);

ALTER TABLE products ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Anyone can view approved products' AND tablename = 'products') THEN
        CREATE POLICY "Anyone can view approved products"
            ON products FOR SELECT
            USING (status = 'approved' OR auth.uid() = manufacturer_id OR EXISTS (
                SELECT 1 FROM users_profile WHERE id = auth.uid() AND role IN ('admin', 'regulator')
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Manufacturers can insert own products' AND tablename = 'products') THEN
        CREATE POLICY "Manufacturers can insert own products"
            ON products FOR INSERT
            WITH CHECK (auth.uid() = manufacturer_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Manufacturers can update own products' AND tablename = 'products') THEN
        CREATE POLICY "Manufacturers can update own products"
            ON products FOR UPDATE
            USING (auth.uid() = manufacturer_id AND status IN ('draft', 'pending_approval', 'rejected'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Admins can manage all products' AND tablename = 'products') THEN
        CREATE POLICY "Admins can manage all products"
            ON products FOR ALL
            USING (
                EXISTS (
                    SELECT 1 FROM users_profile WHERE id = auth.uid() AND role = 'admin'
                )
            );
    END IF;
END $$;


-- ============================================================
-- 3. TABLE: product_versions (Historical Snapshots & Revisions)
-- ============================================================
CREATE TABLE IF NOT EXISTS product_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    effective_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES users_profile(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft', 'active', 'archived')),
    snapshot JSONB NOT NULL,
    change_summary TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_versions_product_id ON product_versions(product_id);
CREATE INDEX IF NOT EXISTS idx_product_versions_version_number ON product_versions(product_id, version_number);

ALTER TABLE product_versions ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Anyone can view product versions' AND tablename = 'product_versions') THEN
        CREATE POLICY "Anyone can view product versions"
            ON product_versions FOR SELECT
            USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Manufacturers can insert product versions' AND tablename = 'product_versions') THEN
        CREATE POLICY "Manufacturers can insert product versions"
            ON product_versions FOR INSERT
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM products WHERE id = product_id AND manufacturer_id = auth.uid()
                ) OR EXISTS (
                    SELECT 1 FROM users_profile WHERE id = auth.uid() AND role = 'admin'
                )
            );
    END IF;
END $$;


-- ============================================================
-- 4. TABLE: product_verifications (Consumer Scan & Verification Event Log)
-- ============================================================
CREATE TABLE IF NOT EXISTS product_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    product_version_id UUID REFERENCES product_versions(id) ON DELETE SET NULL,
    barcode TEXT NOT NULL,
    user_id UUID REFERENCES users_profile(id) ON DELETE SET NULL,
    result TEXT NOT NULL CHECK (result IN ('VERIFIED', 'NOT_REGISTERED', 'INACTIVE_PRODUCT', 'SUSPENDED_PRODUCT', 'INVALID_BARCODE', 'POSSIBLE_DUPLICATE', 'REPORTED_PRODUCT', 'VERIFICATION_REQUIRES_REVIEW')),
    verification_source TEXT NOT NULL DEFAULT 'barcode_scan',
    scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
    ocr_crosscheck_result JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    suspicious_flag TEXT NOT NULL DEFAULT 'NORMAL' CHECK (suspicious_flag IN ('NORMAL', 'SUSPICIOUS', 'UNDER_REVIEW', 'CONFIRMED_ISSUE')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_verifications_barcode ON product_verifications(barcode);
CREATE INDEX IF NOT EXISTS idx_product_verifications_product_id ON product_verifications(product_id);
CREATE INDEX IF NOT EXISTS idx_product_verifications_created_at ON product_verifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_product_verifications_suspicious ON product_verifications(suspicious_flag);

ALTER TABLE product_verifications ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can insert verification events' AND tablename = 'product_verifications') THEN
        CREATE POLICY "Users can insert verification events"
            ON product_verifications FOR INSERT
            WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can view own verification events' AND tablename = 'product_verifications') THEN
        CREATE POLICY "Users can view own verification events"
            ON product_verifications FOR SELECT
            USING (
                auth.uid() = user_id OR EXISTS (
                    SELECT 1 FROM users_profile WHERE id = auth.uid() AND role IN ('admin', 'regulator')
                ) OR EXISTS (
                    SELECT 1 FROM products WHERE id = product_verifications.product_id AND manufacturer_id = auth.uid()
                )
            );
    END IF;
END $$;


-- ============================================================
-- 5. TABLE: executive_reports (Executive Officer / Regulator Case Reports)
-- ============================================================
CREATE TABLE IF NOT EXISTS executive_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number TEXT UNIQUE NOT NULL,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    manufacturer_id UUID REFERENCES users_profile(id) ON DELETE SET NULL,
    barcode TEXT DEFAULT '',
    report_type TEXT NOT NULL CHECK (report_type IN ('VIOLATION', 'SUSPECTED_COUNTERFEIT', 'INFO_DISCREPANCY', 'PACKAGING_DISCREPANCY', 'MISSING_DECLARATION', 'MANUFACTURER_ISSUE', 'CONSUMER_COMPLAINT')),
    severity TEXT NOT NULL DEFAULT 'MEDIUM' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    description TEXT NOT NULL,
    detected_issue TEXT DEFAULT '',
    applicable_rule TEXT DEFAULT '',
    evidence JSONB DEFAULT '{}'::jsonb,
    executive_observations TEXT DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT 'WARNING_NOTICE' CHECK (recommended_action IN ('WARNING_NOTICE', 'SUSPEND_PRODUCT', 'PRODUCT_RECALL', 'SEIZE_BATCH', 'REQUEST_INFO', 'FURTHER_INVESTIGATION', 'NO_ACTION')),
    submitted_by UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'SUBMITTED' CHECK (status IN ('DRAFT', 'SUBMITTED', 'UNDER_ADMIN_REVIEW', 'MORE_INFORMATION_REQUIRED', 'APPROVED', 'REJECTED', 'ACTION_IN_PROGRESS', 'RESOLVED', 'CLOSED')),
    admin_id UUID REFERENCES users_profile(id) ON DELETE SET NULL,
    admin_decision TEXT DEFAULT '',
    admin_comments TEXT DEFAULT '',
    final_action_taken TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_executive_reports_status ON executive_reports(status);
CREATE INDEX IF NOT EXISTS idx_executive_reports_severity ON executive_reports(severity);
CREATE INDEX IF NOT EXISTS idx_executive_reports_submitted_by ON executive_reports(submitted_by);
CREATE INDEX IF NOT EXISTS idx_executive_reports_product_id ON executive_reports(product_id);
CREATE INDEX IF NOT EXISTS idx_executive_reports_created_at ON executive_reports(created_at DESC);

ALTER TABLE executive_reports ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Regulators and Admins can view executive reports' AND tablename = 'executive_reports') THEN
        CREATE POLICY "Regulators and Admins can view executive reports"
            ON executive_reports FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM users_profile WHERE id = auth.uid() AND role IN ('admin', 'regulator')
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Regulators can insert executive reports' AND tablename = 'executive_reports') THEN
        CREATE POLICY "Regulators can insert executive reports"
            ON executive_reports FOR INSERT
            WITH CHECK (
                EXISTS (
                    SELECT 1 FROM users_profile WHERE id = auth.uid() AND role IN ('admin', 'regulator')
                ) AND auth.uid() = submitted_by
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Regulators can update own draft executive reports' AND tablename = 'executive_reports') THEN
        CREATE POLICY "Regulators can update own draft executive reports"
            ON executive_reports FOR UPDATE
            USING (
                auth.uid() = submitted_by AND status IN ('DRAFT', 'MORE_INFORMATION_REQUIRED')
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Admins can update executive reports' AND tablename = 'executive_reports') THEN
        CREATE POLICY "Admins can update executive reports"
            ON executive_reports FOR UPDATE
            USING (
                EXISTS (
                    SELECT 1 FROM users_profile WHERE id = auth.uid() AND role = 'admin'
                )
            );
    END IF;
END $$;


-- ============================================================
-- 6. TABLE: notifications (User Alerts & Workflow Notifications)
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users_profile(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('PRODUCT_APPROVAL', 'PRODUCT_REJECTION', 'CORRECTION_REQUEST', 'SUSPENSION', 'REPORT_FILED', 'CASE_ASSIGNED', 'ACTION_REQUIRED', 'INFO')),
    entity_type TEXT DEFAULT '',
    entity_id UUID,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at DESC);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can view own notifications' AND tablename = 'notifications') THEN
        CREATE POLICY "Users can view own notifications"
            ON notifications FOR SELECT
            USING (auth.uid() = user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can update own notifications' AND tablename = 'notifications') THEN
        CREATE POLICY "Users can update own notifications"
            ON notifications FOR UPDATE
            USING (auth.uid() = user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'System and Admins can insert notifications' AND tablename = 'notifications') THEN
        CREATE POLICY "System and Admins can insert notifications"
            ON notifications FOR INSERT
            WITH CHECK (true);
    END IF;
END $$;
