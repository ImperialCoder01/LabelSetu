# PowerShell startup script for LabelSetu Local PaddleOCR Service
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting LabelSetu Local PaddleOCR Service" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Virtualenv not found at $venvPython."
    exit 1
}

$env:PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT = "False"
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "True"

Write-Host "Launching Uvicorn on http://127.0.0.1:8001..." -ForegroundColor Green
& $venvPython -m uvicorn server:app --host 127.0.0.1 --port 8001
