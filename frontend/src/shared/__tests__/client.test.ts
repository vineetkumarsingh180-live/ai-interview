import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { requestJson, ApiError } from '@shared/api/client';

const realFetch = globalThis.fetch;
let calls: Array<{ url: string; init?: RequestInit }> = [];

function mockFetch(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  globalThis.fetch = (async (url: any, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    return handler(String(url), init);
  }) as typeof fetch;
}

beforeEach(() => {
  calls = [];
});
afterEach(() => {
  globalThis.fetch = realFetch;
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

test('sends JSON bodies and parses JSON responses', async () => {
  mockFetch(() => json({ ok: true }));
  const out = await requestJson<{ ok: boolean }>('/api/v1/x', { method: 'POST', body: { a: 1 }, errorMessage: 'fail' });
  assert.deepEqual(out, { ok: true });
  assert.equal(calls[0].url, '/api/v1/x');
  assert.equal(calls[0].init?.method, 'POST');
  assert.equal(calls[0].init?.body, '{"a":1}');
});

test('maps the structured error envelope to ApiError (detail, code, field errors)', async () => {
  mockFetch(() =>
    json({ detail: 'Request validation failed', code: 'validation_error', errors: [{ field: 'repoUrl', message: 'bad' }] }, 422),
  );
  await assert.rejects(requestJson('/api/v1/x', { errorMessage: 'fallback' }), (err: unknown) => {
    assert.ok(err instanceof ApiError);
    assert.equal(err.message, 'Request validation failed (repoUrl: bad)');
    assert.equal(err.status, 422);
    assert.equal(err.code, 'validation_error');
    assert.deepEqual(err.fieldErrors, [{ field: 'repoUrl', message: 'bad' }]);
    return true;
  });
});

test('uses the fallback message when the error body is not the envelope', async () => {
  mockFetch(() => new Response('<html>oops</html>', { status: 502 }));
  await assert.rejects(requestJson('/api/v1/x', { errorMessage: 'Service is down' }), (err: unknown) => {
    assert.ok(err instanceof ApiError);
    assert.equal(err.message, 'Service is down');
    assert.equal(err.status, 502);
    return true;
  });
});

test('a network failure is an ApiError("network_error"), never data', async () => {
  mockFetch(() => {
    throw new TypeError('fetch failed');
  });
  await assert.rejects(requestJson('/api/v1/x', { errorMessage: 'x' }), (err: unknown) => {
    assert.ok(err instanceof ApiError);
    assert.equal(err.code, 'network_error');
    assert.equal(err.status, 0);
    return true;
  });
});
