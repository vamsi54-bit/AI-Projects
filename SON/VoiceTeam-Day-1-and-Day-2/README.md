# VoiceTeam — A Live Voice AI Team

> Working project name. A deployable, colorful, animated web app where you speak naturally to a supervisor AI, and it coordinates three specialist agents to help you.

**Current status:** Days 1–4 verified. Days 5–6 implementation adds Groq Supervisor text streaming and recorded speech transcription; live acceptance awaits your local key/microphone. Follow `UPDATE-DAY-5-6.md`. See `docs/PROGRESS.md` for verification and blockers. Speech playback and specialists arrive in later days.

**Build schedule:** 28 development days, completed one day at a time in Cursor. A development day is a scope unit, not a promise about hours. If a day is blocked, finish that same day in the next session; never silently shrink it or jump ahead.

The user explicitly authorized Days 3 and 4 together and supplied exact gradient colors, CSS/SVG character direction, a central stage, and a fixed dock. The frontend-only boundary applies to Day 3; the requested Day 4 adds the roadmap’s transport connection only. On 2026-10-07 the user authorized Days 5 and 6 together as the next merge ZIP.

## 1. What exactly are we building?

VoiceTeam is a general-purpose, voice-first assistant with a visible team of agents. It accepts spoken questions, typed messages, and optional images or documents. The supervisor understands the request, asks for clarification when necessary, delegates relevant tasks, and delivers a clear final response.

Users can hear brief agent exchanges and see who is listening, researching, solving, checking, or speaking. They can interrupt, correct instructions, and continue the conversation.

Images are one input option. The project also supports explanations, research, comparisons, planning, document questions, and code assistance. It is not limited to image analysis or a speech benchmark.

The first release targets a focused version of this experience, not complete feature parity with every general-purpose AI product.

### Example without an upload

**User:** “Explain solar energy simply and research its main advantages.”

- **Supervisor:** “I’ll ask the researcher to find sources and the problem solver to prepare a simple explanation.”
- **Researcher:** Retrieves relevant information and records sources.
- **Problem solver:** Produces a clear explanation based on the request and available evidence.
- **Verifier:** Checks the proposed answer for unsupported claims and missing requirements.
- **Supervisor:** Gives one concise spoken answer, with a fuller text response and source links.

**User interrupts:** “Wait, explain it for a school presentation.”

The app stops outdated speech, cancels or invalidates the old task, and uses the corrected instruction.

### Example with an upload

**User:** Uploads a PDF and says, “Summarize this and explain the difficult parts.”

The team works from extracted document content, identifies relevant pages, and returns a spoken summary with a readable answer. If the file cannot be read, the app says so instead of guessing.

These examples describe intended behavior, not existing implementation or guaranteed model accuracy.

## 2. The four agents

| Agent | Responsibility | Visual identity | Voice direction |
| --- | --- | --- | --- |
| Supervisor | Main conversation, clarification, delegation, cancellation, final synthesis | Violet and magenta; central expressive orb | Warm, clear, confident |
| Researcher | Web research, source collection, evidence summaries | Cyan and blue; curious floating character | Curious, informative |
| Problem solver | Explanations, reasoning about provided content, image/PDF analysis, code suggestions | Coral and amber; energetic character | Practical, friendly |
| Verifier | Check claims, citations, coverage of the request, and uncertainty | Emerald and lime; attentive character | Calm, precise |

Each agent must have a separate role instruction, structured inputs and outputs, and real execution status. They may share one underlying model provider. Four agents do not require four separately trained models.

The supervisor chooses the necessary specialists. Independent tasks may run concurrently; dependent work waits for its inputs. The verifier receives the proposed result and available evidence before checking it. Allow at most one revision cycle in the first release.

**Visible communication means useful summaries, findings, and handoffs.** Do not expose private chain-of-thought or manufacture a scripted debate and present it as real work. A checker reduces some errors; it does not certify that every answer is true.

## 3. First-release scope

### Included by the end of the plan

