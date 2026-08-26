from fastapi import APIRouter, Depends
from database import supabase
from auth.dependencies import require_role

router = APIRouter()


@router.get("/all-scans")
async def list_all_scans(regulator: dict = Depends(require_role("regulator", "admin"))):
    """List all scans across all users (regulator/admin only)."""
    result = (
        supabase.table("scans")
        .select("*, users_profile!scans_user_id_fkey(full_name, role)")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/flagged")
async def list_flagged_scans(regulator: dict = Depends(require_role("regulator", "admin"))):
    """List scans with low compliance scores (regulator/admin only)."""
    result = (
        supabase.table("scans")
        .select("*, users_profile!scans_user_id_fkey(full_name, role)")
        .lt("compliance_score", 50)
        .order("compliance_score", asc=True)
        .execute()
    )
    return result.data


@router.get("/compliance-report")
async def compliance_report(regulator: dict = Depends(require_role("regulator", "admin"))):
    """Get compliance summary statistics (regulator/admin only)."""
    all_scans = (
        supabase.table("scans").select("compliance_score, missing_fields").execute()
    )

    if not all_scans.data:
        return {"total": 0, "high": 0, "medium": 0, "low": 0, "avg_score": 0}

    scores = [s["compliance_score"] or 0 for s in all_scans.data]

    return {
        "total": len(scores),
        "high": len([s for s in scores if s >= 80]),
        "medium": len([s for s in scores if 50 <= s < 80]),
        "low": len([s for s in scores if s < 50]),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
    }
