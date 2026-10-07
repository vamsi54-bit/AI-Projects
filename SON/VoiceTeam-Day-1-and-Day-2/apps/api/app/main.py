import asyncio
import json
import time
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from .events import ChatSend, HealthPing
from .provider import GroqProvider, ProviderError, Settings

app = FastAPI(title='VoiceTeam API', version='0.3.0', description='Local Supervisor chat and recorded speech-to-text.')
ALLOWED_ORIGINS = {f'http://{host}:{port}' for host in ('localhost', '127.0.0.1') for port in (5173, 4173)}
app.add_middleware(CORSMiddleware, allow_origins=list(ALLOWED_ORIGINS), allow_methods=['POST'], allow_headers=['Content-Type', 'Authorization'])
MAX_FRAME_BYTES, MAX_AUDIO_BYTES, MAX_MESSAGES, SESSION_SECONDS = 8192, 5 * 1024 * 1024, 1000, 1800
provider = GroqProvider(Settings.from_env())

@dataclass
class Session:
    expires: float
    active: bool = True
    busy: bool = False
    calls: int = 0
    history: list = field(default_factory=list)
    task: asyncio.Task | None = None
    audio_task: asyncio.Task | None = None

sessions: dict[str, Session] = {}

class HealthResponse(BaseModel):
    status: Literal['ok']
    service: Literal['voiceteam-api']

@app.get('/health', response_model=HealthResponse)
def health():
    return HealthResponse(status='ok', service='voiceteam-api')

@app.post('/transcribe')
async def transcribe(request: Request):
    if request.headers.get('origin') not in ALLOWED_ORIGINS:
        raise HTTPException(403, 'Origin is not allowed.')
    token = request.headers.get('authorization', '').removeprefix('Bearer ')
    session = sessions.get(token)
    if not session or not session.active or session.expires <= time.monotonic():
        raise HTTPException(401, 'Connect to the API before recording.')
    if session.busy:
        raise HTTPException(409, 'Wait for the current request to finish.')
    if session.calls >= 40:
        raise HTTPException(429, 'Session request limit reached. Reconnect to continue.')
    mime = request.headers.get('content-type', '').split(';')[0].strip().lower()
    formats = {'audio/webm': 'webm', 'audio/ogg': 'ogg', 'audio/mp4': 'mp4', 'audio/wav': 'wav'}
    if mime not in formats:
        raise HTTPException(415, 'Unsupported recording format. Use Chrome or Edge.')
    session.busy = True
    try:
        data = bytearray()
        async with asyncio.timeout(20):
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > MAX_AUDIO_BYTES:
                    raise HTTPException(413, 'Recording exceeds 5 MB. Try a shorter recording.')
        if len(data) < 100:
            raise HTTPException(400, 'The recording is empty. Try recording again.')
        if not session.active:
            raise HTTPException(401, 'Session ended. Reconnect to continue.')
        session.calls += 1
        session.audio_task = asyncio.create_task(provider.transcribe(bytes(data), mime, formats[mime]))
        text = await asyncio.wait_for(session.audio_task, timeout=45)
        return {'text': text}
    except ProviderError as error:
        raise HTTPException(502, {'code': error.code, 'message': error.message}) from None
    except TimeoutError:
        raise HTTPException(504, 'Recording upload or transcription timed out. Try again.') from None
    finally:
        session.busy = False
        session.audio_task = None

