# 📋 Product Requirements Document (PRD)
## LabelSetu — Smart Label Compliance Platform

---

**Version:** 1.0  
**Date:** August 25, 2026  
**Author:** LabelSetu Team  
**Status:** Draft  

---

## 1. Executive Summary

LabelSetu is an AI-powered web platform that automates product label compliance verification. Users upload product label images, the system extracts text via OCR (EasyOCR), cross-references extracted data against Indian FSSAI and Legal Metrology compliance rules, and generates a compliance score with a detailed breakdown of missing fields.

The platform serves four distinct user roles — **Consumer**, **Brand**, **Regulator**, and **Admin** — each with tailored dashboards and permissions, enabling a full compliance lifecycle from label scanning to regulatory oversight.

---

## 2. Problem Statement

### The Problem
- **1.4 billion+ consumers** in India rely on product labels for safety, nutritional, and pricing information.
- **Manual label compliance** checks are slow, inconsistent, and don't scale.
- **Brands** struggle to ensure every product meets FSSAI and Legal Metrology requirements before market launch.
- **Regulators** lack real-time visibility into non-compliant products across the market.
- **Consumers** have no easy way to verify if a product label is compliant or misleading.

### The Solution
LabelSetu uses **AI-powered OCR** and **rule-based compliance checking** to instantly scan, extract, and evaluate product labels — providing actionable compliance insights in seconds.

---

## 3. Goals & Objectives

| Goal | Metric | Target |
|------|--------|--------|
| Enable instant label scanning | Scan-to-result time | < 10 seconds |
| Improve compliance detection | Accuracy of missing field detection | > 90% |
| Scale regulatory oversight | Scans processable per day | 10,000+ |
| Reduce manual review workload | Time saved per compliance check | 80% reduction |
| Consumer empowerment | % of scans returning actionable results | > 95% |

---

## 4. User Roles & Personas

### 4.1 Consumer
> *"I want to quickly check if a product label is compliant before I buy it."*

| Attribute | Detail |
|-----------|--------|
| **Role** | End-user, shopper |
| **Access** | Upload scans, view own scan history |
| **Key Actions** | Scan label, view compliance score, check missing fields |
| **Pain Point** | No easy way to verify label compliance |

### 4.2 Brand
> *"I need to ensure all my product labels are compliant before hitting the market."*

| Attribute | Detail |
|-----------|--------|
| **Role** | Product manager, compliance officer at a brand |
| **Access** | Upload scans, view compliance scores, track issues |
| **Key Actions** | Scan labels, view compliance breakdown, track missing fields |
| **Pain Point** | Manual compliance review is slow and error-prone |

### 4.3 Regulator
> *"I need real-time visibility into which products are non-compliant across the market."*

| Attribute | Detail |
|-----------|--------|
| **Role** | FSSAI / Legal Metrology official |
| **Access** | View all scans, compliance reports, flagged items |
| **Key Actions** | Monitor all scans, filter by risk, view compliance reports |
| **Pain Point** | No centralized dashboard for compliance monitoring |

### 4.4 Admin
> *"I need full system control, user management, and audit trail visibility."*

| Attribute | Detail |
|-----------|--------|
| **Role** | Platform administrator |
| **Access** | Full CRUD, audit logs, API usage, user management |
| **Key Actions** | Manage users, view audit logs, monitor API usage |
| **Pain Point** | No visibility into system health and user actions |

---

## 5. Feature Requirements

### 5.1 Authentication & Authorization

| Feature | Priority | Status |
|---------|----------|--------|
| Email/password signup | P0 | ✅ Built |
| Email/password login | P0 | ✅ Built |
| Role-based access control (4 roles) | P0 | ✅ Built |
| Session management via Supabase | P0 | ✅ Built |
| Protected routes (frontend) | P0 | ✅ Built |
| JWT verification (backend) | P0 | ✅ Built |
| Row Level Security (Supabase RLS) | P0 | ✅ Built |

