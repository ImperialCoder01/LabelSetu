# LabelSetu Local PaddleOCR Service (Stage 1)

A high-accuracy, standalone, local OCR microservice powered by **PaddleOCR** and **PaddlePaddle 3.3.1**, specialized for Indian consumer packaged goods (CPG) labels with native support for English, Hindi (Devanagari script), and mixed bilingual packaging declarations.

---

## 1. Architectural Role & Isolation

```
┌────────────────────────────────────────────────────────┐
│                   LABELSETU PLATFORM                   │
│                                                        │
│   Vercel Frontend             Render Free Backend      │
│   (Next/React Web UI)         (FastAPI, 512MB RAM cap) │
│            │                             │             │
│            ▼                             ▼             │
│   ┌──────────────────────────────────────────────┐     │
│   │           Future OCR Orchestrator            │     │
│   │               (Phase / Stage 2)              │     │
│   └──────────────┬──────────────────────┬────────┘     │
│                  │                      │              │
│                  ▼                      ▼              │
│       ┌─────────────────────┐  ┌───────────────────┐   │
│       │  OCR.space (Cloud)  │  │ Local PaddleOCR   │   │
│       │  (Always available) │  │ (Optional Engine) │   │
│       └─────────────────────┘  └────────┬──────────┘   │
└─────────────────────────────────────────┼──────────────┘
                                          │
                         [STANDALONE ISOLATED MICROSERVICE]
                         Runs on local Windows machine only
                         Port 8001 | Bound to 127.0.0.1
                         Does NOT run on Render Free
```

### Why Standalone Local Service?
1. **Render Free RAM Limits**: Render Free web services have a strict 512MB RAM ceiling. PaddlePaddle + OCR models require ~1.2GB resident RAM, which would cause an immediate OOM crash on Render.
2. **Superior Indic Script Accuracy**: Traditional cloud OCRs often struggle with conjuncts and Devanagari ligatures. PaddleOCR's `devanagari_PP-OCRv5_mobile_rec` model achieves >94% confidence on complex Hindi packaging text (e.g. *शुद्ध मात्रा*, *निर्माता*, *अधिकतम खुदरा मूल्य*).
3. **Zero Impact on Production**: LabelSetu's existing backend (`backend/`), rule engine, database schema, frontend, Vercel, and Render deployments remain completely untouched.

---

## 2. Directory Structure

```
local_ocr_server/
├── server.py              # FastAPI application (endpoints: /health, /ready, /ocr)
├── ocr_engine.py          # Thread-safe PaddleOCR singleton wrapper & line sorter
├── preprocessing.py       # Safe image decoding, EXIF handling, BGR conversion
├── test_client.py         # Automated CLI validation & benchmark client
├── requirements.txt       # Exact pinned dependencies for Python 3.12
├── .env.example           # Environment configuration template
├── .gitignore             # Git ignore for venv, cache, outputs
├── start_server.bat       # Windows CMD server launcher
├── start_server.ps1       # Windows PowerShell server launcher
├── test_images/           # Synthetic bilingual packaging test images
│   ├── test_en.png
│   ├── test_hi.png
│   └── test_mixed.png
└── test_outputs/          # JSON responses captured during validation
```

---

## 3. Setup & Installation

### Prerequisites
- Windows 10/11 64-bit
- **Python 3.12 (64-bit)** installed at `C:\Users\<user>\AppData\Local\Programs\Python\Python312` (or in PATH)
  *(Note: Python 3.14 is currently unsupported by compiled PaddlePaddle C++ wheels).*

### Virtual Environment Setup
```powershell
# From repository root:
cd local_ocr_server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 4. Running the Service

### Option A: Using Batch Script (CMD)
```cmd
start_server.bat
```

### Option B: Using PowerShell
```powershell
.\start_server.ps1
```

### Option C: Manual Launch
```powershell
.\.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8001
```

The service will bind to `http://127.0.0.1:8001`. (Port 8000 remains free for the main LabelSetu backend).

---

## 5. API Reference

### 1. `GET /health`
Returns runtime status, engine readiness, device, and versions.

**Example Response**:
```json
{
  "status": "ok",
  "service": "paddleocr_local",
  "engine_ready": true,
  "device": "cpu",
  "uptime_seconds": 15.4,
  "versions": {
    "paddleocr": "3.7.0",
    "paddlepaddle": "3.3.1"
  },
  "auth_enabled": false
}
```

### 2. `GET /ready`
Readiness probe returning HTTP 200 when OCR weights are initialized and warm.

### 3. `POST /ocr`
Processes an uploaded packaging label image and returns normalized extracted text lines.

- **Headers**:
  - `Content-Type`: `multipart/form-data`
  - `X-Local-OCR-Key`: *(Optional)* Required only if `LOCAL_OCR_API_KEY` is configured in environment.
- **Form Data**:
  - `file`: Image file (`.png`, `.jpg`, `.jpeg`, `.webp`, max 15MB)
  - `lang`: *(Optional)* Language override (default: `hi`)

**Example Response**:
```json
{
  "provider": "paddleocr_local",
  "success": true,
  "processing_time_ms": 1420,
  "raw_text": "पतंजलि च्यवनप्राश (Patanjali Special Chyawanprash)\nशुद्ध मात्रा / Net Quantity: 500g\nअधिकतम खुदरा मूल्य / MRP: ₹245.00\nबैच संख्या / Batch No: PAT2024B1",
  "lines": [
    {
      "text": "पतंजलि च्यवनप्राश (Patanjali Special Chyawanprash)",
      "confidence": 0.9482,
      "bounding_box": {
        "x_min": 35,
        "y_min": 36,
        "x_max": 540,
        "y_max": 76
      }
    },
    {
      "text": "शुद्ध मात्रा / Net Quantity: 500g",
      "confidence": 0.9470,
      "bounding_box": {
        "x_min": 39,
        "y_min": 85,
        "x_max": 303,
        "y_max": 113
      }
    }
  ],
  "languages_detected": ["en", "hi"],
  "metadata": {
    "engine_version": "3.7.0",
    "model_name": "devanagari_PP-OCRv5_mobile_rec+PP-OCRv5_server_det",
    "device": "cpu",
    "image_dimensions": {
      "width": 700,
      "height": 420
    },
    "total_lines": 5,
    "scale_factor_applied": 1.0
  }
}
```

---

## 6. Running Validation Suite

To run the automated test client against the live server:
```powershell
.\.venv\Scripts\python.exe test_client.py
```
This tests `/health`, `/ready`, English packaging, Hindi packaging, mixed packaging, latency benchmarks (cold vs warm), and failure rejection (empty file, corrupt file, invalid key).
