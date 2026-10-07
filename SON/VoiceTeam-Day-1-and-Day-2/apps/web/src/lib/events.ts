export const PROTOCOL_VERSION = 2;
export interface Envelope {
  event_id: string; session_id: string; request_id: string; turn_id: string;
  sequence: number; timestamp: string; agent: 'system' | 'supervisor';
}
export type ServerEvent = Envelope & (
  | { type: 'session.ready'; payload: { protocol_version: 2; capabilities: ['health', 'chat', 'transcription']; provider_ready: boolean } }
  | { type: 'health.pong'; payload: { status: 'ok'; service: 'voiceteam-api' } }
  | { type: 'chat.started' | 'chat.done'; payload: Record<string, never> }
  | { type: 'chat.delta'; payload: { text: string } }
  | { type: 'chat.error'; payload: { code: ErrorCode; message: string } }
  | { type: 'error'; payload: { code: ErrorCode; message: string } }
);
export type ClientEvent = Envelope & ({ type: 'health.ping'; payload: Record<string, never> } | { type: 'chat.send'; payload: { text: string } });
export const errorCodes = ['INVALID_MESSAGE', 'WRONG_SESSION', 'INVALID_TURN', 'STALE_EVENT', 'DUPLICATE_EVENT', 'SESSION_EXPIRED', 'TOO_MANY_MESSAGES', 'NOT_CONFIGURED', 'PROVIDER_AUTH', 'RATE_LIMITED', 'PROVIDER_REQUEST', 'PROVIDER_UNAVAILABLE', 'PROVIDER_TIMEOUT', 'PROVIDER_RESPONSE', 'RESPONSE_LIMIT', 'INTERNAL_ERROR', 'INVALID_TURN', 'BUSY', 'AUDIO_TOO_LARGE'] as const;
export type ErrorCode = typeof errorCodes[number];
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const keys = ['event_id', 'session_id', 'request_id', 'turn_id', 'sequence', 'timestamp', 'agent', 'type', 'payload'];
function record(value: unknown): value is Record<string, unknown> { return typeof value === 'object' && value !== null && !Array.isArray(value); }
function exact(value: Record<string, unknown>, expected: string[]) { return Object.keys(value).length === expected.length && expected.every(key => Object.hasOwn(value, key)); }
/** Strict runtime validation. TypeScript alone cannot validate network messages. */
export function parseServerEvent(raw: unknown): ServerEvent {
  if (typeof raw !== 'string' || new TextEncoder().encode(raw).length > 8192) throw new Error('Invalid event frame.');
  const event: unknown = JSON.parse(raw);
  if (!record(event) || !exact(event, keys)) throw new Error('Invalid event envelope.');
  for (const key of ['event_id', 'session_id', 'request_id', 'turn_id']) {
    if (typeof event[key] !== 'string' || !uuid.test(event[key])) throw new Error('Invalid event identifier.');
  }
  if (!Number.isSafeInteger(event.sequence) || (event.sequence as number) < 1 || event.agent !== (typeof event.type === 'string' && event.type.startsWith('chat.') ? 'supervisor' : 'system')) throw new Error('Invalid sequence or agent.');
  if (typeof event.timestamp !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|\+00:00)$/.test(event.timestamp) || !Number.isFinite(Date.parse(event.timestamp))) throw new Error('Invalid timestamp.');
  const p = event.payload;
  if (!record(p)) throw new Error('Invalid payload.');
  if (event.type === 'session.ready') {
    if (!exact(p, ['protocol_version', 'capabilities', 'provider_ready']) || p.protocol_version !== 2 || JSON.stringify(p.capabilities) !== JSON.stringify(['health', 'chat', 'transcription']) || typeof p.provider_ready !== 'boolean') throw new Error('Unsupported session capabilities.');
  } else if (event.type === 'health.pong') {
    if (!exact(p, ['status', 'service']) || p.status !== 'ok' || p.service !== 'voiceteam-api') throw new Error('Invalid health response.');
  } else if (event.type === 'chat.started' || event.type === 'chat.done') {
    if (!exact(p, [])) throw new Error('Invalid chat payload.');
  } else if (event.type === 'chat.delta') {
    if (!exact(p, ['text']) || typeof p.text !== 'string' || p.text.length < 1 || p.text.length > 800) throw new Error('Invalid text delta.');
  } else if (event.type === 'error' || event.type === 'chat.error') {
    if (!exact(p, ['code', 'message']) || !errorCodes.includes(p.code as ErrorCode) || typeof p.message !== 'string' || p.message.length < 1 || p.message.length > 160) throw new Error('Invalid error response.');
  } else throw new Error('Unsupported event type.');
  return event as unknown as ServerEvent;
}
/** One instance per socket. Reconnects cannot reuse the old session or sequence. */
export class SessionGate {
  session: { id: string; turn: string } | null = null;
  private chat: { turn: string; request: string } | null = null;
  expectChat(turn: string, request: string) { this.chat = { turn, request }; }
  finishChat() { this.chat = null; }
  private sequence = 0;
  private seen = new Set<string>();
  accept(event: ServerEvent): boolean {
    if (!this.session) {
      if (event.type !== 'session.ready' || event.sequence !== 1) throw new Error('Expected session.ready first.');
      this.session = { id: event.session_id, turn: event.turn_id };
    } else {
      if (event.session_id !== this.session.id) throw new Error('Event belongs to a different session.');
      if (this.seen.has(event.event_id) || event.sequence <= this.sequence) return false;
      if (event.type.startsWith('chat.')) {
        if (!this.chat || event.turn_id !== this.chat.turn || event.request_id !== this.chat.request) throw new Error('Unexpected chat turn.');
      } else if (event.turn_id !== this.session.turn) throw new Error('Event belongs to an outdated turn.');
      if (event.type === 'session.ready') throw new Error('Session cannot be replaced on this connection.');
    }
    this.sequence = event.sequence;
    this.seen.add(event.event_id);
    if (this.seen.size > 256) this.seen.delete(this.seen.values().next().value!);
    return true;
  }
}
export function healthPing(session: { id: string; turn: string }, sequence: number): ClientEvent {
  return { type: 'health.ping', event_id: crypto.randomUUID(), session_id: session.id, request_id: crypto.randomUUID(), turn_id: session.turn, sequence, timestamp: new Date().toISOString(), agent: 'system', payload: {} };
}

export function chatSend(session: { id: string; turn: string }, sequence: number, text: string): ClientEvent {
  return { ...healthPing(session, sequence), type: 'chat.send', turn_id: crypto.randomUUID(), payload: { text } };
}
