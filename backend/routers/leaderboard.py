"""
Leaderboard Router — public endpoint for brand compliance leaderboard.

GET /api/leaderboard — top 10 brands ranked by average compliance score
"""

from fastapi import APIRouter
from database import supabase

router = APIRouter()


@router.get("")
async def get_leaderboard():
    """
    Return the top 10 brands ranked by average compliance score.

    Public endpoint — no authentication required.

    Joins scans with users_profile to group by brand user,
    computes average score and scan count per brand.
    """
    result = (
        supabase.table("scans")
        .select("compliance_score, user_id, users_profile!scans_user_id_fkey(full_name, role)")
        .execute()
    )

    if not result.data:
        return []

    # Aggregate by user_id
    brands = {}
    for scan in result.data:
        profile = scan.get("users_profile")
        if not profile:
            continue
        uid = scan["user_id"]
        if uid not in brands:
            brands[uid] = {
                "user_id": uid,
                "brand_name": profile.get("full_name", "Unknown"),
                "scores": [],
            }
        brands[uid]["scores"].append(scan.get("compliance_score", 0))

    # Compute averages and rank
    leaderboard = []
    for uid, info in brands.items():
        scores = info["scores"]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0
        leaderboard.append({
            "user_id": uid,
            "brand_name": info["brand_name"],
            "average_score": avg_score,
            "scan_count": len(scores),
        })

    leaderboard.sort(key=lambda b: b["average_score"], reverse=True)
    return leaderboard[:10]
