"""
Products Router — complete CRUD, submission, versioning, and administrative
governance for registered manufacturer commodities.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from auth.dependencies import get_current_user, require_role
from models.product_models import (
    ProductCreate,
    ProductUpdate,
    ProductVersionCreate,
    ProductAdminAction,
)
from services import product_registry_service as prs

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    user: dict = Depends(require_role("brand", "admin")),
):
    """
    Register a new product in the authoritative registry.
    Manufacturer enters identity, barcode, packaging images, and statutory declarations.
    """
    try:
        product = prs.create_product(manufacturer_id=user["sub"], data=data)
        return product
    except ValueError as val_err:
        raise HTTPException(status_code=409, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("")
async def list_products(
    search: Optional[str] = Query(None, description="Search by name, brand, barcode, SKU"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (approved, pending_approval, draft, suspended)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    """
    List products.
    - Manufacturers see only their own products.
    - Consumers see approved products.
    - Admins and Regulators see all products with search & filters.
    """
    return prs.list_products(
        requesting_user=user,
        search=search,
        status=status_filter,
        category=category,
        limit=limit,
        offset=offset,
    )


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    user: dict = Depends(get_current_user),
):
    """Retrieve full product details including version history."""
    product = prs.get_product_by_id(product_id=product_id, requesting_user=user)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found or access restricted")
    return product


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    updates: ProductUpdate,
    user: dict = Depends(require_role("brand", "admin")),
):
    """
    Update product details.
    Manufacturers can only edit their own draft or rejected products.
    Admins can edit any product.
    """
    try:
        updated = prs.update_product(product_id=product_id, user=user, updates=updates)
        return updated
    except PermissionError as perm_err:
        raise HTTPException(status_code=403, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{product_id}/version", status_code=status.HTTP_201_CREATED)
async def create_product_version(
    product_id: str,
    version_data: ProductVersionCreate,
    user: dict = Depends(require_role("brand", "admin")),
):
    """Create a new version revision snapshot for a product."""
    try:
        v = prs.create_product_version(product_id=product_id, user_id=user["sub"], version_data=version_data)
        return v
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{product_id}/action")
async def admin_product_action(
    product_id: str,
    body: ProductAdminAction,
    admin: dict = Depends(require_role("admin")),
):
    """
    Admin control action: APPROVE, REJECT, SUSPEND, or REACTIVATE a product.
    Generates immutable audit log entry and notifies the manufacturer.
    """
    try:
        result = prs.admin_set_product_status(
            product_id=product_id,
            action=body.action,
            admin_id=admin["sub"],
            reason=body.reason,
        )
        return {"success": True, "action": body.action, "product": result}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
