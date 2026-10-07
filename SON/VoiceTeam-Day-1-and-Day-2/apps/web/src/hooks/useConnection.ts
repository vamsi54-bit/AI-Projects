import { useCallback, useEffect, useRef, useState } from 'react';
import { chatSend, healthPing, parseServerEvent, SessionGate, type ServerEvent } from '../lib/events';

type Status = 'disconnected' | 'connecting' | 'checking' | 'connected' | 'error';
export interface Message { id: string; role: 'user' | 'assistant'; text: string; status: 'complete' | 'streaming' | 'failed'; }
interface State { status: Status; message: string; sessionId: string | null; events: ServerEvent[]; latency: number | null; providerReady: boolean; generating: boolean; messages: Message[]; chatError: string }
const initial: State = { status: 'disconnected', message: 'Connect to your local API to begin.', sessionId: null, events: [], latency: null, providerReady: false, generating: false, messages: [], chatError: '' };
export const apiUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8010').replace(/\/$/, '');
export function socketUrl(base: string) {
  const url = new URL(base);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error('Invalid API URL.');
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = `${url.pathname.replace(/\/$/, '')}/ws`;
  return url.toString();
}
export function useConnection() {
  const [state, setState] = useState<State>(initial);
  const current = useRef<WebSocket | null>(null);
  const gate = useRef(new SessionGate());
  const clientSequence = useRef(0);
  const ready = useRef(false);
  const pending = useRef<{ id: string; started: number } | null>(null);
  const chat = useRef<{ id: string; started: boolean } | null>(null);
  const deadline = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chatDeadline = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeat = useRef<ReturnType<typeof setInterval> | null>(null);
  const clearTimers = useCallback(() => {
    if (deadline.current) clearTimeout(deadline.current);
    if (chatDeadline.current) clearTimeout(chatDeadline.current);
    if (heartbeat.current) clearInterval(heartbeat.current);
    deadline.current = null; chatDeadline.current = null; heartbeat.current = null; pending.current = null; chat.current = null; ready.current = false;
  }, []);
  const stop = useCallback(() => {
    const old = current.current; current.current = null;
    clearTimers();
    if (old && old.readyState < WebSocket.CLOSING) old.close(1000, 'Client closed session');
  }, [clearTimers]);
  const endState = useCallback((status: Status, message: string) => {
    setState(previous => ({ ...previous, status, message, sessionId: null, latency: null, generating: false, providerReady: false,
      chatError: previous.generating ? 'Connection ended. This answer is incomplete; reconnect and send again.' : previous.chatError,
      messages: previous.messages.map(m => m.status === 'streaming' ? { ...m, status: 'failed' } : m) }));
  }, []);
  const fail = useCallback((message: string) => { stop(); endState('error', message); }, [stop, endState]);
  const checkHealth = useCallback(() => {
    const ws = current.current; const session = gate.current.session;
    if (!ws || ws.readyState !== WebSocket.OPEN || !session || pending.current) return;
    const event = healthPing(session, ++clientSequence.current);
    pending.current = { id: event.request_id, started: performance.now() };
    if (!ready.current) setState(previous => ({ ...previous, status: 'checking', message: 'Checking the API…' }));
    if (deadline.current) clearTimeout(deadline.current);
    deadline.current = setTimeout(() => { if (current.current === ws) fail('The API health check timed out. Reconnect to try again.'); }, 5000);
    try { ws.send(JSON.stringify(event)); } catch { fail('Could not send the health check. Reconnect to try again.'); }
  }, [fail]);
  const connect = useCallback(() => {
    stop(); gate.current = new SessionGate(); clientSequence.current = 0;
    setState({ ...initial, status: 'connecting', message: 'Opening a local connection…' });
    let ws: WebSocket;
    try { ws = new WebSocket(socketUrl(apiUrl)); } catch { fail('Invalid API URL. Check apps/web/.env and restart Vite.'); return; }
    current.current = ws;
    deadline.current = setTimeout(() => { if (current.current === ws) fail('No handshake received. Start the API on port 8010 and reconnect.'); }, 5000);
    ws.onmessage = message => {
      if (current.current !== ws) return;
      try {
        const event = parseServerEvent(message.data);
        if (!gate.current.accept(event)) return;
        if (event.type === 'health.pong' && (!pending.current || event.request_id !== pending.current.id)) throw new Error('Unsolicited health response.');
        if (!event.type.startsWith('chat.')) setState(previous => ({ ...previous, events: [...previous.events, event].slice(-30) }));
        if (event.type === 'session.ready') {
          setState(previous => ({ ...previous, sessionId: event.session_id, providerReady: event.payload.provider_ready }));
          checkHealth();
        } else if (event.type === 'health.pong') {
          const latency = Math.round(performance.now() - pending.current!.started);
          pending.current = null; ready.current = true;
          if (deadline.current) clearTimeout(deadline.current);
          deadline.current = null;
          setState(previous => ({ ...previous, status: 'connected', message: previous.providerReady ? 'Connection verified. Your Supervisor is ready.' : 'Connection verified. Add GROQ_API_KEY to apps/api/.env, restart the API, then reconnect.', latency }));
          if (!heartbeat.current) heartbeat.current = setInterval(checkHealth, 20000);
        } else if (event.type === 'chat.started') {
          if (!chat.current || chat.current.started) throw new Error('Unexpected chat start.');
          chat.current.started = true;
        } else if (event.type === 'chat.delta') {
          if (!chat.current?.started) throw new Error('Chat did not start.');
          setState(previous => ({ ...previous, messages: previous.messages.map(m => m.id === event.request_id ? { ...m, text: m.text + event.payload.text } : m) }));
        } else if (event.type === 'chat.done' || event.type === 'chat.error') {
          if (event.type === 'chat.done' && !chat.current?.started) throw new Error('Unexpected chat completion.');
          if (chatDeadline.current) clearTimeout(chatDeadline.current);
          chatDeadline.current = null; chat.current = null; gate.current.finishChat();
          setState(previous => ({ ...previous, generating: false, chatError: event.type === 'chat.error' ? event.payload.message : '', messages: previous.messages.map(m => m.id === event.request_id ? { ...m, status: event.type === 'chat.done' ? 'complete' : 'failed' } : m) }));
        } else if (event.type === 'error') fail(`API rejected the message (${event.payload.code}). Reconnect to begin a new session.`);
      } catch { fail('Incompatible or invalid server event. Update both apps/web and apps/api, restart, then reconnect.'); }
    };
    ws.onerror = () => { if (current.current === ws) fail('Could not reach the API. Check that it is running on port 8010.'); };
    ws.onclose = () => {
      if (current.current !== ws) return;
      current.current = null; clearTimers();
      endState('disconnected', 'Connection closed. Reconnect to start a fresh conversation.');
    };
  }, [stop, fail, checkHealth, clearTimers, endState]);
  const sendMessage = useCallback((text: string): boolean => {
    text = text.trim();
    const ws = current.current, session = gate.current.session;
    if (!text || text.length > 1200 || !ready.current || chat.current || !ws || ws.readyState !== WebSocket.OPEN || !session) return false;
    const event = chatSend(session, ++clientSequence.current, text);
    gate.current.expectChat(event.turn_id, event.request_id);
    chat.current = { id: event.request_id, started: false };
    try { ws.send(JSON.stringify(event)); } catch { fail('Could not send the question. Reconnect and try again.'); return false; }
    setState(previous => ({ ...previous, generating: true, chatError: '', messages: [...previous.messages, { id: event.event_id, role: 'user' as const, text, status: 'complete' as const }, { id: event.request_id, role: 'assistant' as const, text: '', status: 'streaming' as const }].slice(-80) }));
    chatDeadline.current = setTimeout(() => fail('The answer timed out. Reconnect and send again.'), 70000);
    return true;
  }, [fail]);
  const disconnect = useCallback(() => { stop(); endState('disconnected', 'Disconnected. Reconnecting starts a new conversation.'); }, [stop, endState]);
  useEffect(() => stop, [stop]);
  return { ...state, connect, disconnect, checkHealth, sendMessage };
}