### 5.2 Consumer Features

| Feature | Priority | Status |
|---------|----------|--------|
| Upload product label image | P0 | ✅ Built |
| OCR text extraction (EasyOCR) | P0 | ✅ Built |
| Compliance score calculation | P0 | ✅ Built |
| Missing fields identification | P0 | ✅ Built |
| Scan history view | P0 | ✅ Built |
| Image preview before upload | P1 | 🔲 Planned |
| Drag-and-drop upload | P1 | 🔲 Planned |
| Scan comparison (before/after) | P2 | 🔲 Planned |

### 5.3 Brand Features

| Feature | Priority | Status |
|---------|----------|--------|
| View own compliance scores | P0 | ✅ Built |
| Compliance statistics (avg, total, issues) | P0 | ✅ Built |
| Detailed scan results table | P0 | ✅ Built |
| Missing fields breakdown per scan | P0 | ✅ Built |
| Bulk scan upload | P2 | 🔲 Planned |
| Compliance trend over time | P2 | 🔲 Planned |
| Export compliance report (PDF) | P2 | 🔲 Planned |

### 5.4 Regulator Features

| Feature | Priority | Status |
|---------|----------|--------|
| View all scans across users | P0 | ✅ Built |
| Filter scans by compliance score | P0 | ✅ Built |
| Flagged scans (low compliance) | P0 | ✅ Built |
| Compliance report summary | P0 | ✅ Built |
| Search scans by user/brand | P1 | 🔲 Planned |
| Geographic compliance heatmap | P2 | 🔲 Planned |
| Automated flagging notifications | P2 | 🔲 Planned |

### 5.5 Admin Features

| Feature | Priority | Status |
|---------|----------|--------|
| View all users | P0 | ✅ Built |
| Audit log viewer | P0 | ✅ Built |
| API usage statistics | P0 | ✅ Built |
| System stats (total users, scans) | P0 | ✅ Built |
| User role management (promote/demote) | P1 | 🔲 Planned |
| Manual audit log entry | P1 | 🔲 Planned |
| System health dashboard | P2 | 🔲 Planned |

---

## 6. Compliance Rules Engine

### 6.1 Required Label Fields (FSSAI + Legal Metrology)

| # | Field | FSSAI Required | Legal Metrology Required | Detection Keywords |
|---|-------|---------------|-------------------------|-------------------|
| 1 | Product Name | ✅ | ✅ | product name, brand, label |
| 2 | Manufacturer | ✅ | ✅ | manufactured by, made by, produced by |
| 3 | Ingredients | ✅ | — | ingredients, contains, composition |
| 4 | Net Quantity | — | ✅ | net quantity, net wt, weight, volume |
| 5 | Nutritional Info | ✅ | — | nutrition, calories, protein, fat |
| 6 | Expiry Date | ✅ | ✅ | expiry, best before, use by |
| 7 | Batch Number | — | ✅ | batch, lot, batch no |
| 8 | MRP | — | ✅ | mrp, price, rs, ₹ |
| 9 | Country of Origin | ✅ | ✅ | origin, made in, country |

### 6.2 Compliance Score Calculation

```
score = (found_fields / total_required_fields) × 100
```

| Score Range | Status | Color | Action |
|-------------|--------|-------|--------|
| 80–100% | Compliant | 🟢 Green | No action needed |
| 50–79% | Partially Compliant | 🟡 Yellow | Review recommended |
| 0–49% | Non-Compliant | 🔴 Red | Immediate action required |

### 6.3 Extensibility

Rules are stored in `docs/rules.json` — new fields, keywords, and regulatory standards can be added without code changes.

---

## 7. Technical Architecture

