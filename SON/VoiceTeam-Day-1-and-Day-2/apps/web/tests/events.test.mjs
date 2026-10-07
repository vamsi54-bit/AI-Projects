import { test } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { parseServerEvent, SessionGate, healthPing, chatSend } from '../.test-build/events.js';
const make = overrides => ({ event_id: randomUUID(), session_id: randomUUID(), request_id: randomUUID(), turn_id: randomUUID(), sequence: 1, timestamp: new Date().toISOString(), agent: 'system', type: 'session.ready', payload: { protocol_version: 2, capabilities: ['health', 'chat', 'transcription'], provider_ready: true }, ...overrides });
const parse = event => parseServerEvent(JSON.stringify(event));
test('accepts only the supported ready, pong and error payloads', () => {
  assert.equal(parse(make()).type, 'session.ready');
  assert.equal(parse(make({ type: 'health.pong', payload: { status: 'ok', service: 'voiceteam-api' } })).type, 'health.pong');
  assert.equal(parse(make({ type: 'error', payload: { code: 'INVALID_MESSAGE', message: 'Invalid message' } })).type, 'error');
});
test('rejects malformed JSON, binary frames, unknown fields, invalid IDs and unimplemented events', () => {
  for (const raw of ['{', 'null', '[]', 'x'.repeat(8193), new Uint8Array(2)]) assert.throws(() => parseServerEvent(raw));
  for (const patch of [{ extra: true }, { event_id: 'bad' }, { sequence: true }, { sequence: 1.5 }, { sequence: 0 }, { timestamp: 3 }, { agent: 'supervisor' }, { type: 'agent.status' }, { payload: { protocol_version: 2, capabilities: ['health'] } }, { payload: { protocol_version: 1, capabilities: ['ai'] } }, { type: 'health.pong', payload: { status: 'ok', service: 'other' } }, { type: 'error', payload: { code: 'UNKNOWN', message: 'x' } }]) assert.throws(() => parse(make(patch)));
});
test('requires ready first and rejects cross-session or stale-turn output', () => {
  const gate = new SessionGate(); const ready = parse(make());
  assert.throws(() => gate.accept(parse(make({ sequence: 2 }))));
  assert.equal(gate.accept(ready), true);
  assert.throws(() => gate.accept(parse(make({ sequence: 2 }))));
  assert.throws(() => gate.accept(parse(make({ session_id: ready.session_id, sequence: 2 }))));
});
test('ignores duplicate and out-of-order events; never applies a second ready', () => {
  const gate = new SessionGate(); const ready = parse(make()); gate.accept(ready);
  assert.equal(gate.accept(ready), false);
  const pong = parse(make({ session_id: ready.session_id, turn_id: ready.turn_id, sequence: 3, type: 'health.pong', payload: { status: 'ok', service: 'voiceteam-api' } }));
  assert.equal(gate.accept(pong), true); assert.equal(gate.accept(pong), false);
  assert.equal(gate.accept({ ...pong, event_id: randomUUID(), sequence: 2 }), false);
  assert.throws(() => gate.accept({ ...ready, event_id: randomUUID(), sequence: 4 }));
});
test('creates a new health request with the current connection scope', () => {
  const session = { id: randomUUID(), turn: randomUUID() }; const one = healthPing(session, 1); const two = healthPing(session, 2);
  assert.equal(one.session_id, session.id); assert.equal(one.turn_id, session.turn); assert.equal(one.type, 'health.ping'); assert.deepEqual(one.payload, {});
  assert.notEqual(one.event_id, two.event_id); assert.notEqual(one.request_id, two.request_id); assert.equal(two.sequence, 2);
});

test('chat output is scoped to the outgoing request; health remains on the connection turn', () => {
  const gate = new SessionGate(), ready = parse(make()); gate.accept(ready);
  const sent = chatSend(gate.session, 1, 'Hello');
  assert.notEqual(sent.turn_id, ready.turn_id);
  gate.expectChat(sent.turn_id, sent.request_id);
  const event = { ...ready, event_id: randomUUID(), type: 'chat.delta', agent: 'supervisor', turn_id: sent.turn_id, request_id: sent.request_id, sequence: 2, payload: { text: 'Hello' } };
  assert.equal(gate.accept(parse(event)), true);
  assert.throws(() => gate.accept(parse({ ...event, event_id: randomUUID(), sequence: 3, request_id: randomUUID() })));
  const pong = { ...ready, event_id: randomUUID(), sequence: 3, type: 'health.pong', payload: { status: 'ok', service: 'voiceteam-api' } };
  assert.equal(gate.accept(parse(pong)), true);
  gate.finishChat();
  assert.throws(() => gate.accept(parse({ ...event, event_id: randomUUID(), sequence: 4 })));
});
test('rejects bad chat deltas and terminal payloads', () => {
  for (const patch of [
    { type: 'chat.delta', payload: { text: '' } }, { type: 'chat.delta', payload: { text: 42 } },
    { type: 'chat.delta', payload: { text: 'x'.repeat(801) } },
    { type: 'chat.done', payload: { text: 'unexpected' } },
    { type: 'chat.error', payload: { code: 'UNKNOWN', message: 'wrong' } },
  ]) assert.throws(() => parse(make({ agent: 'supervisor', ...patch })));
  assert.equal(parse(make({ agent: 'supervisor', type: 'chat.error', payload: { code: 'RATE_LIMITED', message: 'Try later.' } })).type, 'chat.error');
});
