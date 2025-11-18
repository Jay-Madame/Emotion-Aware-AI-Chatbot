param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5500
)

# Always run relative to this script's folder (repo root)
$root = $PSScriptRoot

# Path to the venv's Python (no need to "activate" in this script)
$venvPython = Join-Path $root "backend_venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "❌ backend_venv not found or incomplete." -ForegroundColor Red
    Write-Host "Create it and install deps with:" -ForegroundColor Yellow
    Write-Host "  cd $root"
    Write-Host "  python -m venv backend_venv"
    Write-Host "  .\backend_venv\Scripts\Activate.ps1"
    Write-Host "  python -m pip install -r .\docs\backend_requirements.txt"
    exit 1
}

Write-Host " Using venv Python at: $venvPython" -ForegroundColor Green

# --- Start backend (FastAPI + uvicorn) ---
Write-Host " Starting backend on port $BackendPort ..." -ForegroundColor Cyan
$backend = Start-Process `
    -FilePath $venvPython `
    -ArgumentList "-m uvicorn src.server:app --host 0.0.0.0 --port $BackendPort --reload" `
    -WorkingDirectory $root `
    -PassThru

# --- Start frontend static server (chat_ui) ---
$chatUiDir = Join-Path $root "chat_ui"
if (-not (Test-Path $chatUiDir)) {
    Write-Host " chat_ui folder not found at $chatUiDir" -ForegroundColor Red
    Write-Host "Make sure your frontend is in a folder named 'chat_ui' in the repo root."
    exit 1
}

Write-Host " Starting frontend server on port $FrontendPort ..." -ForegroundColor Cyan
$frontend = Start-Process `
    -FilePath $venvPython `
    -ArgumentList "-m http.server $FrontendPort" `
    -WorkingDirectory $chatUiDir `
    -PassThru

# --- Open browser to the frontend ---
Start-Sleep -Seconds 2
$frontendUrl = "http://localhost:$FrontendPort/index.html"
Write-Host " Opening browser at $frontendUrl" -ForegroundColor Green
Start-Process $frontendUrl

Write-Host ""
Write-Host "Backend PID : $($backend.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
Write-Host "To stop them, you can either close the spawned windows or run:" -ForegroundColor Yellow
Write-Host "  Stop-Process -Id $($backend.Id), $($frontend.Id)"
