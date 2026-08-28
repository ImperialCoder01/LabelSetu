import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

from routers import users, scans, admin, regulators, ocr, barcodes, certificates, verification, reports, leaderboard, webhook, products, product_verification, executive_reports, notifications
from services.ocr_service import preload_model
from services.rule_engine import load_rules

load_dotenv()

app = FastAPI(
    title="LabelSetu API",
    description="Smart Label Compliance Backend",
    version="1.0.0",
)

# HTTP Response Compression Middleware — compresses responses >= 1000 bytes (reduces JSON payload size by 70-85%)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS — allow frontend origins
cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://labelsetu-ivory.vercel.app",
]

frontend_env = os.getenv("FRONTEND_URL", "")
if frontend_env:
    for url in frontend_env.split(","):
        cleaned = url.strip().rstrip("/")
        if cleaned and cleaned not in cors_origins:
            cors_origins.append(cleaned)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(scans.router, prefix="/api/scans", tags=["Scans"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(regulators.router, prefix="/api/regulators", tags=["Regulators"])
app.include_router(ocr.router, prefix="/api", tags=["OCR"])
app.include_router(barcodes.router, prefix="/api/barcodes", tags=["Barcodes"])
app.include_router(certificates.router, prefix="/api/scans", tags=["Certificates"])
app.include_router(verification.router, prefix="/api/verify", tags=["Verification"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["Leaderboard"])
app.include_router(webhook.router, prefix="/api/webhook", tags=["Webhook"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(product_verification.router, prefix="/api/verification", tags=["Product Verification"])
app.include_router(executive_reports.router, prefix="/api/executive-reports", tags=["Executive Reports"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])


@app.on_event("startup")
def startup_event():
    """Application startup initialization."""
    preload_model()


@app.get("/")
async def root():
    return {"message": "LabelSetu API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Public health-check endpoint — no auth required.
    Used by Render's health check and UptimeRobot to prevent spin-down."""
    return {"status": "ok"}


@app.get("/api/meta/rules")
async def get_public_rules_metadata(response: Response):
    """
    Public deterministic Legal Metrology rules metadata endpoint.
    Safe for public CDN/browser caching (Cache-Control: public, max-age=3600).
    """
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    rules = load_rules()
    return {
        "rules_version": "2026.1",
        "standard": "Legal Metrology (Packaged Commodities) Rules, 2011",
        "mandatory_fields_count": len(rules.get("fields", [])),
        "fields": [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "severity": f.get("severity"),
                "description": f.get("description"),
            }
            for f in rules.get("fields", [])
        ],
    }
