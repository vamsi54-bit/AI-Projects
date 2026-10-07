# VoiceTeam event contract — protocol 2 (Days 5–6)

All events carry `type`, `event_id`, `session_id`, `request_id`, `turn_id`, `sequence`, UTC `timestamp`, `agent`, and `payload`. UUID identifiers are canonical; unknown envelope fields are rejected. Sequences increase per sender/socket. JSON text frames have an 8192-byte limit. WebSocket endpoint: `/ws`.

| Direction | Type | Payload | Scope |
| --- | --- | --- | --- |
| Server → web | session.ready | protocol_version: 2; capabilities: health/chat/transcription; provider_ready: boolean | New session and connection turn, sequence 1 |
| Web → server | health.ping | empty | Connection turn, agent system |
| Server → web | health.pong | status: ok; service: voiceteam-api | Same request and connection turn, agent system |
| Web → server | chat.send | text: nonblank, ≤1200 characters | New turn/request, agent system |
| Server → web | chat.started | empty | Requested chat turn/request, agent supervisor |
| Server → web | chat.delta | text: incremental content | Same chat turn/request, agent supervisor |
| Server → web | chat.done | empty | Terminal success, same chat turn/request |
| Server → web | chat.error | code and sanitized message | Terminal failure, same chat turn/request |
| Server → web | error | code and sanitized message | Invalid protocol/expired session, connection turn |

Only one provider operation is active per socket. Heartbeats continue during streaming. The browser accepts chat events only for its pending request and rejects cross-session/turn/request output. Duplicate/out-of-order frames are ignored. Disconnect cancels the server's active generation/transcription and discards in-memory history. No paid request is replayed automatically. The browser retains incomplete visible text with a failure label until a new session starts; it never becomes model context.

Protocol errors: INVALID_MESSAGE, WRONG_SESSION, INVALID_TURN, STALE_EVENT, DUPLICATE_EVENT, SESSION_EXPIRED, TOO_MANY_MESSAGES. Chat failures include NOT_CONFIGURED, PROVIDER_AUTH, RATE_LIMITED, PROVIDER_REQUEST, PROVIDER_UNAVAILABLE, PROVIDER_TIMEOUT, PROVIDER_RESPONSE, RESPONSE_LIMIT, BUSY and INTERNAL_ERROR.

## HTTP recorded audio

`POST /transcribe`: raw recorded audio bytes, `Content-Type: audio/webm` (or audio/ogg, audio/mp4, audio/wav), `Authorization: Bearer <active-session-id>`, and an allowed browser Origin. The session UUID is an ephemeral local capability, not an account login. CORS allows only localhost/127.0.0.1 on 5173/4173. State is per process; run one local API instance.

The server reads at most 5 MiB, checks the MIME allowlist, bounds upload/provider time, and forwards a multipart file to Groq. It does not persist audio or decode it locally; container validation is performed by the transcription provider. Response: `{ "text": "recognized question" }`. Failure: FastAPI `detail` string or `{code,message}` with no raw provider error. No transcript is inserted after a cancelled recording or changed session.

Limits: 60-second frontend recording cap; 20-second upload deadline; 45-second transcription deadline; 60-second total chat deadline; 30-minute session; 40 provider operations per session; 32 sockets; 1000 incoming events per socket. `/health` requires no provider key and reports API liveness only.
