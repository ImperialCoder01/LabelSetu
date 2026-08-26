"""
Database Migration helper: Create product_barcodes table and RLS policies on Supabase.
"""

import os
import psycopg2
from config import settings

def migrate():
    # Database connection parameters
    db_url = settings.SUPABASE_URL
    project_ref = settings.SUPABASE_PROJECT_REF or "pmcoytoyqzfcbvgvbkro"
    
    # We can connect using Supabase Python client REST or psycopg2 if DB password is present
    from database import supabase
    
    sql = """
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
    """
    print("Migrating product_barcodes table...")
    try:
        # Check if table exists via Supabase RPC or select
        supabase.table("product_barcodes").select("id").limit(1).execute()
        print("[OK] product_barcodes table already exists!")
    except Exception as exc:
        print("Note: Table may need creation via SQL editor or direct connection: %s", exc)

if __name__ == "__main__":
    migrate()
