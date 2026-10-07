# Day 6 — Recorded microphone input and speech-to-text

Status: **BLOCKED for live acceptance; implementation delivered** (2026-10-07).

Implemented:
- Browser permission-based MediaRecorder capture, supported MIME selection, Web Audio quiet-level check, 60-second cap and 5 MiB limit.
- Track/context cleanup on stop/cancel, tab hidden, preview, disconnect or component removal; unresolved permission grants and stale transcription results cannot reactivate cancelled capture.
- Local API upload linked to an active socket session. Origin/MIME/size/time checks and one operation per session. Groq transcription receives multipart audio; raw audio stays in memory and is not saved by this app.
- Editable transcript is inserted into the text input. The user reviews it and presses Send to reach Day 5 chat. Denied microphone access, no microphone, silence, invalid/empty transcript, provider error, oversized recording and timeouts show actionable feedback.
- Text fallback remains available. No speech playback, continuous listening, specialist work or interruption was added.

Verification:
- TypeScript/build and shared frontend/API test suites passed.
- Browser MediaRecorder using Chromium's synthetic input traversed actual local HTTP upload to the isolated Groq adapter double, produced a transcript, allowed editing, and submitted it over the real local WebSocket. This was not live speech recognition.
- Cancellation released all media tracks. A denied-permission fixture preserved the text fallback. A zero-level audio fixture was rejected before upload. The 60,000 ms timer registration and auto-stop/track cleanup passed with a test-only accelerated timer.
- Empty/silent provider output, upload origin/session requirements, unsupported MIME and 5 MiB limit covered in API tests.

Remaining acceptance: use a physical microphone and a real Groq key, say an English question, confirm the recognized transcript, correct if needed, Send, and receive the actual model answer. Run a real 60-second recording to check physical-device behavior. Groq availability, transcription accuracy, Windows execution and physical mobile browsers were not tested here. Under README section 8, these live checks are required for COMPLETE.

See `../verification/day-05-06.md` and `../../UPDATE-DAY-5-6.md`. Do not advance to Day 7 automatically.
