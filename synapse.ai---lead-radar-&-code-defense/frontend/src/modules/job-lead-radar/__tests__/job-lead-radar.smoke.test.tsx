import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToString } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as publicApi from '@modules/job-lead-radar';

test('exposes exactly its documented public API', () => {
  assert.deepEqual(Object.keys(publicApi).sort(), ['LeadRadarView']);
});

test('renders the lead radar (loading state) without a backend', () => {
  const html = renderToString(
    <QueryClientProvider client={new QueryClient()}>
      <publicApi.LeadRadarView />
    </QueryClientProvider>,
  );
  assert.match(html, /Lead radar/);
  assert.match(html, /Simulate raw post/);
  assert.match(html, /Filter title, company or stack/);
});
