import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToString } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as publicApi from '@modules/code-verifier';

test('exposes exactly its documented public API', () => {
  assert.deepEqual(Object.keys(publicApi).sort(), ['CodeVerifierView', 'useRepoEvaluation']);
});

function Host() {
  const state = publicApi.useRepoEvaluation();
  return <publicApi.CodeVerifierView state={state} />;
}

test('renders the code verifier with no repositories loaded', () => {
  const html = renderToString(
    <QueryClientProvider client={new QueryClient()}>
      <Host />
    </QueryClientProvider>,
  );
  assert.match(html, /Candidate repositories/);
  assert.match(html, /Select or submit a repository/);   // honest empty state, not a fabricated score
  assert.doesNotMatch(html, /Production Ready/);
});
