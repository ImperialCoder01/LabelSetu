"""
Unit Tests for Admin API Usage & Telemetry Endpoint (/api/usage)
"""

import sys
import unittest
import asyncio
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from auth.dependencies import require_role

client = TestClient(app)


class TestApiUsageEndpoint(unittest.TestCase):
    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests to /api/usage must return HTTP 401."""
        res = client.get("/api/usage")
        self.assertEqual(res.status_code, 401)

    def test_consumer_forbidden(self):
        """Consumer role must be forbidden from /api/usage (HTTP 403)."""
        checker = require_role("admin")
        user = {"sub": "u-c", "profile": {"id": "u-c", "role": "consumer"}}
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(checker(user=user))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_brand_forbidden(self):
        """Brand role must be forbidden from /api/usage (HTTP 403)."""
        checker = require_role("admin")
        user = {"sub": "u-b", "profile": {"id": "u-b", "role": "brand"}}
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(checker(user=user))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_regulator_forbidden(self):
        """Regulator role must be forbidden from /api/usage (HTTP 403)."""
        checker = require_role("admin")
        user = {"sub": "u-r", "profile": {"id": "u-r", "role": "regulator"}}
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(checker(user=user))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_allowed_role_check(self):
        """Admin role passes require_role('admin') check."""
        checker = require_role("admin")
        user = {"sub": "u-a", "profile": {"id": "u-a", "role": "admin"}}
        res = asyncio.run(checker(user=user))
        self.assertEqual(res["profile"]["role"], "admin")


if __name__ == "__main__":
    unittest.main()
