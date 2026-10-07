# Day 1 — COMPLETE

## Built

React + TypeScript + Vite web foundation; FastAPI app with typed GET /health; npm workspace scripts; API startup scripts for PowerShell and shell; .env.example files; .gitignore for secrets, dependencies and builds; exact npm lock and universal Python hash lock; provider/deployment decisions; all 28 progress rows. Setup commands are in START-HERE.md.

## Verification performed

- npm dependency installation passed (84 packages added across the two install steps).
- Python dependency resolution and installation with --require-hashes passed (14 packages); universal lock regenerated successfully and installation rechecked.
- `npm run typecheck`: PASS. Initial missing CSS declaration was fixed with `src/vite-env.d.ts` before the passing run.
- `npm run build`: PASS. Vite 7.3.7 built 29 modules. Output: HTML 0.53 kB, CSS 13.81 kB, JS 230.59 kB.
- Uvicorn startup and actual HTTP GET /health: 200, {"status":"ok","service":"voiceteam-api"}. Shutdown completed cleanly.
- Vite local web app opened in Chromium successfully during the combined Day 1/2 verification. No browser page errors.
- Source package inspected: .env example files only; real credentials were never provided. Git ignore patterns cover .env and .env.* while retaining .env.example. No provider calls or hosted services.

## Changed files

Root package.json/package-lock.json, .gitignore, .nvmrc, README.md current-status line, START-HERE.md; apps/web package/config/HTML/bootstrap files and environment example; apps/api app/__init__.py, app/main.py, requirements.in, requirements.txt and environment example; scripts/dev-api.ps1 and dev-api.sh; docs/DECISIONS.md, PROGRESS.md and day logs.

## Decisions and local follow-up

Provider and hosting-plan selections/costs are PENDING, permitted by the Day 1 contract. Source README's roadmap is retained. Exact Windows setup commands are supplied but have not been executed on the user's machine. No local E: drive access, commit, push or deployment.

Suggested commit: `day-1: add web and API foundation with reproducible setup`
