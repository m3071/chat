@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==========================================
echo   Cyber ChatOps MVP Installer / Launcher
echo ==========================================
echo.

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker CLI was not found in PATH.
  echo Install Docker Desktop first, then re-run this file.
  exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker is installed but not running.
  echo Start Docker Desktop, wait until it is ready, then re-run this file.
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy /Y ".env.example" ".env" >nul
    echo [OK] Created .env from .env.example
  ) else (
    echo [WARN] .env.example was not found, continuing without a local .env file.
  )
) else (
  echo [OK] Existing .env found
)

echo.
echo [STEP] Building and starting containers...
docker compose up --build -d
if errorlevel 1 (
  echo [ERROR] Failed to start the stack.
  exit /b 1
)

echo.
echo [STEP] Waiting briefly for services to settle...
timeout /t 8 /nobreak >nul

echo.
echo [OK] Stack started.
echo Web UI:  http://localhost:3000
echo API:     http://localhost:8000
echo Docs:    http://localhost:8000/docs
echo.
echo To load a demo alert, run:
echo   demo-post-alert.bat
echo.
echo To watch logs, run:
echo   docker compose logs -f
echo.
exit /b 0
