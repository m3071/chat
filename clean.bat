@echo off
setlocal

cd /d "%~dp0"

echo [STEP] Cleaning generated files...
for %%D in (build dist apps\web\.next apps\web\node_modules) do (
  if exist "%%D" rd /s /q "%%D"
)

for /d /r %%D in (__pycache__) do (
  if exist "%%D" rd /s /q "%%D"
)

del /s /q *.pyc *.pyo *.log *.tmp *.bak *.orig *.spec *.tsbuildinfo >nul 2>nul

echo [OK] Clean complete. Reinstall dependencies or rebuild when needed.
exit /b 0
