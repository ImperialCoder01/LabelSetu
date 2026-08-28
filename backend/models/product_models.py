"""
Product Models — Pydantic validation schemas for the complete
Manufacturer → Product → Consumer → Executive → Admin workflow.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    product_name: str = Field(..., min_length=2, max_length=200)
    brand_name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=2, max_length=100)
    subcategory: Optional[str] = ""
    sku: Optional[str] = ""
    barcode: str = Field(..., min_length=6, max_length=20)
    barcode_type: Optional[str] = "EAN-13"
    gtin: Optional[str] = ""
    description: Optional[str] = ""
    mrp: Optional[float] = None
    net_quantity: Optional[str] = ""
    unit_sale_price: Optional[str] = ""
    manufacturing_date_info: Optional[str] = ""
    expiry_info: Optional[str] = ""
    batch_info: Optional[str] = ""
    manufacturer_name_address: Optional[str] = ""
    packer_name_address: Optional[str] = ""
    importer_name_address: Optional[str] = ""
    country_of_origin: Optional[str] = "India"
    consumer_care: Optional[str] = ""
    fssai_lic: Optional[str] = ""
    ingredients: Optional[str] = ""
    veg_non_veg: Optional[str] = ""
    category_declarations: Optional[Dict[str, Any]] = {}
    primary_image_url: Optional[str] = ""
    front_image_url: Optional[str] = ""
    back_image_url: Optional[str] = ""
    side_image_urls: Optional[List[str]] = []


class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    brand_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    mrp: Optional[float] = None
    net_quantity: Optional[str] = None
    unit_sale_price: Optional[str] = None
    manufacturing_date_info: Optional[str] = None
    expiry_info: Optional[str] = None
    batch_info: Optional[str] = None
    manufacturer_name_address: Optional[str] = None
    packer_name_address: Optional[str] = None
    importer_name_address: Optional[str] = None
    country_of_origin: Optional[str] = None
    consumer_care: Optional[str] = None
    fssai_lic: Optional[str] = None
    ingredients: Optional[str] = None
    veg_non_veg: Optional[str] = None
    category_declarations: Optional[Dict[str, Any]] = None
    primary_image_url: Optional[str] = None
    front_image_url: Optional[str] = None
    back_image_url: Optional[str] = None
    side_image_urls: Optional[List[str]] = None


class ProductVersionCreate(BaseModel):
    change_summary: str = Field(..., min_length=3)
    updates: Optional[ProductUpdate] = None


class ProductAdminAction(BaseModel):
    action: str = Field(..., description="APPROVE | REJECT | SUSPEND | REACTIVATE")
    reason: Optional[str] = ""


class BarcodeVerifyRequest(BaseModel):
    barcode: str = Field(..., min_length=6, max_length=20)
    verification_source: Optional[str] = "barcode_scan"
    metadata: Optional[Dict[str, Any]] = {}


class CrossValidateRequest(BaseModel):
    barcode: str
    ocr_text: Optional[str] = ""
    extracted_entities: Optional[Dict[str, Any]] = {}
    scan_id: Optional[str] = None


class ExecutiveReportCreate(BaseModel):
    product_id: Optional[str] = None
    barcode: Optional[str] = ""
    report_type: str = Field("VIOLATION", description="VIOLATION | SUSPECTED_COUNTERFEIT | INFO_DISCREPANCY | PACKAGING_DISCREPANCY | MISSING_DECLARATION | MANUFACTURER_ISSUE | CONSUMER_COMPLAINT")
    severity: str = Field("MEDIUM", description="LOW | MEDIUM | HIGH | CRITICAL")
    description: str = Field(..., min_length=10)
    detected_issue: Optional[str] = ""
    applicable_rule: Optional[str] = ""
    evidence: Optional[Dict[str, Any]] = {}
    executive_observations: Optional[str] = ""
    recommended_action: str = Field("WARNING_NOTICE", description="WARNING_NOTICE | SUSPEND_PRODUCT | PRODUCT_RECALL | SEIZE_BATCH | REQUEST_INFO | FURTHER_INVESTIGATION | NO_ACTION")


class ExecutiveReportAdminDecision(BaseModel):
    decision: str = Field(..., description="APPROVED | REJECTED | MORE_INFORMATION_REQUIRED")
    comments: Optional[str] = ""
    final_action_taken: Optional[str] = ""


class ConsumerGrievanceCreate(BaseModel):
    barcode: Optional[str] = ""
    product_id: Optional[str] = None
    scan_id: Optional[str] = None
    issue_type: str = Field("SUSPECTED_COUNTERFEIT", description="SUSPECTED_COUNTERFEIT | MRP_OVERCHARGE | DAMAGED_PACKAGING | MISSING_DECLARATION | EXPIRED_PRODUCT | OTHER")
    description: str = Field(..., min_length=5)
    image_url: Optional[str] = ""
