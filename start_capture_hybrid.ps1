# One-command Windows capture mode:
# - Runs backend on host Windows (real screen capture via mss)
# - Runs frontend in Docker on http://localhost:3001
# - Frontend proxies /api/* to host backend through host.docker.internal

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  throw "Python venv not found at $python. Create it first (python -m venv .venv)."
}

Write-Host "[hybrid] Stopping Docker backend to free port 8000..." -ForegroundColor Cyan
try {
  docker compose stop backend | Out-Null
} catch {
  Write-Host "[hybrid] backend stop skipped: $($_.Exception.Message)" -ForegroundColor Yellow
}

$portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $portInUse) {
  Write-Host "[hybrid] Starting host backend on :8000..." -ForegroundColor Cyan
  Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; & '$python' -m uvicorn mock_server:app --host 0.0.0.0 --port 8000" -WindowStyle Normal | Out-Null
  Start-Sleep -Seconds 2
} else {
  Write-Host "[hybrid] Host backend already running on :8000" -ForegroundColor Green
}

Write-Host "[hybrid] Starting Docker frontend on :3001 with host backend proxy..." -ForegroundColor Cyan
$env:INTERNAL_API_URL = "http://host.docker.internal:8000"
$env:NEXT_PUBLIC_WS_URL = "ws://localhost:8000"
docker compose up -d --build --no-deps frontend

Write-Host "" 
Write-Host "[hybrid] Ready" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:3001"
Write-Host "API docs (host backend): http://localhost:8000/docs"
