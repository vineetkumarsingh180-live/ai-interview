import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToString } from 'react-dom/server';
import { RepoFacts } from '../components/RepoFacts';
import type { CandidateRepo } from '../types';

const base: CandidateRepo = {
  id: '1', candidateName: 'ada', candidateGithubHandle: 'ada', repoUrl: 'https://github.com/ada/engine', repoName: 'engine',
  targetRole: null, branch: null, commitSha: null, language: null, status: 'awaiting_analysis', isDemo: false,
  submittedAt: '2026-01-01T00:00:00Z', sourceType: 'api_manual', verificationStatus: 'unverified',
  githubMetadata: null, metadataFetchedAt: null, benchmark: null, evaluation: null,
};

test('GitHub-sourced facts are shown and labelled as fetched metadata, not analysis', () => {
  const html = renderToString(
    <RepoFacts repo={{
      ...base, sourceType: 'github_api', verificationStatus: 'github_metadata', language: 'Rust', branch: 'trunk',
      commitSha: '0123456789abcdef0123456789abcdef01234567', metadataFetchedAt: '2026-01-02T03:04:05Z',
      githubMetadata: { description: 'A tiny engine', stars: 7, forks: 2, license: 'MIT', pushed_at: '2026-01-01T00:00:00Z' },
    }} />,
  );
  assert.match(html, /Metadata fetched from GitHub/);
  assert.match(html, /Rust/);
  assert.match(html, /0123456789ab/);               // short commit
  assert.match(html, /7 \/ 2/);
  assert.match(html, /the code has not been analysed/i);
});

test('a typed-in repository never shows invented facts', () => {
  const html = renderToString(<RepoFacts repo={base} />);
  assert.match(html, /Typed in: not fetched from GitHub/);
  assert.match(html, /Not reported/);
  assert.match(html, /Not recorded/);
  assert.doesNotMatch(html, /Stars/);
});

test('demo fixtures are labelled and claim no GitHub facts', () => {
  const html = renderToString(<RepoFacts repo={{ ...base, isDemo: true, sourceType: 'demo_fixture', verificationStatus: 'demo_fixture' }} />);
  assert.match(html, /Demo fixture/);
  assert.match(html, /Fixture: no GitHub facts/);
});
