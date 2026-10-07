# VoiceTeam — Day 5 + Day 6 update

This is an update for your working Days 1–4 project. It implements Supervisor text chat through Groq and browser recording → Groq speech-to-text → editable question → Supervisor response.

## 1. Merge into the correct folder

Stop both running servers with Ctrl+C. Extract the ZIP **contents** into:

```text
E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2
```

Choose **Replace files in the destination**. `SETUP-DAY-5-6.cmd` and `UPDATE-DAY-5-6.md` must sit beside `package.json`, with code under the existing `apps` folder. Do not leave the update inside a nested ZIP-named folder. The ZIP contains no `.env`, virtual environment, node_modules, credentials, or raw recordings. Keep your existing `.env` files.

## 2. Install, then add your Groq key

Run in PowerShell:

```powershell
cd "E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2"
.\SETUP-DAY-5-6.cmd
notepad apps\api\.env
```

In **apps/api/.env**, set:

```dotenv
GROQ_API_KEY=paste_your_real_groq_key_here
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
GROQ_STT_MODEL=whisper-large-v3-turbo
```

Get your key at https://console.groq.com/keys. Keep it on your computer; do not paste it into chat, commit it, or put it in `apps/web/.env`. Groq account limits apply. This ZIP does not include a key and does not require an OpenAI key.

The setup installs the locked Python dependencies, including WebSocket support, and all frontend development dependencies. Existing settings are preserved. Python 3.12 and Node 22.12+ are required. If you already have a different `GROQ_API_KEY` environment variable in Windows, it takes precedence over the `.env` file.

## 3. Run both servers

**PowerShell window 1:**

```powershell
cd "E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2"
.\START-API.cmd
```

**PowerShell window 2:**

```powershell
cd "E:\AI PROJECTS\AI-Projects-GitHub\SON\VoiceTeam-Day-1-and-Day-2"
.\START-WEB.cmd
```

Leave both windows open. Open http://127.0.0.1:5173, hard-refresh with Ctrl+Shift+R, and click **Connect API**. `WORKSPACE / 06` appears in the header. Changing API `.env` requires a full API restart and reconnect. For a frontend API URL change, restart Vite too.

## 4. Try Day 5

Type “Explain gravity simply” and press Enter or Send. The Supervisor shows Working and streams the real answer. Ask a follow-up to check conversation context. Only recent successful conversation pairs are kept in server memory; reconnecting clears the conversation. Specialist cards remain Not active.

If the key is missing, the UI tells you where to add it. Invalid keys, exhausted rate limits, provider outages and interrupted answers produce visible errors. Failed or incomplete answers are excluded from future model context. There is no automatic paid retry.

## 5. Try Day 6

Clear/send any draft, click the microphone, and allow browser microphone permission. Speak your question, then click the microphone again to finish. The recording also ends automatically at 60 seconds.

Your audio is submitted to Groq for transcription. Review/edit the text in the input, then press **Send**. This intentionally gives you a chance to correct recognition errors. Cancel recording discards it. Switching to Avatar preview, hiding the tab, disconnecting, or leaving the page releases the microphone. Already-submitted provider work may finish after a user cancellation; its result is not inserted into the cancelled UI.

No recording is saved to disk by this app. Groq processes the submitted audio under its own data policy. The app checks for quiet/empty recordings; noisy environments may still produce inaccurate transcripts. Use Chrome or Edge on localhost for the initial acceptance check.

## What stays unavailable

Spoken replies start on Day 7. Specialist agents, Team mode, uploads, playback Stop/Mute/Volume, and interruption are scheduled later and remain disabled. Avatar preview remains visual-only.

## Troubleshooting

- **Vite not recognized:** from project root run `npm.cmd ci --include=dev`.
- **No supported WebSocket library:** rerun setup; it installs `websockets` into the API's own `.venv`.
- **Could not reach API:** leave the backend running, check http://127.0.0.1:8010/health, then reconnect. `/` returning 404 is expected.
- **Incompatible server event:** frontend and backend versions differ. Merge both `apps/web` and `apps/api`, restart both, and hard-refresh.
- **Key missing despite editing:** confirm the filename is `.env`, not `.env.txt`, under `apps/api`. Stop and restart the API.
- **Connection works but Groq fails:** read the message under the conversation. Check API key/model access, internet and Groq limits.
- **Mic permission denied:** allow the microphone in the browser's site settings. Text chat remains available.
- **No clear audio:** check your input device and speak closer to the microphone. A quiet-level check cannot guarantee speech detection.
- **Port busy:** stop the earlier copy of that server; keep frontend on 5173 and API on 8010. Avoid running two ZIP copies.
- **Setup hash mismatch/install error:** share the install error, without your key; do not disable hash checking as a first fix.

## Verification status

Implementation, TypeScript/build checks, event tests, API tests and browser tests are recorded in `docs/days/day-05.md`, `docs/days/day-06.md` and `docs/verification/day-05-06.md`. Provider tests use clearly labeled isolated doubles; no model response or transcription was fabricated in the app. A real Groq key and a physical microphone were unavailable in the build environment. Under the README completion rule, Days 5–6 remain **BLOCKED for live acceptance** until you verify the two real flows above. No later days were implemented.
