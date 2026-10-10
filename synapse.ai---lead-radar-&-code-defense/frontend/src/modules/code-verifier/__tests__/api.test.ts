import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { submitRepo } from '../api';

const realFetch = globalThis.fetch;
let last: { url: string; init?: RequestInit } | null = null;
beforeEach(() => {
  globalThis.fetch = (async (url: any, init?: RequestInit) => {
    last = { url: String(url), init };
    return new Response('{}', { status: 201, headers: { 'content-type': 'application/json' } });
  }) as typeof fetch;
});
afterEach(() => {
  globalThis.fetch = realFetch;
});

test('submitRepo sends camelCase fields and no invented defaults', async () => {
  await submitRepo({ candidateName: 'Ada', candidateGithubHandle: 'ada', repoUrl: 'https://github.com/ada/engine', targetRole: '  ' });
  assert.equal(last?.url, '/api/v1/assessment/repo/submit');
  const body = JSON.parse(String(last?.init?.body));
  assert.deepEqual(body, { candidateName: 'Ada', candidateGithubHandle: 'ada', repoUrl: 'https://github.com/ada/engine' });
});
