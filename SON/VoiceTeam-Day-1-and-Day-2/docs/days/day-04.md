# Day 4 — COMPLETE

Added typed connection envelopes, strict client/server validation, local WebSocket /ws, real session.ready and health.ping/health.pong, explicit connect/disconnect/reconnect, live status, bounded event history and heartbeat timeout. The existing HTTP health endpoint remains. Default backend port is 8010, which the user verified works on Windows. Only health is advertised; all AI roles remain Not active.

Verification performed:
- `npm run typecheck`: pass.
- `npm run build`: pass, Vite production bundle generated.
- `npm run test:contracts`: 5 tests pass (valid payloads, invalid messages, session/turn ownership, duplicate/stale events, scoped ping generation).
- `.venv/bin/python -m unittest discover -s tests -v` from apps/api: 6 tests pass against an actual local Uvicorn server (HTTP and WebSocket round trip; malformed-event recovery; incorrect sessions/turns, duplicates and sequence; connection isolation; origin checks; binary/oversized frames).
- Chromium connected to the real backend, checked health, disconnected/reconnected with a new session, detected a stopped server, displayed an unavailable error and recovered after restart.
- Avatar preview opened no API socket and injected no messages or specialist state into the live view.
- A separate synthetic malformed-server fixture verified a visible client rejection. It is a negative test only; successful connection acceptance used the real API.
- No JavaScript page errors. Evidence: ../verification/day34-results.json.

Files: app/events.py and app/main.py, requirements.in/requirements.txt, tests/test_connection.py, frontend lib/events.ts, hooks/useConnection.ts, tests/events.test.mjs, tsconfig.contracts.json, package scripts, environment examples, dev scripts, docs/EVENTS.md and update/setup documentation.

Tests are scoped to the new event boundary. No future agent graph or mock specialist results were added. Local origin checks are not the later authentication system. No public deployment, model calls, audio or device access. Node 24.19.0/Python 3.12.14 were used here; run provided commands on Windows after merging.

Suggested commit: `day-4: validate session events and connect the local workspace`

Stopped at Day 4. Day 5 remains NOT_STARTED.
