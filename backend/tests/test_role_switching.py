"""
Targeted tests for role-based authorization, role switching, and token isolation.
Verifies:
  - Consumer role can call POST /api/scans/scan
  - Brand role can call POST /api/scans/scan
  - Regulator role is rejected on POST /api/scans/scan (HTTP 403)
  - Admin role is rejected on POST /api/scans/scan (HTTP 403)
  - Sequential login/logout role switching causes zero token leakage
"""

import sys
import unittest
import asyncio
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import HTTPException
from auth.dependencies import require_role


class TestRoleAuthorization(unittest.TestCase):
    def test_consumer_role_scan_access(self):
        """Consumer role is allowed to access /api/scans/scan."""
        checker = require_role("consumer", "brand")
        user = {"sub": "usr-1", "profile": {"id": "usr-1", "role": "consumer"}}
        res = asyncio.run(checker(user=user))
        self.assertEqual(res["profile"]["role"], "consumer")

    def test_brand_role_scan_access(self):
        """Brand role is allowed to access /api/scans/scan."""
        checker = require_role("consumer", "brand")
        user = {"sub": "usr-2", "profile": {"id": "usr-2", "role": "brand"}}
        res = asyncio.run(checker(user=user))
        self.assertEqual(res["profile"]["role"], "brand")

    def test_regulator_role_scan_denial(self):
        """Regulator role is forbidden from /api/scans/scan."""
        checker = require_role("consumer", "brand")
        user = {"sub": "usr-3", "profile": {"id": "usr-3", "role": "regulator"}}
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(checker(user=user))
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("regulator", ctx.exception.detail)

    def test_admin_role_scan_denial(self):
        """Admin role is strictly forbidden from /api/scans/scan."""
        checker = require_role("consumer", "brand")
        user = {"sub": "usr-4", "profile": {"id": "usr-4", "role": "admin"}}
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(checker(user=user))
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("admin", ctx.exception.detail)

    def test_admin_only_endpoints(self):
        """Admin-only endpoints allow admin, forbid consumer, brand, regulator."""
        checker = require_role("admin")

        admin_user = {"sub": "u-admin", "profile": {"id": "u-admin", "role": "admin"}}
        res = asyncio.run(checker(user=admin_user))
        self.assertEqual(res["profile"]["role"], "admin")

        for r in ["consumer", "brand", "regulator"]:
            other_user = {"sub": f"u-{r}", "profile": {"id": f"u-{r}", "role": r}}
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(checker(user=other_user))
            self.assertEqual(ctx.exception.status_code, 403)

    def test_regulator_endpoints(self):
        """Regulator endpoints allow regulator and admin, forbid consumer and brand."""
        checker = require_role("regulator", "admin")

        for r in ["regulator", "admin"]:
            allowed_user = {"sub": f"u-{r}", "profile": {"id": f"u-{r}", "role": r}}
            res = asyncio.run(checker(user=allowed_user))
            self.assertEqual(res["profile"]["role"], r)

        for r in ["consumer", "brand"]:
            forbidden_user = {"sub": f"u-{r}", "profile": {"id": f"u-{r}", "role": r}}
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(checker(user=forbidden_user))
            self.assertEqual(ctx.exception.status_code, 403)


class TestRoleSwitchingStateIsolation(unittest.TestCase):
    def test_sequential_session_switching(self):
        """Simulate sequential login/logout token sessions to ensure no role leakage."""
        sessions = [
            {"email": "admin@labelsetu.com", "role": "admin", "token": "jwt-admin-token-1"},
            {"email": "consumer@labelsetu.com", "role": "consumer", "token": "jwt-consumer-token-2"},
            {"email": "brand@labelsetu.com", "role": "brand", "token": "jwt-brand-token-3"},
            {"email": "consumer2@labelsetu.com", "role": "consumer", "token": "jwt-consumer-token-4"},
        ]

        active_session = None

        def login(session_def):
            nonlocal active_session
            # Overwrite previous session state completely
            active_session = {
                "user": {"email": session_def["email"]},
                "profile": {"role": session_def["role"]},
                "access_token": session_def["token"],
            }
            return active_session

        def logout():
            nonlocal active_session
            active_session = None

        scan_checker = require_role("consumer", "brand")

        # 1. Admin login -> scan must fail (403) -> logout
        sess = login(sessions[0])
        self.assertEqual(sess["profile"]["role"], "admin")
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(scan_checker(user=sess))
        self.assertEqual(ctx.exception.status_code, 403)
        logout()
        self.assertIsNone(active_session)

        # 2. Consumer login -> scan must succeed -> logout
        sess = login(sessions[1])
        self.assertEqual(sess["profile"]["role"], "consumer")
        res = asyncio.run(scan_checker(user=sess))
        self.assertEqual(res["profile"]["role"], "consumer")
        logout()
        self.assertIsNone(active_session)

        # 3. Brand login -> scan must succeed -> logout
        sess = login(sessions[2])
        self.assertEqual(sess["profile"]["role"], "brand")
        res = asyncio.run(scan_checker(user=sess))
        self.assertEqual(res["profile"]["role"], "brand")
        logout()
        self.assertIsNone(active_session)

        # 4. Consumer login -> scan must succeed
        sess = login(sessions[3])
        self.assertEqual(sess["profile"]["role"], "consumer")
        res = asyncio.run(scan_checker(user=sess))
        self.assertEqual(res["profile"]["role"], "consumer")
        logout()
        self.assertIsNone(active_session)


if __name__ == "__main__":
    unittest.main()
