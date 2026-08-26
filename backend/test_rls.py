"""
RLS Verification Script
=======================
Tests Row Level Security policies by creating two test accounts
(consumer + admin) and verifying access boundaries.

Usage:
    python test_rls.py

Requires:
    - A running Supabase instance
    - .env with SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
"""

import os
import sys
import uuid
import time
from dotenv import load_dotenv

load_dotenv()

# We need two Supabase clients:
# 1. admin_client: uses service_role (bypasses RLS) for setup/teardown
# 2. consumer_client / admin_user_client: uses anon key (respects RLS)
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

if not all([SUPABASE_URL, SERVICE_KEY, ANON_KEY]):
    print("ERROR: Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_ANON_KEY in .env")
    sys.exit(1)

# Admin client (bypasses RLS)
admin_db = create_client(SUPABASE_URL, SERVICE_KEY)

# Track created user IDs for cleanup
created_user_ids = []
passed = 0
failed = 0


def check(description, condition):
    global passed, failed
    if condition:
        print(f"  ✓ {description}")
        passed += 1
    else:
        print(f"  ✗ FAIL: {description}")
        failed += 1


def create_test_user(email, password, full_name, role):
    """Create a test user and return (user_id, anon_supabase_client)."""
    # Create auth user via service role
    result = admin_db.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {"full_name": full_name, "role": role},
    })
    user_id = result.user.id
    created_user_ids.append(user_id)

    # Wait briefly for the trigger to create the profile
    time.sleep(0.5)

    # Verify profile was created
    profile = admin_db.table("users_profile").select("*").eq("id", user_id).single().execute()
    if not profile.data:
        print(f"  WARNING: Profile not created for {email}, inserting manually")
        admin_db.table("users_profile").insert({
            "id": user_id,
            "full_name": full_name,
            "role": role,
        }).execute()

    # Sign in as this user to get an anon-key-scoped client
    client = create_client(SUPABASE_URL, ANON_KEY)
    client.auth.sign_in_with_password({"email": email, "password": password})

    return user_id, client


def cleanup():
    """Remove all test data."""
    print("\nCleaning up test data...")
    for uid in created_user_ids:
        try:
            admin_db.auth.admin.delete_user(uid)
        except Exception:
            pass
    print("  Done.")


