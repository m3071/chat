@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_CMD="
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PYTHON_CMD if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PYTHON_CMD set "PYTHON_CMD=python"

echo [STEP] Installing launcher build dependency...
"%PYTHON_CMD%" -m pip install --user -r launcher\requirements.txt
if errorlevel 1 exit /b 1

echo [STEP] Building CyberRed.exe ...
"%PYTHON_CMD%" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --windowed ^
  --name CyberRed ^
  --exclude-module tkinter ^
  --exclude-module PyQt5 ^
  --exclude-module PyQt6 ^
  --exclude-module PySide2 ^
  --exclude-module PySide6 ^
  --exclude-module gi ^
  --exclude-module matplotlib ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  --exclude-module PIL ^
  launcher\desktop_app.py
if errorlevel 1 exit /b 1

echo.
echo [OK] Build complete.
echo EXE: dist\CyberRed\CyberRed.exe
exit /b 0
