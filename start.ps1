# Ani-Log dev launcher — starts backend + frontend in split terminals
# Usage: .\start.ps1

$root    = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend= Join-Path $root "frontend"
$python  = "G:/Github_Project/Portfolio/.venv/Scripts/python.exe"

Write-Host "🎌 Starting Ani-Log..." -ForegroundColor Cyan

# --- Backend (port 8000) ---
if (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue) {
    Write-Host "  ✅ Backend already running on :8000" -ForegroundColor Green
} else {
    Write-Host "  🚀 Starting FastAPI backend on :8000..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command",
        "cd '$backend'; & '$python' -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload" `
        -WindowStyle Normal
}

# --- Frontend (port 3001) ---
if (Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue) {
    Write-Host "  ✅ Frontend already running on :3001" -ForegroundColor Green
} else {
    Write-Host "  🚀 Starting Next.js frontend on :3001..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command",
        "cd '$frontend'; npm run dev -- --port 3001" `
        -WindowStyle Normal
    Start-Sleep -Seconds 4
}

Write-Host ""
Write-Host "  Backend  → http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend → http://localhost:3001" -ForegroundColor Cyan
Write-Host ""
