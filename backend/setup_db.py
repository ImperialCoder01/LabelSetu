"""
Supabase Schema Setup Script
Connects to Supabase PostgreSQL and runs schema.sql
"""
import sys
import os
import psycopg2
from pathlib import Path

# Force UTF-8 output on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"

# Database connection details (set SUPABASE_PROJECT_REF in .env or as env var)
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "")
if not PROJECT_REF:
    print("ERROR: Set SUPABASE_PROJECT_REF in your .env file or environment")
    sys.exit(1)
DB_HOST = f"db.{PROJECT_REF}.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"

def get_connection(password):
    """Create PostgreSQL connection to Supabase."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=password,
        sslmode="require"
    )

def run_schema(password):
    """Read and execute schema.sql."""
    schema_path = Path(__file__).parent.parent / "supabase" / "schema.sql"
    
    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}")
        sys.exit(1)
    
    sql = schema_path.read_text(encoding="utf-8")
    print(f"[OK] Loaded schema.sql ({len(sql)} bytes)")
    print(f"[..] Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    
    try:
        conn = get_connection(password)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("[OK] Connected to Supabase PostgreSQL!")
        print("[..] Running schema.sql...")
        
        # Execute the SQL
        cur.execute(sql)
        
        print("[OK] Schema created successfully!")
        
        # Verify tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        
        print("\n[TABLES]")
        for table in tables:
            print(f"  [OK] {table[0]}")
        
        # Verify enums
        cur.execute("""
            SELECT typname 
            FROM pg_type 
            WHERE typname = 'user_role';
        """)
        enums = cur.fetchall()
        if enums:
            print(f"\n[ENUMS]")
            for e in enums:
                print(f"  [OK] {e[0]}")
        
        # Verify RLS
        cur.execute("""
            SELECT tablename, rowsecurity 
            FROM pg_tables 
            WHERE schemaname = 'public' AND rowsecurity = true;
        """)
        rls_tables = cur.fetchall()
        if rls_tables:
            print(f"\n[RLS]")
            for t in rls_tables:
                print(f"  [OK] {t[0]}")
        
        # Verify indexes
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%';
        """)
        indexes = cur.fetchall()
        if indexes:
            print(f"\n[INDEXES]")
            for idx in indexes:
                print(f"  [OK] {idx[0]}")
        
        # Verify policies
        cur.execute("""
            SELECT policyname, tablename 
            FROM pg_policies 
            WHERE schemaname = 'public';
        """)
        policies = cur.fetchall()
        if policies:
            print(f"\n[RLS POLICIES]")
            for p in policies:
                print(f"  [OK] {p[1]} -> {p[0]}")
        
        cur.close()
        conn.close()
        print("\n[DONE] All Supabase tables are ready!")
        
    except psycopg2.OperationalError as e:
        print(f"\n[ERROR] Connection failed: {e}")
        print("\n[HELP] Common fixes:")
        print("  1. Check your database password in Supabase Dashboard -> Settings -> Database")
        print("  2. Make sure you're using the DATABASE password, not the API key")
        print("  3. Try: Supabase Dashboard -> Settings -> Database -> Reset Database Password")
        sys.exit(1)
    except psycopg2.ProgrammingError as e:
        print(f"\n[ERROR] SQL Error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python setup_db.py <database_password>")
        print("\nFind your database password at:")
        print("  Supabase Dashboard -> Settings -> Database -> Database password")
        sys.exit(1)
    
    run_schema(sys.argv[1])
