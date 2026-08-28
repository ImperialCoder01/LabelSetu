"""
Product Registry Service — authoritative management of manufacturer products,
barcode registration, packaging artwork versions, and verification event logging.

Maintains strict state transitions, manufacturer tenant isolation, and durable event logs.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from database import supabase
from models.product_models import ProductCreate, ProductUpdate, ProductVersionCreate
from services.notification_service import create_notification

logger = logging.getLogger(__name__)

# Valid Product State Machine Transitions
VALID_PRODUCT_TRANSITIONS = {
    "draft": {"pending_approval", "archived"},
    "pending_approval": {"approved", "rejected", "draft"},
    "approved": {"suspended", "archived"},
    "suspended": {"approved", "archived"},
    "rejected": {"draft", "pending_approval"},
    "archived": {"draft"},
}


def _get_utc_now_iso() -> str:
    """Return ISO format UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _model_to_dict(model_obj: Any) -> Dict[str, Any]:
    """Helper to convert Pydantic model to dict across v1 and v2."""
    if hasattr(model_obj, "model_dump"):
        return model_obj.model_dump()
    elif hasattr(model_obj, "dict"):
        return model_obj.dict()
    return dict(model_obj)


def create_product(manufacturer_id: str, data: ProductCreate) -> Dict[str, Any]:
    """Register a new product in 'draft' or 'pending_approval' status."""
    barcode = data.barcode.strip()

    # Check for barcode duplicate in authoritative products table
    try:
        existing = supabase.table("products").select("id, product_name, manufacturer_id").eq("barcode", barcode).execute()
        if existing.data and len(existing.data) > 0:
            raise ValueError(f"Barcode '{barcode}' is already registered to product '{existing.data[0]['product_name']}'")
    except ValueError:
        raise
    except Exception as exc:
        logger.debug("Barcode uniqueness check fallback: %s", exc)

    payload = _model_to_dict(data)
    payload["manufacturer_id"] = manufacturer_id
    payload["status"] = "pending_approval"
    payload["verification_status"] = "UNDER_REVIEW"
    payload["created_at"] = _get_utc_now_iso()
    payload["updated_at"] = _get_utc_now_iso()

    try:
        res = supabase.table("products").insert(payload).execute()
        product = res.data[0] if res.data else payload

        # Create Initial Version Snapshot (v1)
        if res.data:
            product_id = product["id"]
            v_payload = {
                "product_id": product_id,
                "version_number": 1,
                "created_by": manufacturer_id,
                "status": "active",
                "snapshot": payload,
                "change_summary": "Initial product registration and artwork submission",
                "created_at": _get_utc_now_iso(),
            }
            try:
                supabase.table("product_versions").insert(v_payload).execute()
            except Exception as v_exc:
                logger.warning("Failed to create initial version record: %s", v_exc)

        # Notify Admins of pending submission
        try:
            admin_users = supabase.table("users_profile").select("id").eq("role", "admin").execute()
            if admin_users.data:
                for adm in admin_users.data:
                    create_notification(
                        user_id=adm["id"],
                        title="New Product Awaiting Approval",
                        message=f"{data.brand_name} submitted '{data.product_name}' (Barcode: {barcode}) for registration.",
                        notif_type="ACTION_REQUIRED",
                        entity_type="product",
                        entity_id=product.get("id"),
                    )
        except Exception:
            pass

        return product
    except Exception as exc:
        logger.error("Failed to insert product: %s", exc)
        raise RuntimeError(f"Database error registering product: {exc}")


