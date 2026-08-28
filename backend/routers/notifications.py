"""
Notifications Router — user alerts, case updates, and admin action notifications.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from auth.dependencies import get_current_user
from services import notification_service as ns

router = APIRouter()


@router.get("")
async def list_notifications(
    unread_only: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    """List current user notifications."""
    return ns.list_notifications(user_id=user["sub"], unread_only=unread_only)


@router.patch("/{notif_id}/read")
async def mark_read(
    notif_id: str,
    user: dict = Depends(get_current_user),
):
    """Mark a notification as read."""
    success = ns.mark_notification_read(notif_id=notif_id, user_id=user["sub"])
    return {"success": success}
