#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../apps/api"
exec .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010 --ws-max-size 8192