@app.websocket('/ws')
async def connection(websocket: WebSocket):
    # Local origin checks are not account authentication. Keep bound to loopback until Day 22.
    if websocket.headers.get('origin') not in ALLOWED_ORIGINS or len(sessions) >= 32:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    session_id, connection_turn = uuid4(), uuid4()
    session = Session(time.monotonic() + SESSION_SECONDS)
    sessions[str(session_id)] = session
    server_sequence = client_sequence = 0
    seen_events, seen_requests, used_turns = set(), set(), {connection_turn}
    send_lock = asyncio.Lock()

    async def send(event_type, payload, request_id=None, turn_id=None, agent='system'):
        nonlocal server_sequence
        async with send_lock:
            server_sequence += 1
            await websocket.send_text(json.dumps(dict(type=event_type, payload=payload, event_id=str(uuid4()), session_id=str(session_id), request_id=str(request_id or uuid4()), turn_id=str(turn_id or connection_turn), sequence=server_sequence, timestamp=datetime.now(timezone.utc).isoformat(), agent=agent), ensure_ascii=False))

    async def error(code, message, request_id=None):
        await send('error', {'code': code, 'message': message}, request_id)

    async def chat(event):
        args = dict(request_id=event.request_id, turn_id=event.turn_id, agent='supervisor')
        try:
            await send('chat.started', {}, **args)
            if not provider.configured:
                raise ProviderError('NOT_CONFIGURED', 'Add GROQ_API_KEY to apps/api/.env, restart the API, then reconnect.')
            session.calls += 1
            messages = [*session.history, {'role': 'user', 'content': event.payload.text}]
            answer = ''
            async with asyncio.timeout(60):
                async for delta in provider.stream_chat(messages):
                    answer += delta
                    await send('chat.delta', {'text': delta}, **args)
            # Only complete pairs enter model context. Retain at most six pairs / 24k characters.
            session.history = [*messages, {'role': 'assistant', 'content': answer}][-12:]
            while len(session.history) > 2 and sum(len(m['content']) for m in session.history) > 24000:
                del session.history[:2]
            await send('chat.done', {}, **args)
        except ProviderError as exc:
            await send('chat.error', {'code': exc.code, 'message': exc.message}, **args)
        except TimeoutError:
            await send('chat.error', {'code': 'PROVIDER_TIMEOUT', 'message': 'The answer timed out. Please send again.'}, **args)
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass
        except Exception:
            await send('chat.error', {'code': 'INTERNAL_ERROR', 'message': 'The request failed. Please try again.'}, **args)
        finally:
            session.busy = False

    try:
        await send('session.ready', {'protocol_version': 2, 'capabilities': ['health', 'chat', 'transcription'], 'provider_ready': provider.configured})
        for _ in range(MAX_MESSAGES):
            try:
                frame = await asyncio.wait_for(websocket.receive(), timeout=max(.001, session.expires - time.monotonic()))
            except TimeoutError:
                await error('SESSION_EXPIRED', 'Session expired. Reconnect to start a new session.')
                await websocket.close(code=1000)
                return
            if frame['type'] == 'websocket.disconnect':
                return
            raw = frame.get('text')
            if raw is None or len(raw.encode('utf-8')) > MAX_FRAME_BYTES:
                await error('INVALID_MESSAGE', 'Expected a JSON text event of at most 8192 bytes.')
                await websocket.close(code=1009 if raw is not None else 1003)
                return
            try:
                kind = json.loads(raw).get('type')
                event = (ChatSend if kind == 'chat.send' else HealthPing).model_validate_json(raw)
            except (ValidationError, ValueError, AttributeError):
                await error('INVALID_MESSAGE', 'Message does not match the event contract.')
                continue
            if event.session_id != session_id:
                await error('WRONG_SESSION', 'Event does not belong to this connection.', event.request_id)
                continue
            if isinstance(event, HealthPing) and event.turn_id != connection_turn:
                await error('INVALID_TURN', 'Health checks must use the connection turn.', event.request_id)
                continue
            if event.event_id in seen_events or event.request_id in seen_requests:
                await error('DUPLICATE_EVENT', 'This event or request was already processed.', event.request_id)
                continue
            if event.sequence <= client_sequence:
                await error('STALE_EVENT', 'Client sequence must increase.', event.request_id)
                continue
            client_sequence = event.sequence
            seen_events.add(event.event_id)
            seen_requests.add(event.request_id)
            if isinstance(event, HealthPing):
                await send('health.pong', {'status': 'ok', 'service': 'voiceteam-api'}, event.request_id)
            else:
                reason = None
                if event.turn_id in used_turns:
                    reason = ('INVALID_TURN', 'Each question needs a new turn.')
                elif session.busy:
                    reason = ('BUSY', 'Wait for the current request to finish.')
                elif session.calls >= 40:
                    reason = ('RATE_LIMITED', 'Session request limit reached. Reconnect to continue.')
                if reason:
                    await send('chat.error', dict(zip(('code', 'message'), reason)), event.request_id, event.turn_id, 'supervisor')
                    continue
                used_turns.add(event.turn_id)
                session.busy = True
                session.task = asyncio.create_task(chat(event))
        await error('TOO_MANY_MESSAGES', 'Connection message limit reached. Reconnect to continue.')
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        pass
    finally:
        session.active = False
        sessions.pop(str(session_id), None)
        for task in (session.task, session.audio_task):
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await task
