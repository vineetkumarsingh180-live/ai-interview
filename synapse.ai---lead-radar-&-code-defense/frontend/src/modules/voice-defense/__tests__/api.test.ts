import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { startVoiceSession, submitVoiceTurn } from '../api';

const realFetch = globalThis.fetch;
let last: { url: string; init?: RequestInit } | null = null;
beforeEach(() => {
  globalThis.fetch = (async (url: any, init?: RequestInit) => {
    last = { url: String(url), init };
    return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
  }) as typeof fetch;
});
afterEach(() => {
  globalThis.fetch = realFetch;
});

test('startVoiceSession posts to /init with camelCase fields', async () => {
  await startVoiceSession({ repoId: 'r-1', candidateName: 'Ada' });
  assert.equal(last?.url, '/api/v1/assessment/voice/init');
  assert.deepEqual(JSON.parse(String(last?.init?.body)), { repoId: 'r-1', candidateName: 'Ada' });
});

test('submitVoiceTurn sends the server-issued session id and the answer', async () => {
  await submitVoiceTurn({ sessionId: 's-1', speechText: 'My answer' });
  assert.equal(last?.url, '/api/v1/assessment/voice/turn');
  assert.deepEqual(JSON.parse(String(last?.init?.body)), { sessionId: 's-1', candidateSpeechText: 'My answer' });
});