- Voice conversation with text input as a fallback.
- Speech transcription and spoken responses.
- Four consistent agent voices, selected from voices actually supported by the chosen speech provider.
- Stop playback, correct a request, and interrupt by speaking when the audio setup supports reliable interruption.
- Conversation context within the active session.
- Supervisor delegation to three specialists.
- Live captions, task status, brief handoffs, source links, and final answers.
- Web research through one configured search integration.
- One image or one text-based PDF per request, within enforced size limits.
- Explanations and code suggestions; uploaded or generated code is never executed automatically.
- Quick mode for simple requests and Team mode for specialist collaboration.
- Team audio or Final-answer-only audio, plus mute and volume controls.
- Session reset and download of the transcript/final answer as Markdown.
- A colorful, highly animated desktop experience, a lighter mobile layout, and reduced-motion support.
- Hosted HTTPS frontend and a backend capable of maintaining live connections.
- Controlled demo access, request limits, server-side credentials, and operational error handling.

### Explicitly outside the first 28 days

- Image or video generation; image understanding is included.
- Autonomous email sending, purchases, calendar edits, or control of the user's computer.
- Arbitrary code execution, unrestricted web browsing, and background autonomous jobs.
- Native mobile applications, wake-word detection, or listening while the page is closed.
- Full-duplex overlapping agent speech, voice cloning, and photorealistic human avatars.
- OCR for scanned PDFs, huge document collections, and production RAG infrastructure.
- Full user accounts, payment plans, cross-device history, and long-term personal memory.
- A multilingual accuracy promise. English is the initial acceptance language; additional languages require provider selection and separate evaluation after this plan.

These boundaries keep the general-purpose assistant achievable. Do not add deferred features because a package makes them easy to scaffold.

## 4. Interface and animation direction

**Desired feel:** A lively team of friendly animated characters, with vivid color, expressive motion, and clear conversation controls.

### Screen layout

- Center stage: a large supervisor character with three distinct specialist characters around it.
- Each character has an always-readable name, role, and status label.
- Conversation panel: user messages, concise agent updates, final answers, and clickable sources.
- Bottom control dock: microphone, text input, attachment, stop, mute, mode, and audio preference.
- Expandable task panel: current assignments and completed findings.
- Attachment preview and contextual error messages near the affected controls.
- On mobile: supervisor first, specialists in a compact stack, and a reachable control dock.

### Visual rules

- Use a light neutral or soft lavender base, vivid agent accents, gradient highlights, and restrained translucent panels.
- Create abstract, original orb/creature avatars using SVG, CSS, and component animation; external character images are not required.
- Include expressive eyes, subtle idle movement, responsive hover effects, smooth panel entrances, and clear speaking states.
- Animate a brief handoff between the supervisor and assigned agent when a real delegation event occurs.
- Drive mouth/waveform motion from actual playback amplitude when available. Do not represent a decorative loop as live audio measurement.
- Agent states: idle, listening, transcribing, working, speaking, waiting, complete, cancelled, and error.
- Use text and icons alongside color so status is understandable without color perception.
- Keep body text stable while background/character elements animate.
- Respect reduced-motion preferences; provide a motion toggle; avoid flashes, autoplay sound, and excessive camera movement.
- Prefer transform/opacity animation, cap decorative particles, and pause offscreen motion. Rich animation must not interfere with audio.

Early visual fixtures are allowed only in a clearly labeled demo/preview state. Live mode must be driven by actual backend events.

## 5. Proposed implementation baseline

This is an implementation choice for this project. Verify current compatible versions and official documentation on Day 1, then lock versions. Do not switch stacks later without explaining a concrete blocker.

| Layer | Baseline | Purpose |
| --- | --- | --- |
| Web app | React, TypeScript, Vite | Interactive browser interface |
| Styling and animation | Tailwind CSS, Motion for React, SVG/CSS | Responsive colorful characters and transitions |
| API server | Python, FastAPI | Provider calls, uploads, validation, session management |
| Agent orchestration | LangGraph | Explicit supervisor/specialist state and bounded execution |
| Live updates | WebSocket for events/control; HTTP for bounded uploads | Stream progress and coordinate cancellation |
| Voice | Browser microphone plus server-side STT and TTS adapters | Speech input and agent audio output |
| Intelligence | Configurable model adapter with text/tool capabilities and image support | Reasoning and multimodal requests |
| Research | One server-side search provider | Retrieve evidence with source URLs |
| Deployment | Dockerized persistent backend; built static frontend | Reproducible deployment with HTTPS/WSS |
| Initial session storage | Bounded, in-memory server state | Avoid unnecessary database scope |

Day 1 records selected model, speech, and search providers, required credentials, supported capabilities, and documented usage costs. Use available credentials and budget if supplied. If unavailable, record provider decisions as pending; do not buy services or claim live integrations are working. Credential-dependent days remain blocked until supplied.

