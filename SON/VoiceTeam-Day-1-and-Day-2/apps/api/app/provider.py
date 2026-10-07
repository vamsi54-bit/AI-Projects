"""Groq adapters. Credentials and provider requests stay on the API server."""
import json
import os
from dataclasses import dataclass
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)

@dataclass(frozen=True)
class Settings:
    api_key: str = ''
    chat_model: str = 'llama-3.3-70b-versatile'
    speech_model: str = 'whisper-large-v3-turbo'

    @classmethod
    def from_env(cls):
        return cls(os.getenv('GROQ_API_KEY', '').strip(), os.getenv('GROQ_CHAT_MODEL', 'llama-3.3-70b-versatile').strip(), os.getenv('GROQ_STT_MODEL', 'whisper-large-v3-turbo').strip())

class ProviderError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message

SYSTEM_PROMPT = (
    'You are the Supervisor in VoiceTeam, a helpful conversational assistant. '
    'Answer clearly and concisely in the user\'s language. Only you are active. '
    'You have no browser, specialist agents, uploaded files, or live research tools. '
    'Do not claim to delegate tasks, verify sources, browse, or hear audio; voice input is supplied as text. '
    'Be honest about uncertainty. Do not invent citations. Use plain text suitable for a conversation.'
)

class GroqProvider:
    def __init__(self, settings: Settings, transport=None):
        self.settings, self.transport = settings, transport

    @property
    def configured(self):
        return bool(self.settings.api_key and not self.settings.api_key.startswith('paste_your_'))

    def client(self):
        if not self.configured:
            raise ProviderError('NOT_CONFIGURED', 'Add GROQ_API_KEY to apps/api/.env, restart the API, then reconnect.')
        return httpx.AsyncClient(base_url='https://api.groq.com/openai/v1/', headers={'Authorization': f'Bearer {self.settings.api_key}'}, timeout=httpx.Timeout(30, connect=10), transport=self.transport)

    @staticmethod
    def check(response):
        if response.status_code < 400:
            return
        code, message = {
            401: ('PROVIDER_AUTH', 'Groq rejected the API key. Check apps/api/.env and restart the API.'),
            403: ('PROVIDER_AUTH', 'Groq denied access. Check your account and model permissions.'),
            429: ('RATE_LIMITED', 'Groq rate limit reached. Wait a moment, then send again.'),
            400: ('PROVIDER_REQUEST', 'Groq rejected the request. Check the model settings or try a shorter recording.'),
            404: ('PROVIDER_REQUEST', 'The configured Groq model was not found. Check apps/api/.env.'),
            413: ('AUDIO_TOO_LARGE', 'The recording is too large. Try a shorter recording.'),
        }.get(response.status_code, ('PROVIDER_UNAVAILABLE', 'Groq is unavailable. Please try again shortly.'))
        # Never forward provider bodies, headers or keys to the browser.
        raise ProviderError(code, message)

    async def stream_chat(self, history):
        try:
            async with self.client() as client:
                async with client.stream('POST', 'chat/completions', json={
                    'model': self.settings.chat_model, 'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}, *history],
                    'stream': True, 'temperature': 0.5, 'max_completion_tokens': 1024,
                }) as response:
                    self.check(response)
                    total = 0
                    finished = False
                    async for line in response.aiter_lines():
                        if not line.startswith('data:'):
                            continue
                        data = line[5:].strip()
                        if data == '[DONE]':
                            if not total or not finished:
                                raise ProviderError('PROVIDER_RESPONSE', 'The answer was empty or interrupted. Please send again.')
                            return
                        packet = json.loads(data)
                        if 'error' in packet:
                            raise ProviderError('PROVIDER_RESPONSE', 'The answer was interrupted by Groq. Please send again.')
                        for choice in packet.get('choices', []):
                            if choice.get('finish_reason') == 'length':
                                raise ProviderError('RESPONSE_LIMIT', 'Answer length limit reached. Ask a narrower question or request a shorter answer.')
                            if choice.get('finish_reason') is not None:
                                finished = True
                            content = choice.get('delta', {}).get('content')
                            if content:
                                if not isinstance(content, str):
                                    raise ValueError('Invalid content')
                                total += len(content)
                                if total > 16000:
                                    raise ProviderError('RESPONSE_LIMIT', 'Answer length limit reached. Ask for a shorter answer.')
                                # Stay within the existing 8 KiB WebSocket frame budget, even for Unicode.
                                for start in range(0, len(content), 400):
                                    yield content[start:start + 400]
                    raise ProviderError('PROVIDER_RESPONSE', 'The answer stream ended unexpectedly. Please send again.')
        except httpx.TimeoutException:
            raise ProviderError('PROVIDER_TIMEOUT', 'Groq took too long to respond. Please try again.') from None
        except httpx.HTTPError:
            raise ProviderError('PROVIDER_UNAVAILABLE', 'Could not reach Groq. Check your internet connection.') from None
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ProviderError('PROVIDER_RESPONSE', 'Groq returned an invalid response. Please try again.') from None

    async def transcribe(self, audio: bytes, mime: str, extension: str):
        try:
            async with self.client() as client:
                response = await client.post('audio/transcriptions', files={'file': (f'recording.{extension}', audio, mime)}, data={
                    'model': self.settings.speech_model, 'response_format': 'verbose_json', 'temperature': '0',
                })
                self.check(response)
                body = response.json()
                text = body.get('text', '').strip()
                segments = body.get('segments') or []
                silent = bool(segments) and all(s.get('no_speech_prob', 0) > 0.6 and s.get('avg_logprob', 0) < -1 for s in segments)
                if not text or silent:
                    raise ProviderError('NO_SPEECH', 'No clear speech detected. Try again closer to the microphone.')
                if len(text) > 1200:
                    raise ProviderError('TRANSCRIPT_TOO_LONG', 'The transcript is too long. Record a shorter question.')
                return text
        except httpx.TimeoutException:
            raise ProviderError('PROVIDER_TIMEOUT', 'Transcription timed out. Try a shorter recording.') from None
        except httpx.HTTPError:
            raise ProviderError('PROVIDER_UNAVAILABLE', 'Could not reach Groq. Check your internet connection.') from None
        except (ValueError, TypeError, AttributeError):
            raise ProviderError('PROVIDER_RESPONSE', 'Groq returned an invalid transcript. Please try again.') from None
