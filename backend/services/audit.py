import json
from database import supabase


def log_admin_action(
    admin_id: str,
    action_type: str,
    target_table: str,
    target_id: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> dict:
    """
    Log an admin action to the audit_log table.

    Args:
        admin_id: ID of the admin performing the action
        action_type: Type of action (e.g., "UPDATE_USER", "DELETE_SCAN")
        target_table: Table being affected
        target_id: ID of the affected record
        old_value: Previous state (JSON)
        new_value: New state (JSON)

    Returns:
        Created audit log entry
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