### 7.1 System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│         React + Vite + Tailwind CSS                  │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Consumer │ │  Brand   │ │Regulator │ │ Admin  │  │
│  │Dashboard │ │Dashboard │ │Dashboard │ │Dashboard│ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘  │
│                      │                               │
│              Supabase JS Client                      │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
    ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
    │ Supabase  │ │FastAPI│ │ Supabase  │
    │   Auth    │ │Backend│ │ Database  │
    │ (JWT)     │ │       │ │ (RLS)     │
    └───────────┘ └───┬───┘ └───────────┘
                      │
              ┌───────┼───────┐
              │       │       │
        ┌─────▼──┐ ┌──▼───┐ ┌▼────────┐
        │EasyOCR │ │Rules │ │ Audit   │
        │Service │ │Engine│ │ Logger  │
        └────────┘ └──────┘ └─────────┘
```

### 7.2 Data Flow

```
1. User uploads image
       ↓
2. Frontend sends to FastAPI /api/scans/upload
       ↓
3. FastAPI verifies JWT (Supabase Auth)
       ↓
4. EasyOCR extracts text from image
       ↓
5. Compliance engine checks against rules.json
       ↓
6. Result stored in Supabase DB (scans table)
       ↓
7. Response returned to frontend
       ↓
8. Dashboard displays compliance score + missing fields
```

### 7.3 Database Schema

#### users_profile
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, FK → auth.users |
| full_name | TEXT | NOT NULL |
| role | user_role | ENUM, default 'consumer' |
| created_at | TIMESTAMPTZ | default now() |
| updated_at | TIMESTAMPTZ | default now() |

#### scans
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, default gen_random_uuid() |
| user_id | UUID | FK → users_profile |
| image_url | TEXT | default '' |
| extracted_text | TEXT | default '' |
| compliance_score | INTEGER | CHECK 0–100 |
| missing_fields | JSONB | default '[]' |
| created_at | TIMESTAMPTZ | default now() |

#### audit_log
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| admin_id | UUID | FK → users_profile |
| action_type | TEXT | NOT NULL |
| target_table | TEXT | NOT NULL |
| target_id | UUID | nullable |
| old_value | JSONB | nullable |
| new_value | JSONB | nullable |
| timestamp | TIMESTAMPTZ | default now() |

#### api_usage_log
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| provider | TEXT | NOT NULL |
| request_count | INTEGER | default 0 |
| month | TEXT | UNIQUE(provider, month) |

### 7.4 API Endpoints

| Method | Endpoint | Auth Required | Roles | Description |
|--------|----------|--------------|-------|-------------|
| POST | `/api/scans/upload` | ✅ | Consumer, Brand | Upload & scan label |
| GET | `/api/scans/` | ✅ | Any | List user's scans |
| GET | `/api/scans/{id}` | ✅ | Any (own) / Admin, Regulator (all) | Get scan details |
| GET | `/api/users/me` | ✅ | Any | Get own profile |
| PUT | `/api/users/me` | ✅ | Any | Update own profile |
| GET | `/api/users/` | ✅ | Admin | List all users |
| GET | `/api/admin/audit-logs` | ✅ | Admin | View audit logs |
| GET | `/api/admin/api-usage` | ✅ | Admin | View API usage |
| GET | `/api/admin/stats` | ✅ | Admin | System statistics |
| GET | `/api/regulators/all-scans` | ✅ | Regulator, Admin | View all scans |
| GET | `/api/regulators/flagged` | ✅ | Regulator, Admin | View flagged scans |
| GET | `/api/regulators/compliance-report` | ✅ | Regulator, Admin | Compliance summary |

---

## 8. Security Requirements

| Requirement | Implementation |
|-------------|---------------|
| No hardcoded secrets | All API keys in `.env` files |
| `.env` in `.gitignore` | ✅ Configured |
| JWT verification on backend | ✅ python-jose with HS256 |
| Row Level Security (RLS) | ✅ Enabled on all 4 tables |
| Role-based access control | ✅ FastAPI dependency injection |
| CORS restricted to frontend | ✅ localhost:5173, localhost:3000 |
| Password minimum length | 6 characters (Supabase default) |
| Service role key (backend only) | ✅ Never exposed to frontend |

---

## 9. Non-Functional Requirements

| Category | Requirement |
|----------|------------|
| **Performance** | Scan-to-result latency < 10 seconds |
| **Scalability** | Support 10,000+ scans per day |
| **Availability** | 99.5% uptime target |
| **Browser Support** | Chrome, Firefox, Safari, Edge (latest 2 versions) |
| **Responsive Design** | Mobile-friendly Tailwind CSS layout |
| **Accessibility** | WCAG 2.1 AA basics (semantic HTML, labels, contrast) |

---

## 10. Environment Variables

### Frontend (.env)
| Variable | Description |
|----------|------------|
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous/public key |

### Backend (.env)
| Variable | Description |
|----------|------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role secret |
| `SUPABASE_JWT_SECRET` | JWT verification secret |
| `BACKEND_URL` | Backend server URL |
| `DEBUG` | Debug mode flag |

---

## 11. Dependencies

### Frontend
| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.3.x | UI framework |
| react-dom | 18.3.x | DOM rendering |
| react-router-dom | 6.26.x | Client-side routing |
| @supabase/supabase-js | 2.45.x | Supabase client |
| vite | 5.4.x | Build tool |
| tailwindcss | 3.4.x | CSS framework |

### Backend
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115.x | Web framework |
| uvicorn | 0.30.x | ASGI server |
| supabase | 2.9.x | Supabase Python client |
| easyocr | 1.7.x | OCR engine |
| python-jose | 3.3.x | JWT decoding |
| python-dotenv | 1.0.x | Env file loading |
| Pillow | 10.4.x | Image processing |
| pydantic-settings | 2.5.x | Settings management |

---

## 12. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| EasyOCR slow on large images | Medium | Medium | Image resize preprocessing |
| OCR accuracy on Hindi/regional text | High | Medium | Add Hindi language support to EasyOCR |
| Supabase free tier limits | Low | High | Monitor usage, plan upgrade path |
| JWT secret compromise | Low | Critical | Rotate keys, use Supabase managed secrets |
| Large image upload failures | Medium | Low | Client-side compression, file size limits |
| Rules engine false positives | Medium | Medium | Tunable keyword matching, manual override |

---

## 13. Success Metrics

| Metric | Baseline | Target (3 months) |
|--------|----------|-------------------|
| Total scans processed | 0 | 5,000+ |
| Active users | 0 | 500+ |
| Average compliance score | N/A | Track baseline |
| OCR accuracy (English labels) | N/A | > 85% |
| False positive rate | N/A | < 10% |
| Average scan processing time | N/A | < 8 seconds |

---

## 14. Future Roadmap

### Phase 2 (v1.1)
- [ ] Supabase Storage integration for label images
- [ ] Image preview before upload
- [ ] Drag-and-drop upload
- [ ] Mobile responsive optimization

### Phase 3 (v1.2)
- [ ] Hindi / regional language OCR support
- [ ] Bulk scan upload for brands
- [ ] PDF compliance report export
- [ ] Email notifications for flagged scans

### Phase 4 (v2.0)
- [ ] AI-powered compliance suggestions (LLM integration)
- [ ] Geographic compliance heatmap
- [ ] API for third-party integrations
- [ ] Multi-language UI (Hindi, Tamil, Bengali)
- [ ] Mobile app (React Native)

---

## 15. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | Should we support image upload to Supabase Storage now or defer? | Product | Decided: Defer to Phase 2 |
| 2 | What's the target scan processing SLA? | Engineering | Decided: < 10 seconds |
| 3 | Do we need admin ability to manually edit audit logs? | Product | Open |
| 4 | Should brands see other brands' scans? | Product | Decided: No |
| 5 | What regulatory standards beyond FSSAI? | Domain | Open |

---

*This PRD is a living document. Updated as features are built and requirements evolve.*