Cursor's subscription is separate from the deployed application's model, speech, search, and hosting usage. Do not assume a coding subscription pays for application API calls.

### Planned repository layout

```text
README.md
apps/web/
apps/api/
docs/DECISIONS.md
docs/PROGRESS.md
docs/days/day-XX.md
docs/DEPLOYMENT.md
```

Create only the directories/files required by the current day. This layout is a destination, not permission to scaffold every future module on Day 1.

## 6. Runtime behavior

1. The user explicitly starts a session and grants microphone access.
2. The browser submits a bounded recording or a typed message. Speech is transcribed through the server.
3. The server assigns session, request, and turn identifiers and records the current instruction.
4. The supervisor responds directly or delegates structured tasks to specialists.
5. Specialists return findings, source references, and limitations. Their real events update the interface.
6. The verifier checks the proposed response when appropriate; the supervisor synthesizes the result.
7. A single audio queue speaks concise updates and the final answer. Specialists may work concurrently, but only one voice plays at a time.
8. On interruption, the browser stops and clears playback immediately. The server cancels pending work where possible; responses from an outdated turn are discarded.

Start with turn-based recorded speech. Add automatic end-of-turn detection and barge-in incrementally. Do not promise zero latency or treat ordinary playback as a full real-time speech model.

### Event contract

Every event carries an event ID, session ID, request ID, turn ID, sequence number, timestamp, agent identifier, and typed payload.

Suggested events: `session.ready`, `transcript.final`, `task.assigned`, `agent.status`, `agent.update`, `source.added`, `answer.delta`, `answer.final`, `audio.ready`, `turn.cancelled`, and `error`.

- Reject malformed payloads and events for another session.
- Ignore stale-turn output after a correction.
- Deduplicate replayed events and never replay spoken updates accidentally.
- UI state must come from the event contract, not timers that pretend tasks succeeded.
- Keep user-facing updates concise. Never send API credentials or hidden reasoning in events.

## 7. Deployment and reliability requirements

- The frontend must run over HTTPS; microphone capture requires a secure browser context, with localhost exceptions during development.
- The backend must support long-lived WebSocket connections and use WSS in production. A persistent Render web service is a candidate; verify its current service limits and pricing before choosing a plan.
- Provide container startup, a health endpoint, environment documentation, and exact build/run instructions.
- Keep model, speech, and search credentials on the server. Frontend configuration contains only public values such as the API base URL.
- Use a signed, short-lived demo session after access-code validation; authorize HTTP uploads and WebSocket sessions. Do not put a permanent shared secret in the frontend bundle or connection URL.
- Enforce allowed origins, schema validation, upload size/type limits, and per-session and global usage bounds.
- Initial configurable limits: 60 seconds per recorded utterance, one attachment per turn, 10 MB per attachment, 20 text-PDF pages, a 120-second agent-run timeout, and one verifier-driven revision. Adjust only with documented evidence.
- Bound context size and session lifetime. Provide a clear reset behavior when the server restarts or a session expires.
- Use one backend instance initially because state is in memory. Horizontal scaling requires shared session/job storage and is outside this release.
- Never persist raw audio or uploads by default. Clear temporary data after processing/cancellation; document necessary processing by external providers.
- Handle denied microphone access, silence, unsupported formats, missing credentials, rate limits, timeouts, reconnects, and unavailable providers without a frozen UI.
- Reconnection must not silently duplicate paid model requests or resume cancelled speech. If a task cannot resume safely, explain that it ended and offer an explicit retry.
- Budget and latency figures are measured results, not invented badges. Do not promise free deployment or unlimited usage.

## 8. Strict daily execution contract

**Implement exactly the day requested by the user: no future-day work and no skipped acceptance criteria.**

1. The user provides an explicit day number. Do not infer permission to advance from the calendar date.
2. Read this README, repository instructions, `docs/PROGRESS.md` if present, and the relevant existing code.
3. Inspect the repository before writing; preserve existing user changes.
4. List today's scope, acceptance criteria, and exclusions briefly, then implement it.
5. All earlier prerequisite days must be completed with evidence. If a prerequisite is missing or broken, report the smallest blocker; do not silently implement a different day.
6. Dependencies and infrastructure necessary for today's acceptance are allowed; future features, unnecessary refactors, and speculative scaffolding are not.
7. Run the relevant checks and the normal build/type checks available for changed components. Do not claim success when commands were not run.
8. Mark the day complete only when every acceptance criterion passes. A live-integration day cannot pass using mocks.
9. Update `docs/PROGRESS.md` and `docs/days/day-XX.md` with status, evidence, changed files, and any manual steps or blockers.
10. Stop once today's checklist is satisfied. Do not start the next day, even if time remains.

