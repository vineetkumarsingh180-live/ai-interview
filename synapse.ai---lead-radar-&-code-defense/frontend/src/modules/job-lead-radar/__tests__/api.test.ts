import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { fetchLeads, ingestPost, generateOutreachDraft } from '../api';

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

test('fetchLeads builds the query only from active filters', async () => {
  await fetchLeads({ platform: 'all', minScore: 0 });
  assert.equal(last?.url, '/api/v1/leads/ingest/recent');
  await fetchLeads({ platform: 'reddit', minScore: 80 });
  assert.equal(last?.url, '/api/v1/leads/ingest/recent?platform=reddit&min_score=80');
});

test('ingestPost sends a camelCase contract body', async () => {
  await ingestPost({ platform: 'twitter', authorHandle: '', authorName: '', rawContent: 'Hiring', sourceChannel: 'Manual import' });
  const body = JSON.parse(String(last?.init?.body));
  assert.equal(body.rawContent, 'Hiring');
  assert.equal(body.sourceChannel, 'Manual import');
  assert.ok(typeof body.externalId === 'string' && body.externalId.length > 5);
  assert.equal('raw_content' in body, false);
});

test('generateOutreachDraft sends leadId and omits an empty background', async () => {
  await generateOutreachDraft({ leadId: '11111111-1111-1111-1111-111111111111', tone: 'Executive', candidateProfile: '  ' });
  const body = JSON.parse(String(last?.init?.body));
  assert.deepEqual(body, { leadId: '11111111-1111-1111-1111-111111111111', tone: 'Executive' });
});
