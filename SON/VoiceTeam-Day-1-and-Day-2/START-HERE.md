# VoiceTeam — local setup

For the current Days 5–6 update, follow **UPDATE-DAY-5-6.md**. Merge the ZIP contents into:

```text
E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2
```

1. Stop both servers, then merge and replace the changed files.
2. Run `.\SETUP-DAY-5-6.cmd` from project root.
3. Add your Groq key to `apps/api/.env` (server only).
4. Run `.\START-API.cmd` and `.\START-WEB.cmd` in two separate PowerShell windows.
5. Open http://127.0.0.1:5173 and click Connect API.

Keep both terminals running. API health is http://127.0.0.1:8010/health. Text answers stream from Groq; microphone recordings produce a transcript for review before sending. Speech playback starts in Day 7.

Requirements: Node 22.12+, npm, Python 3.12, Groq API key, internet. All `VITE_` variables are public; never put secrets there. `apps/web/.env` should contain `VITE_API_BASE_URL=http://127.0.0.1:8010`.

Manual installation alternative:

```powershell
npm.cmd ci --include=dev
# Create this environment only if it does not exist:
py -3.12 -m venv apps/api/.venv
.\apps\api\.venv\Scripts\python.exe -m pip install --require-hashes -r apps/api/requirements.txt
# Copy each example only if the corresponding .env does not already exist:
Copy-Item apps/api/.env.example apps/api/.env
Copy-Item apps/web/.env.example apps/web/.env
```

On macOS/Linux, use `python3.12 -m venv apps/api/.venv`, `apps/api/.venv/bin/python -m pip install --require-hashes -r apps/api/requirements.txt`, then `sh scripts/dev-api.sh` in a separate terminal from `npm run dev`.

Checks: `npm run typecheck`, `npm run build`, `npm run test:contracts`. From `apps/api`, run `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. Provider doubles in tests are not live Groq acceptance. See the day logs for remaining manual checks.