If the same day is requested again, resume incomplete work or verify its existing completion. Do not overwrite it or advance automatically. New user instructions can revise scope, but record the change explicitly instead of silently rewriting the roadmap.

### Progress record format

Create this record on Day 1. All 28 days initially have `NOT_STARTED` status.

```markdown
Last completed day: None
Active day: 1

| Day | Status | Evidence / day log |
| --- | --- | --- |
| 1 | NOT_STARTED | — |
```

Allowed statuses: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `COMPLETE`. Include all 28 rows in the actual progress file. Record verification commands/results, manual checks still pending, and an optional commit hash for each completed day. Never fabricate a commit or deployment URL.

## 9. The 28-day build plan

The acceptance column is the minimum completion contract for each day. Shared requirements above apply when the relevant feature is introduced. Early local previews remain private; public usage starts only after the access and cost controls are verified.

| Day | Build only this scope | Acceptance criteria | Explicit stop boundary |
| --- | --- | --- | --- |
| 1 | Project foundation: web/API skeleton, health endpoint, local scripts, sample environment files, dependency locks, provider/deployment decision notes, progress records | Web opens locally; API health returns success; production web build passes; exact setup commands recorded; secrets ignored | No dashboard, avatars, AI calls, microphone, WebSockets, or hosting deployment |
| 2 | Static responsive workspace and visual tokens: stage, four agent cards, transcript area, control dock, attachment placeholder | Desktop and narrow mobile layouts are usable; all four roles labeled; inactive controls clearly disabled | No animation engine, audio, backend integration, or fake working buttons |
| 3 | Original animated avatars and component state previews; reduced-motion behavior | Four distinct colored characters visibly support idle/working/speaking/error; preview is labeled; motion toggle works | No real agent activity, microphone, or speech |
| 4 | Typed session/event contract and frontend/backend WebSocket connection | Real connection/disconnection status; health/session-ready round trip; malformed events rejected; preview fixtures isolated | No model calls or simulated specialist success in live mode |
| 5 | Supervisor text conversation through one real model provider | Typed question produces a genuine streamed text answer; provider failure is visible; credentials stay server-side | No specialist graph, speech, research, or uploads |
| 6 | Microphone capture and real speech-to-text; push-to-talk/record-and-submit | Spoken request appears as a transcript and reaches Day 5 chat; denial, silence, and recording limit handled | No speech playback or continuous listening |
| 7 | Supervisor text-to-speech and a single playback queue | A real response is spoken after user interaction; captions remain readable; mute works; audio never overlaps | No specialist voices or voice interruption detection |
| 8 | Stop-and-correct controls with turn cancellation | Stop clears playback/queue; typed or newly recorded correction creates a new turn; late old output is ignored | No automatic barge-in or specialist delegation |
| 9 | In-session voice activity detection, automatic turn end, and spoken barge-in | On tested hardware, user speech interrupts playback and produces a corrected turn; echo behavior checked; push-to-talk fallback retained | No background wake word or unsupported full-duplex promise |
| 10 | LangGraph supervisor routing and bounded task state | Supervisor creates validated specialist assignments for relevant requests; direct path works; unit fixtures verify routing and cancellation | Specialist integrations remain explicitly unavailable until their days; no fake completed tasks |
| 11 | Researcher with one real search integration | Research request invokes search and returns relevant source-linked findings; unavailable search produces an honest error | No arbitrary browsing, PDF/image work, or unscheduled tools |
| 12 | Problem solver specialist for text requests and supplied code snippets | Separate specialist receives its assignment and returns structured output; supervisor incorporates it; research findings can be passed as evidence | No code execution, image/PDF parsing, or verifier |
| 13 | Verifier and bounded revision workflow | Checker receives draft/evidence/request; identifies a seeded unsupported claim; supervisor revises or marks uncertainty; loop cannot run forever | No claim of guaranteed correctness or unbounded debate |
| 14 | Live agent communication and four voice identities | Actual assignments, concise findings, and handoffs drive cards/captions; four configured voices speak in order; Final-answer-only mode works | No scripted conversations shown as genuine work |
| 15 | One-image upload, preview, validation, and vision analysis | A real image request reaches a vision-capable model; answer references visible content; invalid/oversized uploads rejected; uncertainty supported | No image generation, editing, OCR pipeline, or batch attachments |
| 16 | Text-PDF upload and page-aware extraction | A supported PDF can be summarized/questioned using extracted text with page references; scanned/oversized PDFs get clear limitations | No OCR, vector database, or unlimited document context |
| 17 | Bounded session context and clarification | Follow-up references and corrections retain relevant context; ambiguous requests ask a question; reset clears context and attachments | No cross-session personal memory or account system |
| 18 | Quick/Team mode and complete voice preference controls | Quick uses supervisor directly; Team delegates when useful; mode and audio preferences apply predictably to subsequent turns; volume/mute work | No forcing four model calls for every request |
| 19 | Final live animation integration and responsive polish | Real audio drives speaking motion; actual delegation drives handoffs; keyboard/reduced-motion flows work; mobile avoids heavy effects | No new assistant capabilities or decorative 3D engine |
| 20 | Session export, clear-session behavior, and data lifecycle | Markdown export contains actual transcript/final answer/sources; raw uploads/audio are not silently saved; reset cleans active session data | No database-backed history, cloud sync, or PDF report generator |
| 21 | Runtime resilience, deadlines, retry policy, and context budgets | Simulated provider timeout/rate limit/disconnect ends in recoverable UI; no duplicate spoken messages or blind reruns; limits enforced | No new providers, features, or queue infrastructure |
| 22 | Controlled access and cost/security hardening | Unauthorized sessions/uploads rejected; per-session/global limits enforced; origin checks work; secret and sensitive-log review passes | No billing, social login, enterprise roles, or public launch |
| 23 | Critical-path automated regression suite | Meaningful checks cover routing, stale turns, cancellation, event ownership, upload limits, access limits, and verifier bounds; clearly label mocked provider tests | No paid API stress testing or tests that merely duplicate implementation |
| 24 | Deployment packaging and operator instructions | Clean web build and backend container startup pass; health and shutdown work; environment/setup documentation is reproducible | No production publication or unrelated code refactoring |
| 25 | Deploy a controlled staging instance | Hosted HTTPS app connects over WSS; microphone, real model response, TTS, research, and uploads work remotely; record actual URL and results | Do not declare release ready or bypass missing credentials/account setup |
| 26 | Cross-device/browser and voice usability checks | Test desktop plus a real mobile browser where available; verify permission handling, barge-in/fallback, readable layout, reconnect, and motion settings; record unavailable tests honestly | Fix only defects found in existing features; no scope expansion |
| 27 | Release review and measured demo walkthrough | Run voice, research, image, PDF, correction, and failure scenarios; record latency and available usage metrics; finish setup/troubleshooting and remaining release blockers | No new features, invented performance numbers, or skipped failures |
| 28 | Release deployment, hosted smoke test, and project handoff | Deploy reviewed version with access/cost controls; verify live URL and core scenarios; finalize README and known limitations; prepare final commit/release notes | Stop. Do not implement a Day 29 or deferred features |

