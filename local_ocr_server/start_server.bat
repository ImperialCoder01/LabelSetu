@echo off
chcp 65001 > nul
echo ===================================================
echo Starting LabelSetu Local PaddleOCR Service
echo ===================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Error: .venv not found. Please create virtualenv first.
    exit /b 1
)

set PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=False
set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

echo Activating .venv and launching server on http://127.0.0.1:8001...
call .venv\Scripts\activate.bat
python -m uvicorn server:app --host 127.0.0.1 --port 8001
pause
