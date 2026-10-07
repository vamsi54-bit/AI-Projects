"""Isolated provider doubles only. These do not count as live Groq acceptance."""
import asyncio
import json
import unittest
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime, timezone
import httpx
from fastapi.testclient import TestClient
from app import main
from app.provider import GroqProvider, ProviderError, Settings

ORIGIN = 'http://127.0.0.1:5173'

def question(ready, text='Hello', sequence=1, **extra):
    return dict(type='chat.send', event_id=str(uuid4()), session_id=ready['session_id'], request_id=str(uuid4()), turn_id=str(uuid4()), sequence=sequence, timestamp=datetime.now(timezone.utc).isoformat(), agent='system', payload={'text': text}, **extra)

class TestStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        for part in ['Hello ', 'world']:
            await asyncio.sleep(.02)
            yield ('data: ' + json.dumps({'choices': [{'delta': {'content': part}}]}) + '\n\n').encode()
        yield b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'

class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_and_request_credentials(self):
        def respond(request):
            self.assertEqual(request.headers['authorization'], 'Bearer test-key')
            self.assertTrue(json.loads(request.content)['stream'])
            return httpx.Response(200, stream=TestStream())
        provider = GroqProvider(Settings('test-key'), httpx.MockTransport(respond))
        self.assertEqual(''.join([x async for x in provider.stream_chat([{'role': 'user', 'content': 'Hello'}])]), 'Hello world')

    async def test_errors_do_not_leak_provider_body_or_key(self):
        for status, code in [(401, 'PROVIDER_AUTH'), (429, 'RATE_LIMITED'), (503, 'PROVIDER_UNAVAILABLE')]:
            provider = GroqProvider(Settings('secret-test-key'), httpx.MockTransport(lambda r: httpx.Response(status, text='secret-test-key raw provider error')))
            with self.assertRaises(ProviderError) as caught:
                _ = [x async for x in provider.stream_chat([])]
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('secret-test-key', str(caught.exception))
        with self.assertRaises(ProviderError) as caught:
            _ = [x async for x in GroqProvider(Settings()).stream_chat([])]
        self.assertEqual(caught.exception.code, 'NOT_CONFIGURED')

    async def test_provider_timeout_is_sanitized(self):
        def timeout(request):
            raise httpx.ReadTimeout('private transport details', request=request)
        provider = GroqProvider(Settings('test'), httpx.MockTransport(timeout))
        with self.assertRaises(ProviderError) as caught:
            _ = [x async for x in provider.stream_chat([])]
        self.assertEqual(caught.exception.code, 'PROVIDER_TIMEOUT')
        self.assertNotIn('private', str(caught.exception))

    async def test_truncated_empty_and_invalid_streams_fail(self):
        for raw in [b'data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\n', b'data: [DONE]\n\n', b'data: {broken}\n\n', b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n']:
            provider = GroqProvider(Settings('test'), httpx.MockTransport(lambda r: httpx.Response(200, content=raw)))
            with self.assertRaises(ProviderError):
                _ = [x async for x in provider.stream_chat([])]

    async def test_transcription_multipart_silence_and_limits(self):
        def respond(request):
            self.assertIn('multipart/form-data', request.headers['content-type'])
            self.assertIn(b'whisper-large-v3-turbo', request.content)
            return httpx.Response(200, json={'text': 'What is gravity?'})
        provider = GroqProvider(Settings('test'), httpx.MockTransport(respond))
        self.assertEqual(await provider.transcribe(b'x' * 100, 'audio/webm', 'webm'), 'What is gravity?')
        for body in [{'text': ''}, {'text': 'hallucination', 'segments': [{'no_speech_prob': .99, 'avg_logprob': -2}]}, {'text': 'x' * 1201}]:
            provider = GroqProvider(Settings('test'), httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
            with self.assertRaises(ProviderError): await provider.transcribe(b'x'*100, 'audio/webm', 'webm')

class ChatVoiceTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        def respond(request):
            self.requests.append(request)
            if request.url.path.endswith('/audio/transcriptions'):
                return httpx.Response(200, json={'text': 'What is gravity?'})
            return httpx.Response(200, stream=TestStream())
        self.provider = GroqProvider(Settings('test-key'), httpx.MockTransport(respond))
        self.patch = patch.object(main, 'provider', self.provider); self.patch.start()
        self.client = TestClient(main.app); self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None); self.patch.stop()

    def ws(self): return self.client.websocket_connect('/ws', headers={'origin': ORIGIN})

    def until_done(self, ws):
        events = []
        for _ in range(20):
            event = ws.receive_json(); events.append(event)
            if event['type'] in ('chat.done', 'chat.error'): return events
        self.fail('No terminal chat event')

    def test_chat_stream_follow_up_and_heartbeat(self):
        with self.ws() as ws:
            ready = ws.receive_json(); self.assertTrue(ready['payload']['provider_ready'])
            first = question(ready); ws.send_json(first)
            ping = {**question(ready, sequence=2), 'type': 'health.ping', 'turn_id': ready['turn_id'], 'payload': {}}
            ws.send_json(ping)
            events = self.until_done(ws)
            self.assertIn('health.pong', [e['type'] for e in events])
            self.assertEqual(''.join(e['payload']['text'] for e in events if e['type'] == 'chat.delta'), 'Hello world')
            for event in events:
                if event['type'].startswith('chat.'):
                    self.assertEqual(event['turn_id'], first['turn_id']); self.assertEqual(event['request_id'], first['request_id'])
            ws.send_json(question(ready, 'Remember my question?', sequence=3)); self.until_done(ws)
            self.assertEqual([m['role'] for m in json.loads(self.requests[-1].content)['messages']], ['system', 'user', 'assistant', 'user'])
        self.assertNotIn(ready['session_id'], main.sessions)

    def test_replay_and_busy_do_not_duplicate_provider_calls(self):
        with self.ws() as ws:
            ready = ws.receive_json(); event = question(ready); ws.send_json(event); ws.send_json(event)
            ws.send_json(question(ready, sequence=2))
            events = []
            while len([e for e in events if e['type'] == 'chat.done']) < 1:
                events.append(ws.receive_json())
            self.assertIn('DUPLICATE_EVENT', [e['payload'].get('code') for e in events])
            self.assertIn('BUSY', [e['payload'].get('code') for e in events])
            self.assertEqual(len(self.requests), 1)

    def test_missing_key_chat_error_and_health_still_works(self):
        with patch.object(main, 'provider', GroqProvider(Settings())):
            with self.ws() as ws:
                ready = ws.receive_json(); self.assertFalse(ready['payload']['provider_ready'])
                ws.send_json(question(ready)); events = self.until_done(ws)
                self.assertEqual(events[-1]['payload']['code'], 'NOT_CONFIGURED')
                ws.send_json({**question(ready, sequence=2), 'type': 'health.ping', 'turn_id': ready['turn_id'], 'payload': {}})
                self.assertEqual(ws.receive_json()['type'], 'health.pong')

    def test_audio_requires_live_session_and_allowed_origin_and_size(self):
        headers = {'origin': ORIGIN, 'content-type': 'audio/webm'}
        self.assertEqual(self.client.post('/transcribe', headers=headers, content=b'x'*100).status_code, 401)
        with self.ws() as ws:
            ready = ws.receive_json(); headers['authorization'] = 'Bearer ' + ready['session_id']
            self.assertEqual(self.client.post('/transcribe', headers={**headers, 'origin':'https://example.com'}, content=b'x'*100).status_code, 403)
            self.assertEqual(self.client.post('/transcribe', headers={**headers, 'content-type':'text/plain'}, content=b'x'*100).status_code, 415)
            self.assertEqual(self.client.post('/transcribe', headers=headers, content=b'').status_code, 400)
            self.assertEqual(self.client.post('/transcribe', headers=headers, content=b'x'*(main.MAX_AUDIO_BYTES+1)).status_code, 413)
            response = self.client.post('/transcribe', headers=headers, content=b'x'*100)
            self.assertEqual(response.json(), {'text': 'What is gravity?'})
        self.assertEqual(self.client.post('/transcribe', headers=headers, content=b'x'*100).status_code, 401)

    def test_disconnect_cancels_generation(self):
        import threading
        cancelled = threading.Event()
        class SlowProvider:
            configured = True
            async def stream_chat(self, history):
                try:
                    yield 'started'
                    await asyncio.sleep(120)
                finally:
                    cancelled.set()
        with patch.object(main, 'provider', SlowProvider()):
            with self.ws() as ws:
                ready = ws.receive_json(); ws.send_json(question(ready))
                self.assertEqual(ws.receive_json()['type'], 'chat.started')
                self.assertEqual(ws.receive_json()['type'], 'chat.delta')
            self.assertTrue(cancelled.wait(1))
            self.assertNotIn(ready['session_id'], main.sessions)

    def test_request_limit_and_history_are_bounded(self):
        with self.ws() as ws:
            ready = ws.receive_json(); session = main.sessions[ready['session_id']]
            for i in range(8):
                ws.send_json(question(ready, sequence=i+1)); self.until_done(ws)
            self.assertEqual(len(session.history), 12)
            session.calls = 40
            ws.send_json(question(ready, sequence=9))
            self.assertEqual(self.until_done(ws)[-1]['payload']['code'], 'RATE_LIMITED')
