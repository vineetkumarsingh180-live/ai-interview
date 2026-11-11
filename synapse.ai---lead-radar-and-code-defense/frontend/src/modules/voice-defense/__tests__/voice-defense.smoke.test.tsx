import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToString } from 'react-dom/server';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as publicApi from '@modules/voice-defense';

test('exposes exactly its documented public API', () => {
  assert.deepEqual(Object.keys(publicApi).sort(), ['VoiceDefenseView', 'useVoiceStream']);
});

function Host({ candidate }: { candidate: publicApi.VoiceCandidate | null }) {
  const session = publicApi.useVoiceStream(candidate?.name, candidate?.id);
  return <publicApi.VoiceDefenseView session={session} candidate={candidate} />;
}

function render(candidate: publicApi.VoiceCandidate | null) {
  return renderToString(
    <QueryClientProvider client={new QueryClient()}>
      <Host candidate={candidate} />
    </QueryClientProvider>,
  );
}

test('renders without a candidate and shows no score before an answer', () => {
  const html = render(null);
  assert.match(html, /No candidate selected/);
  assert.match(html, /Not scored/);
  assert.match(html, /Start the interview to receive the opening question/);
  assert.doesNotMatch(html, /auto[-_ ]?hire/i);
});

test('takes the candidate from its host via the narrow VoiceCandidate shape', () => {
  const html = render({ id: 'r1', name: 'Ada Lovelace', repoName: 'engine', targetRole: 'Staff Eng', commitSha: 'abc123' });
  assert.match(html, /Ada Lovelace/);
  assert.match(html, /engine/);
});
