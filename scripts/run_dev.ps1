# Run Backend and Frontend Applications Locally in PowerShell
param (
    [string]$Target = "all" # backend | user | admin | all
)

$RootDir = "$PSScriptRoot\.."

switch ($Target) {
    "backend" {
        Write-Host "[1/3] Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
        Set-Location -Path "$RootDir\backend"
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    }
    "user" {
        Write-Host "[2/3] Starting User Frontend on http://localhost:3000..." -ForegroundColor Green
        Set-Location -Path "$RootDir\apps\user-frontend"
        npm run dev
    }
    "admin" {
        Write-Host "[3/3] Starting Admin Frontend on http://localhost:3001..." -ForegroundColor Green
        Set-Location -Path "$RootDir\apps\admin-frontend"
        npm run dev
    }
    default {
        Write-Host "==========================================================" -ForegroundColor Cyan
        Write-Host " AI FAQ COLLEGE CHAT BOT - UNIFIED RUNNER" -ForegroundColor Cyan
        Write-Host "==========================================================" -ForegroundColor Cyan
        Set-Location -Path $RootDir
        node scripts/start-dev.js --open
    }
}
