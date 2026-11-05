import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToString } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as publicApi from '@modules/leaderboard';

test('exposes exactly its documented public API', () => {
  assert.deepEqual(Object.keys(publicApi).sort(), ['LEADERBOARD_QUERY_KEY', 'LeaderboardView']);
});

test('renders the leaderboard (loading state) with its no-recommendation disclaimer', () => {
  const html = renderToString(
    <QueryClientProvider client={new QueryClient()}>
      <publicApi.LeaderboardView />
    </QueryClientProvider>,
  );
  assert.match(html, /Assessment leaderboard/);
  assert.match(html, /Nothing here is a hiring recommendation/i);
});
