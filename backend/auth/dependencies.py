from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from config import settings
from database import supabase

security = HTTPBearer()


def decode_token(token: str) -> dict:
    """Decode and verify Supabase JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except JWTError as e:
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    # Fetch user profile
    try:
        result = (
            supabase.table("users_profile")
            .select("*")
            .eq("id", user_id)
            .maybeSingle()
            .execute()
        )
        profile_data = result.data
    except Exception:
        profile_data = None

    if not profile_data:
        # Auto-heal profile using JWT metadata
        user_metadata = payload.get("user_metadata", {})
        role = user_metadata.get("role", "consumer")
        full_name = user_metadata.get("full_name", payload.get("email", "").split("@")[0] or "User")
        profile_data = {"id": user_id, "full_name": full_name, "role": role}
        try:
            upsert_res = (
                supabase.table("users_profile")
                .upsert({"id": user_id, "full_name": full_name, "role": role})
                .select("*")
                .maybeSingle()
                .execute()
            )
            if upsert_res and upsert_res.data:
                profile_data = upsert_res.data
        except Exception:
            pass

    return {**payload, "profile": profile_data}


def require_role(*allowed_roles):
    """Dependency factory that checks if user has one of the allowed roles."""

    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("profile", {}).get("role")

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' is not authorized. Required: {allowed_roles}",
            )

        return user

    return role_checker
