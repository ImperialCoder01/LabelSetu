# 🏛️ LabelSetu Technical Architecture & Evidence Isolation Model

---

## Overview

LabelSetu is designed around the fundamental principle of **Authoritative Statutory Compliance with Supplementary AI Assistance**. This document outlines the technical architecture, evidence segregation rules, and data contracts between system components.

---

## 1. Two-Layer Evidence Model

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: PACKAGE EVIDENCE                       │
│  - Sources: Uploaded packaging photos, OpenCV processing, OCR tokens   │
│  - Processing: Deterministic Legal Metrology Rule Engine               │
│  - Authority: 100% SOLE AUTHORITY for compliance score & pass/fail    │
│  - Field Tag: package_verified = true                                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   LAYER 2: EXTERNAL REFERENCE EVIDENCE                 │
│  - Sources: GTIN Barcodes, Open Food Facts, National FMCG Catalog      │
│  - Processing: Product Research Service & Groq AI Assistance          │
│  - Authority: Informational / Reference ONLY                           │
│  - Field Tag: package_verified = false, REQUIRES_PACKAGE_VERIFICATION  │
│  - Safety Rule: ZERO False Approvals (Never turns FAIL into PASS)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 Image Preprocessing (`backend/services/image_processor.py`)
- **Auto-Deskew**: Calculates bounding box angles of text contours to rotate tilted package captures.
- **CLAHE Contrast Enhancement**: Applies Contrast Limited Adaptive Histogram Equalization for glossy or unevenly lit packaging panels.
- **Client-Side Optimization**: Frontend scales images to max 1600px before uploading to conserve bandwidth and prevent server memory spikes.

### 2.2 OCR Service (`backend/services/ocr_service.py`)
- **Primary**: Cloud OCR engine (OCR.space Tier) with structured token confidence scores.
- **Fallback**: Local CPU-based EasyOCR when network or quota limits are reached.

### 2.3 Entity Extraction (`backend/services/entity_extractor.py`)
- High-precision regular expressions and NER patterns extracting:
  - Product Name, Brand Name, Manufacturer / Packer Address
  - Net Quantity (metric units: g, kg, ml, l)
  - MRP (inclusive of all taxes syntax)
  - Manufacturing Date, Packaging Date, Expiry Date
  - Consumer Care (Helpline, Email, Postal Address)
  - Country of Origin
  - Unit Sale Price (USP)

### 2.4 Deterministic Rule Engine (`backend/services/rule_engine.py`)
- Evaluates extracted entities against statutory criteria defined in `backend/models/rules.json`.
- Calculates `overall_score` (0–100) and categorizes violations into `Critical` vs `Minor`.
- Aggregates multi-image evidence across Front, Back, Side, and Flap panels.

### 2.5 Groq AI Inference Engine (`backend/services/ai_service.py`)
- Active Model: `openai/gpt-oss-20b` via Groq Cloud API.
- Delivers JSON-structured semantic interpretation, plain-English summary, and actionable brand compliance recommendations.
- **Non-blocking**: Errors, timeouts (12s), or rate limits trigger structured fallbacks without failing the user scan.

### 2.6 External Product Research Service (`backend/services/product_research_service.py`)
- Queries National FMCG Standard Catalog and Open Food Facts API.
- Matches product identity via Barcode/GTIN or token overlap with confidence scoring.
- Flags missing package declarations with reference values, tagging each as `package_verified = False` and `REQUIRES_PACKAGE_VERIFICATION`.
- Recommends specific physical panel photos (e.g., Back Panel, Date-Code Flap) to complete the audit.

---

## 3. Data Contracts & Output Schemas

### Scan Response Schema (`POST /api/scans/scan`)
```json
{
  "scan_id": "5c2bd87d-ff40-474a-96e6-e1f07e9f06b9",
  "image_count": 1,
  "ocr": {
    "provider": "cloud",
    "full_text": "...",
    "average_confidence": 0.94
  },
  "compliance": {
    "overall_score": 75,
    "status": "partial",
    "passed": 5,
    "failed": 3,
    "fields": [
      {
        "field_id": "mrp",
        "field_name": "Maximum Retail Price (MRP)",
        "severity": "Critical",
        "status": "fail",
        "evidence_status": "CONFIRMED_MISSING",
        "extracted_value": null
      }
    ]
  },
  "ai_analysis": {
    "available": true,
    "status": "success",
    "provider": "groq",
    "model": "openai/gpt-oss-20b",
    "explanation": "...",
    "recommendations": ["..."]
  },
  "external_research": {
    "status": "success",
    "product_match": {
      "name": "Tata Salt Iodised 1kg",
      "brand": "Tata",
      "confidence": 0.92,
      "confidence_level": "high_confidence",
      "matched_by": "brand_and_name"
    },
    "sources": [
      {
        "name": "National FMCG Packaging Standard Catalog",
        "url": "https://legalmetrology.gov.in/catalog/8901030300000",
        "source_type": "official_catalog"
      }
    ],
    "fields": [
      {
        "field_id": "mrp",
        "field_name": "Reference Maximum Retail Price (MRP)",
        "value": "Rs 28.00",
        "source_type": "external_reference",
        "package_verified": false,
        "verification_status": "REQUIRES_PACKAGE_VERIFICATION",
        "is_package_specific": true,
        "explanation": "Reference value found online. This declaration varies by packaging batch and MUST be physically verified from the printed package label."
      }
    ],
    "recommended_photos": [
      {
        "panel": "Back Panel or Price Stamp Area",
        "reason": "Not visible in uploaded images",
        "recommendation": "Upload a clear Back Panel or Price Stamp area showing the printed MRP and Unit Sale Price."
      }
    ],
    "identity_conflict": false,
    "disclaimer": "External product information is provided as a reference only. It does not prove that these declarations appear on the specific package you scanned."
  }
}
```
