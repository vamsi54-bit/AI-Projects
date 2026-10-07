@echo off
setlocal
cd /d "%~dp0"
if not exist "apps\api\.venv\Scripts\python.exe" (
  echo Run SETUP-DAY-5-6.cmd first.
  exit /b 1
)
"apps\api\.venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir apps/api --reload --reload-dir apps/api --host 127.0.0.1 --port 8010 --ws-max-size 8192
