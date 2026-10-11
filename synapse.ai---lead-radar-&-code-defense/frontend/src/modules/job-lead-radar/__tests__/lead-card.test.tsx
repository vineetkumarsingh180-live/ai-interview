import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToString } from 'react-dom/server';
import { LeadCard } from '../components/LeadCard';
import type { JobLead } from '../types';

const lead: JobLead = {
  id: 'l1', rawPostId: 'p1', roleTitle: 'Rust Engineer', companyName: 'Acme', companyStage: null, compMin: null, compMax: null,
  compCurrency: null, equityNote: null, techStack: ['Rust'], locationMode: null, clearanceRequired: null, isHiring: true,
  matchScore: null, urgencyTier: null, contactAnchor: null, enrichmentMetadata: {}, entrySource: 'operator_entered',
  isDemo: false, createdAt: '2026-01-01T00:00:00Z',
  rawPost: {
    id: 'p1', platform: 'reddit', externalId: 'x', authorHandle: 'u/a', authorName: 'A', rawContent: 'Acme hires', sourceChannel: 'Manual import',
    ingestedAt: '2026-01-01T00:00:00Z', isProcessed: true, sourceType: 'manual_text', verificationStatus: 'unverified',
    sourceUrl: 'https://example.com/post/1', postedAt: null, isDemo: false,
  },
};

test('user-provided leads are labelled unverified and show how their fields were produced', () => {
  const html = renderToString(<LeadCard lead={lead} onDraftOutreach={() => {}} />);
  assert.match(html, /User-provided, unverified/);
  assert.match(html, /Fields entered by hand/);
  assert.match(html, /Match not measured/);
  assert.match(html, /Compensation not stated/);
  assert.match(html, /href="https:\/\/example\.com\/post\/1"/);
  assert.match(html, /noopener noreferrer/);
  assert.doesNotMatch(html, /Demo fixture/);
});

test('a javascript: source url is never rendered as a link', () => {
  const evil = { ...lead, rawPost: { ...lead.rawPost!, sourceUrl: 'javascript:alert(1)' } };
  assert.doesNotMatch(renderToString(<LeadCard lead={evil} onDraftOutreach={() => {}} />), /javascript:/);
});

test('demo fixtures are visibly labelled', () => {
  const html = renderToString(<LeadCard lead={{ ...lead, isDemo: true, entrySource: 'demo_fixture' }} onDraftOutreach={() => {}} />);
  assert.match(html, /Demo fixture/);
  assert.match(html, /Fixture fields/);
});