def main():
    global passed, failed

    consumer_email = f"test_consumer_{uuid.uuid4().hex[:8]}@test.com"
    admin_email = f"test_admin_{uuid.uuid4().hex[:8]}@test.com"
    TEST_PASSWORD = "TestPass123!"

    print("=" * 60)
    print("RLS VERIFICATION TEST")
    print("=" * 60)

    # ---- Create test users ----
    print("\n1. Creating test accounts...")
    consumer_id, consumer_db = create_test_user(
        consumer_email, TEST_PASSWORD, "Test Consumer", "consumer"
    )
    print(f"   Consumer: {consumer_id[:8]}... ({consumer_email})")

    admin_id, admin_db_client = create_test_user(
        admin_email, TEST_PASSWORD, "Test Admin", "admin"
    )
    print(f"   Admin:    {admin_id[:8]}... ({admin_email})")

    # ---- Create test scans ----
    print("\n2. Creating test scan data...")
    consumer_scan = admin_db.table("scans").insert({
        "user_id": consumer_id,
        "extracted_text": "Consumer Product Scan",
        "compliance_score": 85,
        "missing_fields": "[]",
    }).execute()
    consumer_scan_id = consumer_scan.data[0]["id"]
    print(f"   Consumer scan: {consumer_scan_id[:8]}...")

    admin_scan = admin_db.table("scans").insert({
        "user_id": admin_id,
        "extracted_text": "Admin Product Scan",
        "compliance_score": 60,
        "missing_fields": '["mrp"]',
    }).execute()
    admin_scan_id = admin_scan.data[0]["id"]
    print(f"   Admin scan:    {admin_scan_id[:8]}...")

    other_user_id = str(uuid.uuid4())
    other_scan = admin_db.table("scans").insert({
        "user_id": other_user_id,
        "extracted_text": "Other User Scan",
        "compliance_score": 40,
        "missing_fields": '["mrp", "net_quantity"]',
    }).execute()
    other_scan_id = other_scan.data[0]["id"]
    print(f"   Other scan:    {other_scan_id[:8]}...")

    # ---- Test 1: Consumer can only see their own scans ----
    print("\n3. Testing CONSUMER access to scans...")
    consumer_scans = consumer_db.table("scans").select("*").execute()
    consumer_ids = {s["id"] for s in consumer_scans.data}

    check("Consumer sees their own scan", consumer_scan_id in consumer_ids)
    check("Consumer does NOT see admin's scan", admin_scan_id not in consumer_ids)
    check("Consumer does NOT see other user's scan", other_scan_id not in consumer_ids)
    check("Consumer sees exactly 1 scan", len(consumer_scans.data) == 1)

    # ---- Test 2: Admin can see all scans ----
    print("\n4. Testing ADMIN access to scans...")
    admin_scans_result = admin_db_client.table("scans").select("*").execute()
    admin_ids = {s["id"] for s in admin_scans_result.data}

    check("Admin sees consumer's scan", consumer_scan_id in admin_ids)
    check("Admin sees admin's own scan", admin_scan_id in admin_ids)
    check("Admin sees other user's scan", other_scan_id in admin_ids)
    check("Admin sees all 3 scans", len(admin_scans_result.data) >= 3)

    # ---- Test 3: Consumer cannot update other users' scans ----
    print("\n5. Testing CONSUMER cannot UPDATE other scans...")
    update_result = consumer_db.table("scans").update({
        "compliance_score": 999
    }).eq("id", admin_scan_id).execute()

    # With RLS, update should affect 0 rows
    check("Consumer UPDATE on other scan affects 0 rows", len(update_result.data) == 0)

    # Verify the score wasn't changed
    verify = admin_db.table("scans").select("compliance_score").eq("id", admin_scan_id).single().execute()
    check("Admin scan score unchanged", verify.data["compliance_score"] == 60)

    # ---- Test 4: Admin can update any scan ----
    print("\n6. Testing ADMIN can UPDATE any scan...")
    admin_update = admin_db_client.table("scans").update({
        "compliance_score": 75
    }).eq("id", consumer_scan_id).execute()

    check("Admin UPDATE on consumer scan succeeds", len(admin_update.data) == 1)

    # Restore original score
    admin_db.table("scans").update({"compliance_score": 85}).eq("id", consumer_scan_id).execute()

    # ---- Test 5: users_profile access ----
    print("\n7. Testing users_profile access...")
    consumer_profiles = consumer_db.table("users_profile").select("*").execute()
    check("Consumer can see their own profile",
          any(p["id"] == consumer_id for p in consumer_profiles.data))

    admin_profiles = admin_db_client.table("users_profile").select("*").execute()
    check("Admin can see all profiles", len(admin_profiles.data) >= 2)

    # ---- Test 6: audit_log access ----
    print("\n8. Testing audit_log access...")
    # Insert an audit log entry via service role
    admin_db.table("audit_log").insert({
        "admin_id": admin_id,
        "action_type": "TEST",
        "target_table": "scans",
        "target_id": consumer_scan_id,
    }).execute()

    consumer_logs = consumer_db.table("audit_log").select("*").execute()
    check("Consumer CANNOT see audit logs", len(consumer_logs.data) == 0)

    admin_logs = admin_db_client.table("audit_log").select("*").execute()
    check("Admin CAN see audit logs", len(admin_logs.data) >= 1)

    # ---- Test 7: product_reports access ----
    print("\n9. Testing product_reports access...")
    admin_db.table("product_reports").insert({
        "scan_id": consumer_scan_id,
        "reporter_id": consumer_id,
        "reason": "Test report",
        "status": "pending",
    }).execute()

    consumer_reports = consumer_db.table("product_reports").select("*").execute()
    check("Consumer can see their own reports",
          len(consumer_reports.data) >= 1)

    # ---- Summary ----
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 60)

    cleanup()

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