def get_product_by_id(product_id: str, requesting_user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Retrieve full product details including version history."""
    try:
        res = supabase.table("products").select("*, users_profile!products_manufacturer_id_fkey(full_name)").eq("id", product_id).single().execute()
        if not res.data:
            return None
        product = res.data

        # Enforce role boundary: other manufacturers cannot view unapproved draft products
        if requesting_user:
            role = requesting_user.get("role", "consumer")
            user_id = requesting_user.get("sub")
            if role == "brand" and product["manufacturer_id"] != user_id and product["status"] != "approved":
                return None

        # Fetch versions
        try:
            v_res = supabase.table("product_versions").select("*").eq("product_id", product_id).order("version_number", desc=True).execute()
            product["versions"] = v_res.data or []
        except Exception:
            product["versions"] = []

        return product
    except Exception as exc:
        logger.error("Failed to fetch product %s: %s", product_id, exc)
        return None


def get_product_by_barcode(barcode: str) -> Optional[Dict[str, Any]]:
    """Retrieve registered product by barcode."""
    barcode = barcode.strip()
    try:
        res = supabase.table("products").select("*, users_profile!products_manufacturer_id_fkey(full_name)").eq("barcode", barcode).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as exc:
        logger.debug("Failed to lookup product by barcode %s: %s", barcode, exc)
        return None


def list_products(
    requesting_user: Dict[str, Any],
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """List products with search and role-based filtering."""
    role = requesting_user.get("role", "consumer")
    user_id = requesting_user.get("sub")

    try:
        query = supabase.table("products").select("*, users_profile!products_manufacturer_id_fkey(full_name)")

        # Brand users only see their own products
        if role == "brand":
            query = query.eq("manufacturer_id", user_id)
        elif role == "consumer":
            query = query.eq("status", "approved")

        if status:
            query = query.eq("status", status)
        if category:
            query = query.eq("category", category)
        if search:
            query = query.or_(f"product_name.ilike.%{search}%,brand_name.ilike.%{search}%,barcode.ilike.%{search}%,sku.ilike.%{search}%")

        res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return res.data or []
    except Exception as exc:
        logger.error("Failed to list products: %s", exc)
        return []


def update_product(
    product_id: str,
    user: Dict[str, Any],
    updates: ProductUpdate,
) -> Dict[str, Any]:
    """Update product information with strict authorization."""
    role = user.get("role", "consumer")
    user_id = user.get("sub")

    existing = get_product_by_id(product_id)
    if not existing:
        raise ValueError("Product not found")

    if role not in ("brand", "admin"):
        raise PermissionError(f"Access denied: Role '{role}' is not authorized to edit products")

    if role == "brand" and existing["manufacturer_id"] != user_id:
        raise PermissionError("Access denied: You cannot edit another manufacturer's product")

    payload = {k: v for k, v in _model_to_dict(updates).items() if v is not None}
    payload["updated_at"] = _get_utc_now_iso()

    try:
        res = supabase.table("products").update(payload).eq("id", product_id).execute()
        return res.data[0] if res.data else payload
    except Exception as exc:
        logger.error("Failed to update product %s: %s", product_id, exc)
        raise RuntimeError(f"Database error updating product: {exc}")


def admin_set_product_status(
    product_id: str,
    action: str,
    admin_id: str,
    reason: Optional[str] = "",
) -> Dict[str, Any]:
    """Admin action to approve, reject, suspend, or reactivate a product."""
    action = action.upper()
    existing = get_product_by_id(product_id)
    if not existing:
        raise ValueError("Product not found")

    status_map = {
        "APPROVE": ("approved", "VERIFIED"),
        "REJECT": ("rejected", "NOT_REGISTERED"),
        "SUSPEND": ("suspended", "SUSPENDED"),
        "REACTIVATE": ("approved", "VERIFIED"),
    }
    if action not in status_map:
        raise ValueError(f"Invalid admin action '{action}'. Must be APPROVE, REJECT, SUSPEND, or REACTIVATE.")

    current_status = existing.get("status", "draft")
    new_status, new_verification_status = status_map[action]

    # Validate State Transition
    allowed_transitions = VALID_PRODUCT_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_transitions and new_status != current_status:
        raise ValueError(f"Invalid status transition from '{current_status}' to '{new_status}'")

    update_data = {
        "status": new_status,
        "verification_status": new_verification_status,
        "rejection_reason": reason if action in ("REJECT", "SUSPEND") else "",
        "updated_at": _get_utc_now_iso(),
    }

    try:
        res = supabase.table("products").update(update_data).eq("id", product_id).execute()

        # Audit Log Entry
        try:
            supabase.table("audit_log").insert({
                "admin_id": admin_id,
                "action_type": f"PRODUCT_{action}",
                "target_table": "products",
                "target_id": product_id,
                "old_value": json.dumps({"status": current_status, "verification_status": existing.get("verification_status")}),
                "new_value": json.dumps({"status": new_status, "verification_status": new_verification_status, "reason": reason}),
            }).execute()
        except Exception:
            pass

        # Notify Manufacturer
        mfg_id = existing.get("manufacturer_id")
        if mfg_id:
            notif_type = "PRODUCT_APPROVAL" if action == "APPROVE" else "PRODUCT_REJECTION" if action == "REJECT" else "SUSPENSION"
            create_notification(
                user_id=mfg_id,
                title=f"Product {action.title()}d: {existing.get('product_name')}",
                message=f"Your product '{existing.get('product_name')}' status was updated to '{new_status}'. {reason or ''}".strip(),
                notif_type=notif_type,
                entity_type="product",
                entity_id=product_id,
            )

        return res.data[0] if res.data else update_data
    except Exception as exc:
        logger.error("Failed admin status transition on %s: %s", product_id, exc)
        raise RuntimeError(f"Database error executing admin action: {exc}")


def create_product_version(
    product_id: str,
    user_id: str,
    version_data: ProductVersionCreate,
) -> Dict[str, Any]:
    """Create a new version snapshot for a product revision."""
    existing = get_product_by_id(product_id)
    if not existing:
        raise ValueError("Product not found")

    # Apply updates to product if provided
    if version_data.updates:
        update_dict = {k: v for k, v in _model_to_dict(version_data.updates).items() if v is not None}
        if update_dict:
            update_dict["updated_at"] = _get_utc_now_iso()
            supabase.table("products").update(update_dict).eq("id", product_id).execute()
            existing = get_product_by_id(product_id)

    versions = existing.get("versions", [])
    next_v = max([v.get("version_number", 1) for v in versions], default=0) + 1

    v_payload = {
        "product_id": product_id,
        "version_number": next_v,
        "created_by": user_id,
        "status": "active",
        "snapshot": existing,
        "change_summary": version_data.change_summary,
        "created_at": _get_utc_now_iso(),
    }

    try:
        res = supabase.table("product_versions").insert(v_payload).execute()
        return res.data[0] if res.data else v_payload
    except Exception as exc:
        logger.error("Failed to insert product version: %s", exc)
        raise RuntimeError(f"Database error creating product version: {exc}")


def verify_barcode_authenticity(
    barcode: str,
    user_id: Optional[str] = None,
    source: str = "barcode_scan",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Consumer Barcode Authenticity Verification with Anti-Cloning & Verification Event Logging.
    """
    barcode = barcode.strip()
    product = get_product_by_barcode(barcode)
    now_iso = _get_utc_now_iso()

    # Determine Base Verification Status
    if not product:
        result = "NOT_REGISTERED"
        suspicious_flag = "NORMAL"
        message = "Product is not registered in the authoritative manufacturer registry."
    elif product.get("status") == "suspended":
        result = "SUSPENDED_PRODUCT"
        suspicious_flag = "UNDER_REVIEW"
        message = "Product registration has been suspended by regulatory authorities."
    elif product.get("status") != "approved":
        result = "INACTIVE_PRODUCT"
        suspicious_flag = "NORMAL"
        message = f"Product is registered but in '{product.get('status')}' status."
    else:
        result = "VERIFIED"
        suspicious_flag = "NORMAL"
        message = "Product is officially registered and verified by manufacturer."

    # Anti-Cloning Telemetry: Check verification frequency in last 1 hour
    try:
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        recent_scans = (
            supabase.table("product_verifications")
            .select("id", count="exact")
            .eq("barcode", barcode)
            .gte("created_at", one_hour_ago)
            .execute()
        )
        scan_count = recent_scans.count if hasattr(recent_scans, "count") and recent_scans.count is not None else 1
        if scan_count >= 50 and result == "VERIFIED":
            suspicious_flag = "SUSPICIOUS"
            result = "POSSIBLE_DUPLICATE"
            message = "High verification frequency detected for this barcode across multiple locations. Review recommended."
    except Exception as ac_exc:
        logger.debug("Anti-cloning frequency check skipped: %s", ac_exc)

    # Record Verification Event
    verif_record = {
        "product_id": product.get("id") if product else None,
        "barcode": barcode,
        "user_id": user_id,
        "result": result,
        "verification_source": source,
        "metadata": metadata or {},
        "suspicious_flag": suspicious_flag,
        "created_at": now_iso,
    }
    try:
        supabase.table("product_verifications").insert(verif_record).execute()
    except Exception as v_exc:
        logger.warning("Failed to record verification event: %s", v_exc)

    return {
        "barcode": barcode,
        "result": result,
        "suspicious_flag": suspicious_flag,
        "message": message,
        "verified_product": product,
        "timestamp": now_iso,
    }
