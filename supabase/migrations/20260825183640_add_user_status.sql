-- Migration: Add status column to users_profile
-- Run this in the Supabase SQL Editor

-- ============================================================
-- 1. Add status column
-- ============================================================
ALTER TABLE users_profile ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';

-- ============================================================
-- 2. Set existing brand users as pending_approval
-- ============================================================
UPDATE users_profile SET status = 'pending_approval' WHERE role = 'brand' AND status = 'active';

-- ============================================================
-- 3. Update the auto-create trigger to set brand users as pending
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users_profile (id, full_name, role, status)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
        COALESCE(NEW.raw_user_meta_data->>'role', 'consumer')::user_role,
        CASE WHEN COALESCE(NEW.raw_user_meta_data->>'role', 'consumer') = 'brand'
             THEN 'pending_approval'
             ELSE 'active'
        END
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
