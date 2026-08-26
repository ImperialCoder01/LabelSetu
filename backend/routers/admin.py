"""
Admin Router

GET    /api/admin/rules        — read current rules.json
PUT    /api/admin/rules        — write updated rules.json + audit log entry
GET    /api/admin/audit-logs   — list audit logs
POST   /api/admin/audit-log    — create an audit log entry
GET    /api/admin/api-usage    — API usage stats
GET    /api/admin/stats        — system stats
"""

import json
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from database import supabase
from auth.dependencies import require_role

router = APIRouter()

RULES_PATH = Path(__file__).parent.parent.parent / "docs" / "rules.json"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class RulesUpdate(BaseModel):
    rules: dict[str, Any]
    change_summary: str = ""


class AuditLogEntry(BaseModel):
    action_type: str
    target_table: str = "rules_config"
    target_id: str | None = None
    old_value: dict | None = None
    new_value: dict | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_rules() -> dict:
    if not RULES_PATH.exists():
        raise HTTPException(status_code=404, detail="rules.json not found")
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_rules(rules: dict) -> None:
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)


def _create_audit_log(admin_id: str, action: str, target_table: str, target_id: str | None, old_val: Any, new_val: Any) -> None:
    """Insert an entry into the audit_log table via Supabase."""
    entry = {
        "admin_id": admin_id,
        "action_type": action,
        "target_table": target_table,
        "old_value": json.dumps(old_val) if old_val else None,
        "new_value": json.dumps(new_val) if new_val else None,
    }
    if target_id:
        entry["target_id"] = target_id
    try:
        supabase.table("audit_log").insert(entry).execute()
    except Exception:
        pass  # best-effort; don't fail the request if audit write fails


# ---------------------------------------------------------------------------
# Rules CRUD
# ---------------------------------------------------------------------------
@router.get("/rules")
async def get_rules(admin: dict = Depends(require_role("admin"))):
    """Read the current compliance rules from rules.json."""
    return _read_rules()


@router.put("/rules")
async def update_rules(body: RulesUpdate, admin: dict = Depends(require_role("admin"))):
    """
    Write updated rules to rules.json and create an audit log entry.
    The entire rules dict is replaced (not merged).
    """
    old_rules = _read_rules()
    _write_rules(body.rules)
    _create_audit_log(
        admin_id=admin["sub"],
        action="UPDATE",
        target_table="rules_config",
        target_id=body.rules.get("version", "unknown"),
        old_val={"fields_count": len(old_rules.get("fields", [])), "scoring": old_rules.get("scoring")},
        new_val={"fields_count": len(body.rules.get("fields", [])), "scoring": body.rules.get("scoring"), "summary": body.change_summary},
    )
    return {"success": True, "message": "Rules updated"}


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
@router.get("/audit-logs")
async def list_audit_logs(
    admin: dict = Depends(require_role("admin")),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """List audit logs with optional date range filter (admin only)."""
    query = (
        supabase.table("audit_log")
        .select("*, users_profile!audit_log_admin_id_fkey(full_name)")
        .order("timestamp", desc=True)
        .limit(500)
    )
    if start_date:
        query = query.gte("timestamp", start_date)
    if end_date:
        # Append end-of-day so the full end_date is included
        query = query.lte("timestamp", end_date + "T23:59:59")
    result = query.execute()
    return result.data


@router.post("/audit-log")
async def create_audit_log(body: AuditLogEntry, admin: dict = Depends(require_role("admin"))):
    """Create an audit log entry (admin only)."""
    _create_audit_log(
        admin_id=admin["sub"],
        action=body.action_type,
        target_table=body.target_table,
        target_id=body.target_id,
        old_val=body.old_value,
        new_val=body.new_value,
    )
    return {"success": True}


# ---------------------------------------------------------------------------
# Other admin endpoints
# ---------------------------------------------------------------------------
@router.get("/api-usage")
async def get_api_usage(admin: dict = Depends(require_role("admin"))):
    """Get API usage statistics (admin only)."""
    result = (
        supabase.table("api_usage_log")
        .select("*")
        .order("month", desc=True)
        .execute()
    )
    return result.data


@router.get("/stats")
async def get_system_stats(admin: dict = Depends(require_role("admin"))):
    """Get overall system statistics (admin only)."""
    users_count = supabase.table("users_profile").select("id", count="exact").execute()
    scans_count = supabase.table("scans").select("id", count="exact").execute()
    return {
        "total_users": users_count.count or 0,
        "total_scans": scans_count.count or 0,
    }
