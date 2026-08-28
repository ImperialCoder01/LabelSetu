import json
from typing import List, Dict, Any, Optional
from database import supabase


def log_admin_action(
    admin_id: str,
    action_type: str,
    target_table: str,
    target_id: Optional[str] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
) -> dict:
    """
    Log a single admin action to the audit_log table.
    """
    log_data = {
        "admin_id": admin_id,
        "action_type": action_type,
        "target_table": target_table,
        "target_id": target_id,
        "old_value": json.dumps(old_value) if old_value else None,
        "new_value": json.dumps(new_value) if new_value else None,
    }

    result = supabase.table("audit_log").insert(log_data).execute()
    return result.data[0] if result.data else log_data


def log_admin_actions_batch(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Log multiple admin actions to the audit_log table in a single batched database round-trip.
    Reduces N round-trips to 1 bulk insert operation.
    """
    if not entries:
        return []

    batch_rows = []
    for entry in entries:
        batch_rows.append({
            "admin_id": entry.get("admin_id"),
            "action_type": entry.get("action_type"),
            "target_table": entry.get("target_table"),
            "target_id": entry.get("target_id"),
            "old_value": json.dumps(entry.get("old_value")) if entry.get("old_value") else None,
            "new_value": json.dumps(entry.get("new_value")) if entry.get("new_value") else None,
        })

    result = supabase.table("audit_log").insert(batch_rows).execute()
    return result.data if result.data else batch_rows
