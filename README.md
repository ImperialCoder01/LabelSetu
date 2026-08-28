# 🏷️ LabelSetu — AI-Powered Legal Metrology & Packaging Compliance Platform

[![Live Production Frontend](https://img.shields.io/badge/Frontend-Vercel%20Live-brightgreen?style=for-the-badge&logo=vercel)](https://labelsetu-ivory.vercel.app)
[![Live Production Backend](https://img.shields.io/badge/Backend-Render%20FastAPI-blue?style=for-the-badge&logo=render)](https://labelsetu.onrender.com)
[![Test Suite](https://img.shields.io/badge/Tests-82%2F82%20Passing-success?style=for-the-badge&logo=python)](https://github.com/ImperialCoder01/LabelSetu)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)

**LabelSetu** is an industry-grade, full-stack AI platform developed for **Smart India Hackathon (SIH 2026)** to automate packaging compliance auditing under the **Legal Metrology (Packaged Commodities) Rules, 2011** and Indian regulatory standards.

The platform bridges consumers, packaged food brands, and regulatory enforcement officers through multi-image packaging audits, OCR extraction, deterministic statutory compliance scoring, Groq LLM semantic assistance, and safe external product catalog cross-referencing.

---

## 🌟 Core System Highlights

1. **Deterministic Statutory Scoring Authority**: 100% mathematical, rule-based legal compliance score (0–100) evaluated exclusively against physical package evidence.
2. **Strict Evidence Segregation**:
   - **Layer 1 (Package Evidence)**: Facts physically visible in user-uploaded packaging images (`package_verified = true`).
   - **Layer 2 (External Reference Evidence)**: Supplementary product information retrieved from public GTIN registries and Open Food Facts (`package_verified = false`, `REQUIRES_PACKAGE_VERIFICATION`).
   - **Zero False Approvals**: External internet data can *never* convert a missing or failed legal declaration into a pass.
3. **Groq AI Supplementary Intelligence**: Non-blocking semantic normalization, plain-English label explanations, and actionable brand compliance recommendations powered by `openai/gpt-oss-20b`.
4. **Intelligent Panel Recovery**: Advises users on the exact physical panel/flaps to photograph when declarations are missing (e.g., Back Panel, Date-Code Flap, Manufacturer Address Box).
5. **Role-Based Isolation (4 Roles)**: Strict RBAC boundaries across **Consumer**, **Brand**, **Regulator**, and **Admin** personas.

---

## 🏗️ Architecture & Processing Pipeline

```
                         USER UPLOADED IMAGES
                                  ↓
                        OpenCV Preprocessing
                    (Auto-Deskew, Contrast Enhance)
                                  ↓
                            OCR SERVICE
                      (OCR.space Cloud API)
                                  ↓
                      PACKAGE ENTITY EXTRACTION
                     (Custom Regex & NER Parsing)
                                  ↓
                          PACKAGE EVIDENCE
                                  ↓
       ════════════════════════════════════════════════════════
       DETERMINISTIC LEGAL METROLOGY RULE ENGINE (SOLE AUTHORITY)
       - Evaluates 8 statutory declarations against rules.json
       - Calculates 100% authoritative score (0–100) & Pass/Fail status
       ════════════════════════════════════════════════════════
                                  ↓
       ┌──────────────────────────┴──────────────────────────┐
       ↓                                                     ↓
  Groq AI Service                           Product Research Service
  (openai/gpt-oss-20b)                      (GTIN / Open Food Facts / FMCG Catalog)
  - Normalized summary                      - External reference retrieval
  - Semantic observations                   - package_verified = False
  - Actionable brand recommendations        - REQUIRES_PACKAGE_VERIFICATION
                                            - Identity conflict warning alerts
                                            - Missing panel photo recommendations
       └──────────────────────────┬──────────────────────────┘
                                  ↓
                    COMBINED STRUCTURED SCAN JSON
                                  ↓
       REACT / VITE UI (Visual Evidence Segregation & Reporting)
```

---

## 👥 Role-Based Portals & Capabilities

| Role | Target Persona | Key Capabilities | Accessible Routes |
| :--- | :--- | :--- | :--- |
| **Consumer** | Shoppers, Everyday Buyers | Multi-image packaging scan, instant statutory audit, AI explanation, grievance reporting | `/consumer/dashboard`, `/consumer/scan`, `/consumer/history` |
| **Brand** | FMCG Manufacturers, Quality Officers | Pre-market packaging validation, compliance breakdown, batch audit logs | `/brand/dashboard`, `/brand/validate`, `/brand/history` |
| **Regulator** | Legal Metrology & FSSAI Officers | Real-time market surveillance, non-compliance review queue, grievance resolution | `/regulator/dashboard`, `/regulator/scans`, `/regulator/reports` |
| **Admin** | System Administrators | Telemetry monitoring, OCR/Groq quota tracking, system audit logs, user management | `/admin/dashboard`, `/admin/users`, `/admin/audit-logs`, `/admin/api-usage` |

---

## 📋 8 Mandatory Legal Metrology Declarations Verified

Under the Legal Metrology (Packaged Commodities) Rules, 2011, the deterministic engine validates:

1. **Name & Address of Manufacturer / Packer / Importer** (Critical)
2. **Common or Generic Name of the Commodity** (Critical)
3. **Net Quantity** (Standard unit & weight/volume syntax) (Critical)
4. **Month & Year of Manufacture / Pre-packing / Import** (Critical)
5. **Maximum Retail Price (MRP)** (Inclusive of all taxes) (Critical)
6. **Consumer Care / Grievance Helpline Details** (Phone, Email, Postal Address) (Standard)
7. **Country of Origin** (Mandatory for all imported/domestic goods) (Critical)
8. **Unit Sale Price (USP)** (Mandatory per gram/ml/kg calculation) (Standard)

---

## 💻 Tech Stack

- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React, React Router 6 (SPA Rewrite support on Vercel).
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2.
- **Computer Vision & OCR**: OpenCV (`cv2`), OCR.space Cloud API, PIL/Pillow.
- **AI & LLM Inference**: Groq Cloud API (`openai/gpt-oss-20b`).
- **Database & Authentication**: Supabase (PostgreSQL, Row Level Security, Auth with ES256/HS256 JWT tokens).
- **External Catalog Integrations**: Open Food Facts API, National FMCG Standard Barcode Registry.
- **Deployment**: Vercel (Frontend), Render (Backend).

---

## 📁 Repository Structure

```text
LabelSetu/
├── backend/                     # FastAPI Application
│   ├── main.py                  # Server entrypoint & middleware configuration
│   ├── config.py                # Environment settings & credentials
│   ├── database.py              # Supabase database client
│   ├── models/
│   │   ├── barcode_catalog.json # National FMCG catalog dataset (~1,000+ items)
│   │   └── rules.json           # Statutory Legal Metrology rule configurations
│   ├── routers/
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── scans.py             # Packaging audit & scan pipeline
│   │   ├── ocr.py               # OCR & API usage telemetry
│   │   ├── users.py             # User profile endpoints
│   │   ├── reports.py           # Regulatory grievance reporting
│   │   └── admin.py             # Audit logs & administrative metrics
│   ├── services/
│   │   ├── ai_service.py        # Groq LLM integration (openai/gpt-oss-20b)
│   │   ├── product_research_service.py # External catalog recovery & evidence isolation
│   │   ├── rule_engine.py       # Deterministic Legal Metrology compliance engine
│   │   ├── entity_extractor.py  # Regex & NER token extraction
│   │   ├── ocr_service.py       # Multi-tier OCR processing
│   │   ├── barcode_service.py   # GTIN / Barcode lookups
│   │   └── image_processor.py   # OpenCV deskew & contrast enhancement
│   └── tests/                   # 10 test suites (82/82 passing tests)
│
├── frontend/                    # React + Vite Application
│   ├── src/
│   │   ├── components/          # Reusable UI (Sidebars, Drawers, ProtectedRoute)
│   │   ├── pages/
│   │   │   ├── consumer/        # Consumer Scan & Dashboard views
│   │   │   ├── brand/           # Brand Quality & Audit views
│   │   │   ├── regulator/       # Regulatory Review & Grievance views
│   │   │   └── admin/           # Admin Telemetry & Audit Log views
│   │   ├── context/             # AuthContext with Supabase Auth
│   │   └── App.jsx              # Role-based route definitions
│   └── vercel.json              # SPA rewrite rules for direct URL routing
│
├── docs/                        # Specifications & Architecture Documentation
│   ├── PRD.md                   # Complete Product Requirements Document
│   └── ARCHITECTURE.md          # Evidence segregation & system architecture
└── README.md                    # Project manual & developer guide
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Node.js 18+
- Python 3.10+
- Supabase Project & Credentials
- Groq API Key (Optional for local testing; backend handles graceful fallback)

### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GROQ_API_KEY

# Run server
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE=http://localhost:8000

# Start development server
npm run dev
```

---

## 🧪 Comprehensive Test Suite (82/82 Passing)

Run all backend unit and regression test modules:

```bash
cd backend

# Run individual test modules
python tests/test_product_research.py     # 12/12 Tests (Evidence isolation & regressions)
python tests/test_groq_ai.py              # 7/7 Tests (Groq resilience & JSON parsing)
python tests/test_api_usage.py            # 5/5 Tests (Admin telemetry RBAC)
python tests/test_entity_extractor.py     # 20/20 Tests (Regex / NER token parsing)
python tests/test_multi_image_evidence.py # 16/16 Tests (Multi-panel aggregation)
python tests/test_image_processor.py      # 5/5 Tests (OpenCV deskew & enhancement)
python tests/test_auth.py                 # 6/6 Tests (JWT decoding & RBAC)
python test_rule_engine.py                # 4/4 Tests (Deterministic statutory rules)
python tests/test_role_switching.py       # 7/7 Tests (Role boundary isolation)

# Build frontend verification
cd ../frontend && npm run build
```

---

## 🔒 Security & Privacy Architecture

- **Backend-Only Secrets**: `GROQ_API_KEY`, Supabase Service Role Key, and external API keys are loaded strictly backend-side and never exposed in frontend code or client bundles.
- **Role-Based Authorization**: Protected endpoints enforce strict user roles at the FastAPI middleware layer via `require_role(...)`.
- **Row-Level Security (RLS)**: PostgreSQL tables enforce database-level access controls.
- **Client-Side Optimization**: Mobile canvas pre-scaling prevents memory exhaustion on constrained network environments.

---

## 📄 License

This project is licensed under the **MIT License**.
Developed with pride for the **Smart India Hackathon (SIH 2026)**.