For deployment days, complete all local preparation first. If account access, credentials, budget approval, or required manual actions are unavailable, provide exact next steps and keep that day `BLOCKED`. “Deployable” and “successfully deployed” are different statuses.

## 10. Reusable Cursor daily prompt

Place this README in the project root. Open that folder in Cursor. Paste the prompt below into Agent mode, changing only `DAY_TO_BUILD` to the day you explicitly want to complete.

```text
DAY_TO_BUILD = 1

You are the implementation engineer for VoiceTeam, a voice-first web app with
one supervisor and three specialist agents. Treat the root README.md as the
project specification and 28-day scope contract. Follow repository instructions
and the user's latest explicit corrections.

YOUR TASK
Complete exactly DAY_TO_BUILD. Implement every acceptance criterion for that
day, verify it, document the result, and stop. Do not begin any later day.
The roadmap describes the eventual application, not permission to build it all.

BEFORE EDITING
1. Read README.md, applicable repository instructions, docs/PROGRESS.md if it
   exists, today's day log if it exists, and the code relevant to today's work.
2. Inspect git status. Preserve unrelated changes and do not overwrite work.
3. Verify prerequisite days. If required previous work is missing or broken,
   report the specific blocker and the smallest prerequisite repair needed;
   do not silently change today's scope.
4. State today's deliverables, acceptance checks, and exclusions briefly.
   Then proceed without asking for approval for ordinary in-scope edits.

IMPLEMENTATION RULES
- Build only what today's acceptance requires. Shared helper changes are
  allowed only when directly necessary; explain why.
- Do not scaffold future-day services, routes, tools, accounts, or integrations.
- Use the agreed stack. Check official documentation when integrating changing
  APIs. Lock compatible versions instead of guessing SDK methods or model IDs.
- Keep credentials server-side. Provide environment variable names/examples,
  never real secrets in source, logs, commits, or browser bundles.
- For credential-dependent work, request only the missing setup; never buy a
  service or mark a mocked integration as real. Never ask me to paste secrets
  into chat when they can be set locally or in the host's secret settings.
- Use real backend events for live agent activity. Visual fixtures must be
  explicitly labeled. No invented research, sources, checks, or task completion.
- Keep cancellation and session isolation intact whenever changing runtime code.
- Follow the colorful animated character design, accessibility, and reduced-
  motion rules on the days that implement UI. Protect audio responsiveness.
- Make reasonable local implementation choices. Ask a focused question only
  when a missing decision materially blocks today's acceptance.

VERIFICATION AND RECORDS
- Run the build/type checks relevant to touched components and targeted tests
  or manual checks for today's acceptance. Inspect actual results.
- Do not use mocks to claim live integration acceptance. Do not invent tests,
  browser observations, benchmark numbers, commits, or deployment results.
- Fix issues introduced by today's work within scope. Report unrelated failures.
- Create/update docs/PROGRESS.md and docs/days/day-XX.md with actual outcomes,
  commands, changed files, remaining manual steps, and blockers.
- Mark COMPLETE only after every acceptance criterion passes. Otherwise mark
  IN_PROGRESS or BLOCKED with a precise explanation. Never reduce scope to
  make the day appear complete.
- On Day 1, create progress entries for all 28 days, initially NOT_STARTED.
- If this day is already COMPLETE, verify the record, explain any gaps, and
  stop; do not automatically choose the next day.
- Do not commit or push automatically. Provide a proposed commit message and
  stage only scoped files if I explicitly request a commit. Push only when I
  have explicitly requested it and the destination is known.

FINAL RESPONSE FORMAT
Day N — COMPLETE / IN_PROGRESS / BLOCKED
Built: short list of today's actual deliverables.
Verified: checks actually run and their results.
Files changed: concise list.
Run/demo: exact commands and what I should see, if applicable.
Blockers/manual steps: only if present.
Suggested commit: day-N: <brief actual change>
Stopped at Day N. No later-day features implemented.

Do not continue to the next day unless I explicitly ask for it in a new request.
```

