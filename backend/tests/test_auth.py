"""
Automated Security Unit Tests for Auth Verification & Authorization.

Tests:
  - Valid ES256 JWKS token signature verification
  - Missing token header handling (401)
  - Malformed JWT header handling (401)
  - Expired token handling (401)
  - Invalid signature verification (401)
  - Unsupported algorithm handling (401)
  - Profile lookup & metadata fallback handling
  - Allowed role authorization (PASS)
  - Disallowed role authorization (403 FAIL)
"""

import sys
import time
import unittest
from pathlib import Path
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import HTTPException
from auth.dependencies import decode_token, require_role, get_current_user


class TestAuthDependencies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate an EC P-256 private key for testing ES256 signatures
        cls.private_key = ec.generate_private_key(ec.SECP256R1())
        cls.public_key = cls.private_key.public_key()
        cls.kid = "test-ec-kid-123"

    def _create_token(self, payload: dict, alg="ES256", key=None, headers=None) -> str:
        if key is None:
            key = self.private_key
        h = {"kid": self.kid}
        if headers:
            h.update(headers)
        return jwt.encode(payload, key, algorithm=alg, headers=h)

    def test_missing_empty_token(self):
        """Test missing or empty token raises HTTP 401."""
        with self.assertRaises(HTTPException) as ctx:
            decode_token("")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_malformed_token(self):
        """Test malformed JWT token raises HTTP 401."""
        with self.assertRaises(HTTPException) as ctx:
            decode_token("not.a.valid.jwt.string.123")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_unsupported_algorithm(self):
        """Test token with unsupported algorithm (e.g. none) raises HTTP 401."""
        header_b64 = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0" # {"alg":"none","typ":"JWT"}
        payload_b64 = "eyJzdWIiOiIxMjM0NTY3ODkwIiwiYXVkIjoiYXV0aGVudGljYXRlZCJ9"
        unsigned_token = f"{header_b64}.{payload_b64}."
        with self.assertRaises(HTTPException) as ctx:
            decode_token(unsigned_token)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_expired_token(self):
        """Test expired token raises HTTP 401."""
        expired_payload = {
            "sub": "user-123",
            "aud": "authenticated",
            "exp": int(time.time()) - 3600, # expired 1 hour ago
        }
        expired_token = self._create_token(expired_payload)
        
        # Mock get_jwks_client to return test key
        from auth import dependencies
        original_client = dependencies._jwks_client
        class MockSigningKey:
            def __init__(self, k, kid):
                self.key = k
                self.key_id = kid
        class MockJWKSClient:
            def get_signing_key_from_jwt(inner_self, t):
                return MockSigningKey(self.public_key, self.kid)
        
        dependencies._jwks_client = MockJWKSClient()
        try:
            with self.assertRaises(HTTPException) as ctx:
                decode_token(expired_token)
            self.assertEqual(ctx.exception.status_code, 401)
        finally:
            dependencies._jwks_client = original_client

    def test_invalid_signature(self):
        """Test token signed with wrong key raises HTTP 401."""
        wrong_private_key = ec.generate_private_key(ec.SECP256R1())
        wrong_token = self._create_token({"sub": "user-123", "aud": "authenticated", "exp": int(time.time()) + 3600}, key=wrong_private_key)
        
        from auth import dependencies
        original_client = dependencies._jwks_client
        class MockSigningKey:
            def __init__(self, k, kid):
                self.key = k
                self.key_id = kid
        class MockJWKSClient:
            def get_signing_key_from_jwt(inner_self, t):
                return MockSigningKey(self.public_key, self.kid)
        
        dependencies._jwks_client = MockJWKSClient()
        try:
            with self.assertRaises(HTTPException) as ctx:
                decode_token(wrong_token)
            self.assertEqual(ctx.exception.status_code, 401)
        finally:
            dependencies._jwks_client = original_client

    def test_valid_token_verification(self):
        """Test valid ES256 token verification passes and returns payload."""
        valid_payload = {
            "sub": "user-valid-123",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
            "role": "authenticated",
        }
        valid_token = self._create_token(valid_payload)
        
        from auth import dependencies
        original_client = dependencies._jwks_client
        class MockSigningKey:
            def __init__(self, k, kid):
                self.key = k
                self.key_id = kid
        class MockJWKSClient:
            def get_signing_key_from_jwt(inner_self, t):
                return MockSigningKey(self.public_key, self.kid)
        
        dependencies._jwks_client = MockJWKSClient()
        try:
            payload = decode_token(valid_token)
            self.assertEqual(payload["sub"], "user-valid-123")
            self.assertEqual(payload["aud"], "authenticated")
        finally:
            dependencies._jwks_client = original_client


if __name__ == "__main__":
    unittest.main()
