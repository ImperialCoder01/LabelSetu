import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from config import settings
from database import supabase

logger = logging.getLogger(__name__)
security = HTTPBearer()


def decode_token(token: str) -> dict:
    """Decode and verify Supabase JWT token."""
    if not settings.SUPABASE_JWT_SECRET or settings.SUPABASE_JWT_SECRET == "your-jwt-secret-here":
        logger.warning("[AUTH DEBUG] SUPABASE_JWT_SECRET is set to default placeholder ('your-jwt-secret-here')")

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        logger.info("[AUTH DEBUG] JWT decode succeeded")
        return payload
    except JWTError as e:
        err_msg = str(e).lower()
        if "signature" in err_msg:
            logger.warning("[AUTH DEBUG] JWT decode failed: signature verification")
        elif "audience" in err_msg or "aud" in err_msg:
            logger.warning("[AUTH DEBUG] JWT decode failed: audience")
        elif "expired" in err_msg or "exp" in err_msg:
            logger.warning("[AUTH DEBUG] JWT decode failed: expiration")
        else:
            logger.warning("[AUTH DEBUG] JWT decode failed: malformed token (%s)", type(e).__name__)

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
            .maybeSingle()
            .execute()
        )
        profile_data = result.data
    except Exception as exc:
        logger.error("[AUTH DEBUG] User profile lookup exception: %s", exc)

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