### First use

1. Create a project folder and save this file there as `README.md`.
2. Open that folder in Cursor.
3. Paste the daily prompt with `DAY_TO_BUILD = 1`.
4. Let Cursor finish the Day 1 checklist and inspect its verification results.
5. When you choose to begin Day 2, use the same prompt with `DAY_TO_BUILD = 2`.

The prompt and progress record provide a repeatable working process. They are not a technical sandbox; review Cursor's proposed changes and its final scope report.

## 11. Final release definition

The release is complete only when a visitor with authorized demo access can:

- Open the real hosted app and start a voice session.
- Ask a question and receive genuine spoken and written output.
- Watch real specialist assignments, findings, and handoffs with distinct voices.
- Interrupt or correct a request without hearing stale output afterward.
- Ask about a supported image or text-PDF and receive a grounded response.
- Research a topic and inspect actual source links.
- Use Quick/Team and audio modes without overlapping speech.
- Reset the session, export its text, and recover from ordinary errors.
- Use a readable mobile layout and reduced-motion option.

The repository must also have reproducible setup/deployment instructions, no committed credentials, a verified build, meaningful regression checks, enforced demo limits, and honest known limitations.

## 12. Official implementation references

Baseline references checked while preparing this plan on 2026-10-05. Recheck the relevant documentation when implementing each integration.

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [LangGraph Python reference](https://reference.langchain.com/python/langgraph/overview)
- [Browser microphone and secure-context requirements](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [Render WebSocket hosting](https://render.com/docs/websocket)
- [Render web services](https://render.com/docs/web-services)

Model, speech, and search provider documentation links belong in `docs/DECISIONS.md` once those services have actually been selected.
