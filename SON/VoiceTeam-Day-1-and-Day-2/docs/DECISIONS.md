# Foundation decisions — 2026-10-06

## Scope and source

The user explicitly requested Days 1 AND 2 in one ZIP, superseding the README's one-day-per-request workflow for this delivery only. Stop after Day 2. The supplied README is the scope authority. No existing SON source tree was supplied; the Windows path is the extraction destination, not an accessible repository. No commits, pushes, or deployments were performed.

## Stack

React with TypeScript and Vite; Tailwind's Vite plugin plus semantic CSS tokens/layouts. Use Vite 7 and plugin-react 5 as a compatible baseline, not a claim of latest versions. Exact installed versions are in package.json and package-lock.json. `npm ci` reproduces the resolved dependency tree. Node 22.12+ is the documented project baseline. Verification runtime details are in the day logs.

Python 3.12, FastAPI and Uvicorn. `requirements.in` records direct dependencies; `requirements.txt` pins their resolved transitive dependencies and distribution hashes. Use pip's `--require-hashes`. A plain sync health handler returns a typed response. No provider calls, session scaffolding, CORS middleware, or dotenv loading is necessary for the health-only API.

The frontend and API run independently. The frontend makes no backend calls on Day 2. 'Not connected' is a static label, not a measured network state. Placeholder controls use native disabled semantics. Example use-case tags are plain text, not fake buttons. Icons are static inline SVG, not animated avatars. No animation engine, LangGraph or provider SDK is installed ahead of its day.

## Providers and costs

| Capability | Selection | Credentials / capability checks | Cost status |
| --- | --- | --- | --- |
| Text / tool / vision model | PENDING | No app credentials or budget supplied. Before Day 5, select provider and model, record its credential names, official model capabilities and rates. Before Day 15 verify image input. | PENDING; no live usage or API calls |
| Speech transcription | PENDING | Select before Day 6; check recording formats, limits, supported language and credential requirements. | PENDING; record official per-minute/request rates at selection |
| Speech synthesis | PENDING | Select before Day 7; verify four supported distinct voices before Day 14. No voice cloning. | PENDING; record official audio/character/token rates at selection |
| Search | PENDING | Select before Day 11; verify source URL output, limits and server credential names. | PENDING; record official request pricing at selection |

Provider decisions pending is explicitly allowed by the README on Day 1. No live integration is claimed. Do not put future secrets in `VITE_` variables or ask the user to send keys in chat. Coding-tool subscriptions are not application API billing.

## Deployment decision

PENDING provider/plan selection. Architecture remains a built static frontend and a persistent, single-instance Dockerized FastAPI backend with HTTPS/WSS and bounded in-memory state. Render is only a candidate from the specification, not a selected service or free-hosting promise. Verify its limits and pricing when choosing the deployment plan. Container implementation belongs to Day 24; hosting to Days 25 and 28. No deployment configuration is scaffolded now.

## Official references checked for this implementation

- https://vite.dev/guide/ — development/build workflow and Node compatibility.
- https://v7.vite.dev/guide/migration — Vite 7 Node baseline.
- https://tailwindcss.com/docs/installation/using-vite — official Vite plugin and CSS import.
- https://fastapi.tiangolo.com/tutorial/first-steps/ — FastAPI instance and HTTP route.
- https://fastapi.tiangolo.com/deployment/manually/ — Uvicorn startup.

These references concern the foundation only. Provider and hosting pricing has not been selected or quoted.

## Day 3–4 additions

The user authorized both days together and replaced the static stage with exact violet/magenta, cyan/blue, coral/amber, and emerald/lime profiles. Original SVG avatars and CSS keyframes meet this day’s animation needs without adding Motion for React. Body text does not animate. CSS reduced-motion rules take precedence immediately; the preference toggle is stored locally. Offscreen animation pauses via passive scroll/resize measurement, limited to one animation frame per avatar. Mobile uses smaller translations and fewer decorative loops.

Day 3 fixtures are local state behind a labeled preview view. They never create API messages or transcript entries. Live cards remain unavailable until actual agents exist. A connected transport is not described as a connected AI agent.

Day 4 uses WebSocket /ws and retains GET /health. The chosen default API port is now 8010 because the user confirmed 8000 was blocked on Windows and 8010 worked. Session readiness is followed by a health.ping/health.pong round trip. A 20-second health heartbeat with a five-second response deadline detects lost transport; there is no automatic reconnection or task replay. A reconnect creates a fresh socket/session and drops previous request state. No model requests exist.

Strict Pydantic inputs and explicit TypeScript runtime guards reject malformed events. The frontend rejects cross-session and stale-turn events and ignores duplicate/older sequence output. Each direction has its own monotonic sequence. Socket state is in-memory and released on close; session lifetime is 30 minutes, with 1000 messages and 8192 bytes per frame. The event list is capped at 30. Local origin checks are not authentication; later public access controls are still required. Only health is advertised as a capability.

Official references checked:
- https://fastapi.tiangolo.com/advanced/websockets/
- https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_client_applications
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion


## Days 5–6 — Groq and bounded recorded voice (2026-10-07)

- Use Groq for both Supervisor chat and speech-to-text, consistent with the user's provider preference. Defaults are `llama-3.3-70b-versatile` and `whisper-large-v3-turbo`; change server `.env` model names if account availability changes.
- Use HTTPX directly against Groq's documented Chat Completions SSE and multipart transcription APIs. Locked HTTPX and dotenv dependencies; no frontend API key and no provider SDK required.
- Official references checked: https://console.groq.com/docs/text-chat , https://console.groq.com/docs/speech-to-text , https://console.groq.com/docs/models . No claim of free or unlimited use. Account/model limits apply.
- Preserve the Day 4 WebSocket, upgrade the contract to v2, stream request-scoped `chat.*` events. Health stays responsive during generation. Each answer has a unique turn; strict schemas reject mismatches/replays. Reconnect clears context and cancels outstanding tasks.
- Browser MediaRecorder records only after a button click. Maximum 60 seconds / 5 MiB; capture tracks stop on finish, cancellation, preview, hidden page, disconnect or unmount. The Web Audio analyser provides a quiet-level check, not a speech-recognition guarantee. STT additionally handles empty/no-speech output.
- Transcription is a bounded HTTP upload with exact local-origin and active session-token checks. Audio is held in memory only and sent to Groq. Transcripts require review/Send before chat; no background listening or automatic resubmission.
- Keep at most six complete conversation pairs / 24k characters. Max 1200 characters per question, 16k per generated answer, 1024 provider output tokens, 40 provider operations per 30-minute session, 32 active sessions. Local loopback only; account access/cost controls remain Day 22.
- All generated text is rendered as text, not raw HTML. Errors are sanitized; no raw Groq body/key is sent to the UI. Tests contain isolated provider doubles but runtime has no fallback fabricated responses.
- Day 5/6 code can be delivered without a key; README acceptance remains BLOCKED until live model/STT and physical microphone checks pass. Do not start Day 7 in this update.
