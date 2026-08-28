"""
Notification Service — manages in-app alerts and notifications for
manufacturers, regulators, consumers, and administrators.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import supabase

logger = logging.getLogger(__name__)


def create_notification(
    user_id: str,
    title: str,
    message: str,
    notif_type: str = "INFO",
    entity_type: str = "",
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an in-app notification entry for a user."""
    payload = {
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notif_type,
        "entity_type": entity_type,
        "is_read": False,
    }
    if entity_id:
        payload["entity_id"] = entity_id

    try:
        res = supabase.table("notifications").insert(payload).execute()
        return res.data[0] if res.data else payload
    except Exception as exc:
        logger.warning("Failed to insert notification into database: %s", exc)
        return payload


def list_notifications(user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
    """List notifications for a user, newest first."""
    try:
        query = supabase.table("notifications").select("*").eq("user_id", user_id)
        if unread_only:
            query = query.eq("is_read", False)
        res = query.order("created_at", desc=True).limit(50).execute()
        return res.data or []
    except Exception as exc:
        logger.warning("Failed to list notifications: %s", exc)
        return []


def mark_notification_read(notif_id: str, user_id: str) -> bool:
    """Mark a specific notification as read."""
    try:
        supabase.table("notifications").update({"is_read": True}).eq("id", notif_id).eq("user_id", user_id).execute()
        return True
    except Exception as exc:
        logger.warning("Failed to mark notification read: %s", exc)
        return False
