@echo off
setlocal

cd /d "%~dp0"

if not exist "dist\CyberRed\CyberRed.exe" (
  echo [STEP] Desktop EXE not found, building it first...
  call build-exe.bat
  if errorlevel 1 exit /b 1
)

set "ISCC_CMD="
where ISCC >nul 2>nul
if not errorlevel 1 set "ISCC_CMD=ISCC"
if not defined ISCC_CMD if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_CMD if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC_CMD if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC_CMD (
  echo [ERROR] Inno Setup compiler ^(ISCC^) was not found.
  echo Install Inno Setup, then re-run this file.
  exit /b 1
)

echo [STEP] Building installer...
"%ISCC_CMD%" installer\CyberRed.iss
if errorlevel 1 exit /b 1

echo.
echo [OK] Installer created in dist\CyberRedSetup.exe
exit /b 0
