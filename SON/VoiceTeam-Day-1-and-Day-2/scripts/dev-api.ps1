$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot "apps/api/.venv/Scripts/python.exe"
if (-not (Test-Path $Python)) { throw "Run the API setup commands in START-HERE.md first." }
Push-Location (Join-Path $ProjectRoot "apps/api")
try { & $Python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010 --ws-max-size 8192; if ($LASTEXITCODE -ne 0) { throw "API stopped with exit code $LASTEXITCODE" } } finally { Pop-Location }
