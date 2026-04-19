$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=========================================="
Write-Host "  Cyber ChatOps MVP Installer / Launcher"
Write-Host "=========================================="
Write-Host ""

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker CLI was not found in PATH."
    Write-Host "Install Docker Desktop first, then re-run this file."
    exit 1
}

try {
    docker info *> $null
} catch {
    Write-Host "[ERROR] Docker is installed but not running."
    Write-Host "Start Docker Desktop, wait until it is ready, then re-run this file."
    exit 1
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env" -Force
        Write-Host "[OK] Created .env from .env.example"
    } else {
        Write-Host "[WARN] .env.example was not found, continuing without a local .env file."
    }
} else {
    Write-Host "[OK] Existing .env found"
}

Write-Host ""
Write-Host "[STEP] Building and starting containers..."
docker compose up --build -d

Write-Host ""
Write-Host "[STEP] Waiting briefly for services to settle..."
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "[OK] Stack started."
Write-Host "Web UI:  http://localhost:3000"
Write-Host "API:     http://localhost:8000"
Write-Host "Docs:    http://localhost:8000/docs"
Write-Host ""
Write-Host "To load a demo alert, run:"
Write-Host "  .\demo-post-alert.bat"
Write-Host ""
Write-Host "To watch logs, run:"
Write-Host "  docker compose logs -f"
