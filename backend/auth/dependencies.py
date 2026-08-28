import logging
import jwt
from jwt import PyJWKClient, PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from database import supabase

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Lazy initialized PyJWKClient instance for trusted Supabase JWKS public keys
_jwks_client = None


def get_jwks_client() -> PyJWKClient:
    """Get or initialize the PyJWKClient bound to the configured Supabase project domain."""
    global _jwks_client
    if _jwks_client is None:
        base_url = (settings.SUPABASE_URL or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("SUPABASE_URL setting is missing or empty")
        jwks_url = f"{base_url}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
        logger.info("[AUTH DEBUG] Initialized JWKS client for URL: %s", jwks_url)
    return _jwks_client


def decode_token(token: str) -> dict:
    """
    Decode and cryptographically verify Supabase JWT token.
    Supports:
      - ES256 / RS256 (asymmetric signing via trusted Supabase JWKS)
      - HS256 (symmetric signing via configured SUPABASE_JWT_SECRET)
    """
    if not token or not token.strip():
        logger.warning("[AUTH DEBUG] JWT decode failed: malformed token (empty string)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: Empty authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Unverified header inspection to detect algorithm and kid
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        logger.warning("[AUTH DEBUG] JWT decode failed: malformed token (%s)", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: Malformed header ({str(exc)})",
            headers={"WWW-Authenticate": "Bearer"},
        )

    alg = header.get("alg", "").upper()
    kid = header.get("kid")
    logger.info("[AUTH DEBUG] JWT algorithm detected: %s | Key ID found: %s", alg, "yes" if kid else "no")

    # 2. Cryptographic Verification based on Algorithm
    try:
        if alg in ("ES256", "RS256", "ES384", "ES512"):
            # Asymmetric Public Key Verification via trusted JWKS
            client = get_jwks_client()
            signing_key = client.get_signing_key_from_jwt(token)
            logger.info("[AUTH DEBUG] JWKS lookup: success")

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
            )
            logger.info("[AUTH DEBUG] Signature verification: success")
            logger.info("[AUTH DEBUG] Claims validation: success")
            return payload

        elif alg == "HS256":
            # Symmetric Secret Verification for legacy HS256 tokens
            secret = settings.SUPABASE_JWT_SECRET
            if not secret or secret == "your-jwt-secret-here":
                logger.warning("[AUTH DEBUG] SUPABASE_JWT_SECRET is placeholder or missing for HS256 token")

            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            logger.info("[AUTH DEBUG] Signature verification: success (HS256)")
            logger.info("[AUTH DEBUG] Claims validation: success")
            return payload

        else:
            logger.warning("[AUTH DEBUG] JWT decode failed: unsupported algorithm (%s)", alg)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: Unsupported algorithm '{alg}'",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except PyJWTError as e:
        err_msg = str(e).lower()
        if "expired" in err_msg or "exp" in err_msg:
            logger.warning("[AUTH DEBUG] JWT decode failed: expiration")
        elif "audience" in err_msg or "aud" in err_msg:
            logger.warning("[AUTH DEBUG] JWT decode failed: audience")
        elif "signature" in err_msg or "verify" in err_msg:
            logger.warning("[AUTH DEBUG] JWT decode failed: signature verification")
        else:
            logger.warning("[AUTH DEBUG] JWT decode failed: %s", type(e).__name__)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.warning("[AUTH DEBUG] JWT decode failed: unexpected error (%s)", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Get current authenticated user from JWT token."""
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id:
        logger.warning("[AUTH DEBUG] JWT decode failed: token missing user ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    # Fetch user profile
    profile_data = None
    try:
        result = (
            supabase.table("users_profile")
            .select("*")
            .eq("id", user_id)
            .execute()
        )
        profile_data = result.data[0] if result.data and len(result.data) > 0 else None
    except Exception as exc:
        logger.error("[AUTH DEBUG] User profile lookup exception: %s", exc)
        profile_data = None

    if profile_data:
        logger.info("[AUTH DEBUG] User profile found")
    else:
        logger.warning("[AUTH DEBUG] User profile lookup failed (using token metadata fallback)")
        user_metadata = payload.get("user_metadata", {})
        role = user_metadata.get("role", "consumer")
        full_name = user_metadata.get("full_name", payload.get("email", "").split("@")[0] or "User")
        profile_data = {"id": user_id, "full_name": full_name, "role": role}

    return {**payload, "profile": profile_data}


def require_role(*allowed_roles):
    """Dependency factory that checks if user has one of the allowed roles."""

    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("profile", {}).get("role")

        if user_role not in allowed_roles:
            logger.warning("[AUTH DEBUG] Role check failed (User role: %s, Required: %s)", user_role, allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' is not authorized. Required: {allowed_roles}",
            )

        logger.info("[AUTH DEBUG] Role check passed")
        return user

    return role_checker
