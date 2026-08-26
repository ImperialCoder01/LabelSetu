# 🏷️ LabelSetu — Smart Label Compliance Platform

A full-stack web application for verifying product label compliance using AI-powered OCR and automated rule checking.

## 🎯 Features

- **Consumer**: Scan product labels, check compliance instantly
- **Brand**: Upload labels, view compliance scores and missing fields
- **Regulator**: Monitor all scans, view compliance reports, flag non-compliant products
- **Admin**: Full system access, audit logs, API usage tracking, user management

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Auth | Supabase Auth (JWT) |
| Database | Supabase PostgreSQL |
| Backend | Python FastAPI |
| OCR | EasyOCR |
| Compliance Engine | JSON rules matching |

## 📁 Project Structure

```
labelsetu/
├── frontend/          # React + Vite + Tailwind CSS
├── backend/           # Python FastAPI
├── docs/              # Compliance rules (rules.json)
├── supabase/          # Database schema (schema.sql)
├── .env.example       # Environment variables template
└── README.md
```

## 🚀 Setup Instructions

### Prerequisites

- Node.js 18+ (from nodejs.org)
- Python 3.10+ (from python.org)
- Git (from git-scm.com)
- Supabase account (supabase.com)

### 1. Clone & Install

```bash
# Clone the repository
git clone <your-repo-url>
cd labelsetu

# Install frontend dependencies
cd frontend
npm install
cd ..

# Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 2. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run the contents of `supabase/schema.sql`
3. Go to **Settings → API** and copy:
   - Project URL
   - `anon` public key
   - `service_role` secret key
   - JWT Secret (from Settings → Auth → JWT Settings)

### 3. Configure Environment Variables

```bash
# Create .env files from examples
cp .env.example .env
cp frontend/.env.example frontend/.env
cp backend/.env.example backend/.env
```

Edit each `.env` file with your Supabase credentials:

**Frontend `.env`** (frontend/.env):
```
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

**Backend `.env`** (backend/.env):
```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

### 4. Run the Application

**Terminal 1 — Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

### 5. Access the App

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 Database Schema

| Table | Description |
|-------|-------------|
| `users_profile` | User metadata (id, role, full_name) |
| `scans` | OCR scan results with compliance scores |
| `audit_log` | Admin action tracking |
| `api_usage_log` | API quota monitoring |

## 🔐 User Roles

| Role | Permissions |
|------|------------|
| **Consumer** | Upload scans, view own history |
| **Brand** | Upload scans, view compliance scores |
| **Regulator** | View all scans, compliance reports |
| **Admin** | Full CRUD, audit logs, user management |

## 🛡️ Security

- All API keys stored in `.env` (never committed to Git)
- `.env` files included in `.gitignore`
- Row Level Security (RLS) enabled on all tables
- JWT verification on all protected endpoints
- Role-based access control (RBAC)

## 📝 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/scans/upload` | Consumer, Brand | Upload & scan label |
| GET | `/api/scans/` | Any | List user's scans |
| GET | `/api/scans/{id}` | Any | Get scan details |
| GET | `/api/users/me` | Any | Get own profile |
| PUT | `/api/users/me` | Any | Update own profile |
| GET | `/api/users/` | Admin | List all users |
| GET | `/api/admin/audit-logs` | Admin | View audit logs |
| GET | `/api/admin/api-usage` | Admin | View API usage |
| GET | `/api/regulators/all-scans` | Regulator, Admin | View all scans |
| GET | `/api/regulators/flagged` | Regulator, Admin | View flagged scans |
| GET | `/api/regulators/compliance-report` | Regulator, Admin | Compliance stats |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.
