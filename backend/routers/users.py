from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import supabase
from auth.dependencies import get_current_user, require_role

router = APIRouter()


class ProfileUpdate(BaseModel):
    full_name: str | None = None


@router.get("/me")
async def get_my_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile."""
    return user["profile"]


@router.put("/me")
async def update_my_profile(
    update: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Update current user's profile."""
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        supabase.table("users_profile")
        .update(update_data)
        .eq("id", user["sub"])
        .execute()
    )

    return result.data[0] if result.data else {"message": "Profile updated"}


@router.get("/")
async def list_users(admin: dict = Depends(require_role("admin"))):
    """List all users (admin only)."""
    result = supabase.table("users_profile").select("*").execute()
    return result.data
