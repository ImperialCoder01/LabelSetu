import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import users, scans, admin, regulators, ocr, barcodes, certificates, verification, reports, leaderboard, webhook
from services.ocr_service import preload_model

load_dotenv()

app = FastAPI(
    title="LabelSetu API",
    description="Smart Label Compliance Backend",
    version="1.0.0",
)

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


@app.on_event("startup")
def startup_event():
    """Preload OCR model at startup when using local provider."""
    preload_model()


@app.get("/")
async def root():
    return {"message": "LabelSetu API is running", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Public health-check endpoint — no auth required.
    Used by Render's health check and UptimeRobot to prevent spin-down."""
    return {"status": "ok"}
