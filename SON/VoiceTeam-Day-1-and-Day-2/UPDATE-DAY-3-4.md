# VoiceTeam — Day 3 + Day 4 update

This ZIP contains only changed/new files. Merge it into your existing Day 1–2 project; it is not a separate runnable project.

## 1. Apply the update

Stop both development servers with Ctrl+C. Back up any files you have edited. Extract the ZIP into this exact folder and allow replacement of matching files:

`E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2`

You should now see `UPDATE-DAY-3-4.md` beside your existing `package.json`. Do not create an extra nested Day 3–4 folder.

## 2. Update dependencies and the API address

```powershell
cd "E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2"
npm ci
.\apps\api\.venv\Scripts\python.exe -m pip install --require-hashes -r apps/api/requirements.txt
```

In `apps/web/.env`, set this line (create the file if absent):

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8010
```

Replace any old `VITE_API_BASE_URL` line using port 8000. Keep other settings. Also check `.env.local` if you previously created it, as it can override `.env`. Restart Vite after changing settings.

## 3. Start frontend — terminal 1

```powershell
cd "E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2"
npm run dev
```

Open http://127.0.0.1:5173.

## 4. Start backend — terminal 2

```powershell
cd "E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2\apps\api"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8010 --ws-max-size 8192
```

Health: http://127.0.0.1:8010/health. This uses the port that worked on your Windows machine.

## 5. Try the two days

- **Day 3:** Select **Avatar preview**. Use Idle, Working, Speaking, or Error for all agents, or choose a state on each card. Toggle Motion off/on. An operating-system reduced-motion setting always takes priority. Speaking is only a visual fixture, with no audio.
- **Day 4:** Return to **Live workspace**, then click **Connect API**. The badge becomes **API connected** only after a validated session and real health response. Try Check health, Disconnect, and Reconnect. Connection events contain genuine transport events only.
- Live cards say **Not active** because AI agents are not implemented yet. Microphone, messages, attachments, mode and audio controls remain disabled.

## Checks

From the project root:

```powershell
npm run typecheck
npm run build
npm run test:contracts
cd apps/api
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The API tests start and stop their own local server on an available port. The frontend contract checks use Node's built-in test runner. Node 22.12+ and Python 3.12 remain the baseline.

## Scope

Your frontend-only constraints apply to Day 3. Day 4 follows the earlier approved roadmap: a real local WebSocket connection and strict event validation. No model calls, fake agent results, microphone streams, speech, generated images, or deployment were added.

Local preview only. Accepted browser origins are localhost/127.0.0.1 on ports 5173 and 4173. Public access and authorization are scheduled for later days. Existing .env files, node_modules and virtual environments are not included or replaced by this archive.
