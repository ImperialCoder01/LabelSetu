# 📋 Product Requirements Document (PRD)
## LabelSetu — AI-Powered Legal Metrology & Packaging Compliance Platform

---

**Version:** 2.0 (Production Verified)  
**Target Event:** Smart India Hackathon (SIH 2026)  
**Status:** Implemented & Verified  
**Live Frontend:** https://labelsetu-ivory.vercel.app  
**Live Backend:** https://labelsetu.onrender.com  

---

## 1. Executive Summary

**LabelSetu** is an end-to-end statutory compliance auditing platform designed to enforce the **Legal Metrology (Packaged Commodities) Rules, 2011** across packaged goods in India.

The platform enables:
1. **Consumers** to instantly scan multi-panel packaging, detect missing statutory declarations (MRP, Net Qty, Mfg Date, Manufacturer), and lodge structured grievances with regulatory officers.
2. **Brands & FMCG Manufacturers** to perform pre-market packaging verification and receive actionable AI recommendations.
3. **Regulators & Officers** to monitor market non-compliance trends, investigate consumer grievances, and export audit reports.
4. **Administrators** to track system telemetry, OCR cloud quotas, Groq LLM inference health, and audit logs.

---

## 2. Evidence Architecture & Legal Safety Model

The core architectural requirement of LabelSetu is the **Strict Two-Layer Evidence Model**:

### Layer 1: Package Evidence (Authoritative)
- Extracted strictly from user-uploaded packaging images via OpenCV preprocessing, multi-tier OCR, and deterministic regex/NER extraction.
- **Sole authority** for the legal compliance score (0–100) and statutory pass/fail determinations.
- Field status: `package_verified = true`.

### Layer 2: External Reference Evidence (Supplementary)
- Retrieved from public databases (National FMCG standard catalog, Open Food Facts API, GTIN registries).
- Field status: `package_verified = false`, `verification_status = "REQUIRES_PACKAGE_VERIFICATION"`.
- **Zero False Approvals**: Internet reference information can **never** turn a missing legal declaration from `FAIL` to `PASS`.

---

## 3. Mandatory Statutory Declarations Verified

Under the Legal Metrology (Packaged Commodities) Rules, 2011:

| # | Statutory Declaration | Severity | Statutory Requirement |
|---|---|---|---|
| 1 | **Manufacturer Name & Address** | Critical | Full name and complete physical address of manufacturer, packer, or importer. |
| 2 | **Product / Commodity Name** | Critical | Common or generic name prominently placed on the Principal Display Panel (PDP). |
| 3 | **Net Quantity** | Critical | Standard metric units (g, kg, ml, l) with specified minimum font height. |
| 4 | **Month & Year of Manufacture** | Critical | Month and year of manufacture, pre-packing, or import. |
| 5 | **Maximum Retail Price (MRP)** | Critical | Inclusive of all taxes syntax (`MRP Rs XX.XX incl. of all taxes`). |
| 6 | **Consumer Care Contact Details** | Standard | Grievance officer name, telephone number, email, and physical postal address. |
| 7 | **Country of Origin** | Critical | Declaration of country of manufacture / origin. |
| 8 | **Unit Sale Price (USP)** | Standard | Mandatory calculation per gram/ml/kg printed adjacent to MRP. |

---

## 4. System Architecture & Components

```
User Uploaded Images
  ↓
OpenCV Image Preprocessor (Deskew & CLAHE Contrast)
  ↓
OCR Engine (Cloud OCR.space)
  ↓
Entity Extractor (Regex & NER Parsing)
  ↓
Multi-Panel Evidence Aggregator
  ↓
Deterministic Legal Metrology Rule Engine (Sole Authority)
  ↓
Groq AI Service (openai/gpt-oss-20b - Semantic Assistance & Recommendations)
  ↓
External Product Research Service (GTIN & Open Food Facts Reference Recovery)
  ↓
Supabase Database Persistence & RLS
  ↓
React / Vite UI (Evidence Segregation & Telemetry)
```

---

## 5. Non-Blocking Resilience & Failure Recovery

| Potential Failure Mode | System Response | Outcome |
| :--- | :--- | :--- |
| **Groq AI Timeout / Rate Limit** | Catches exception locally, returns `ai_analysis.status = "unavailable"` | Scan completes (`HTTP 200`), statutory compliance report intact. |
| **Open Food Facts Outage** | Bounded 6.0s timeout, returns `external_research.status = "unavailable"` | Scan completes (`HTTP 200`), statutory score 100% unaffected. |
| **Cloud OCR Quota Exhaustion** | Returns safe structured unavailable result | Handled gracefully without crash. |
| **Client Network Constraints** | Client-side HTML5 Canvas pre-scaling to 1600px | Prevents memory exhaustion and upload timeouts. |

---

## 6. Testing & Quality Assurance

The backend test suite consists of 10 modules and 82 unit/regression tests:
- `tests/test_product_research.py` (12 Tests): Verifies evidence segregation, MRP/date protection, conflict detection.
- `tests/test_groq_ai.py` (7 Tests): Groq fallback, schema parsing, rate-limit resilience.
- `tests/test_api_usage.py` (5 Tests): Admin telemetry RBAC enforcement.
- `tests/test_entity_extractor.py` (20 Tests): Regex and NER token extraction.
- `tests/test_multi_image_evidence.py` (16 Tests): Multi-panel aggregation.
- `tests/test_image_processor.py` (5 Tests): OpenCV deskew and contrast.
- `tests/test_auth.py` (6 Tests): JWT token decoding and role enforcement.
- `test_rule_engine.py` (4 Tests): Statutory compliance calculations.
- `tests/test_role_switching.py` (7 Tests): Role boundary isolation.

**All 82 tests passing with 0 failures.**
