@echo off
setlocal
cd /d "%~dp0"
echo VoiceTeam - install Day 5 and Day 6 dependencies
if not exist "apps\api\app\provider.py" (
  echo ERROR: Extract the whole update into your project folder first.
  goto failed
)
if not exist "package-lock.json" (
  echo ERROR: Run this in VoiceTeam-Day-1-and-Day-2 beside package.json.
  goto failed
)
call npm.cmd ci --include=dev
if errorlevel 1 goto failed
if not exist "apps\api\.venv\Scripts\python.exe" (
  py -3.12 -m venv "apps\api\.venv"
  if errorlevel 1 goto failed
)
"apps\api\.venv\Scripts\python.exe" -m pip install --require-hashes -r "apps\api\requirements.txt"
if errorlevel 1 goto failed
if not exist "apps\api\.env" copy "apps\api\.env.example" "apps\api\.env" >nul
if not exist "apps\web\.env" copy "apps\web\.env.example" "apps\web\.env" >nul
echo.
echo Installed. Add your GROQ_API_KEY to apps\api\.env using Notepad.
echo Never add it to apps\web or send it in a screenshot.
echo Then run START-API.cmd and START-WEB.cmd in separate windows.
exit /b 0
:failed
echo.
echo Setup stopped. Keep this error output and check UPDATE-DAY-5-6.md.
exit /b 1
