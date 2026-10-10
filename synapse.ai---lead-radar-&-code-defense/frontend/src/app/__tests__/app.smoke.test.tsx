import { test } from 'node:test';
import assert from 'node:assert/strict';
import { renderToString } from 'react-dom/server';
import App from '@app/App';
import { buildNavSections, getBreadcrumb } from '@app/navigation';

test('app shell renders navigation for all four modules and the default module', () => {
  const html = renderToString(<App />);
  for (const label of ['Job Lead Radar', 'Code Verifier', 'Voice Interview', 'Leaderboard']) {
    assert.ok(html.includes(label), label);
  }
  assert.match(html, /Lead radar/);          // default view is the lead radar
  assert.doesNotMatch(html, /Demo data/);     // no static demo claim; live status instead
  assert.match(html, /System status/);
  assert.match(html, /Open navigation menu/); // mobile drawer trigger present
});

test('navigation keeps stable DOM ids and marks exactly one entry active', () => {
  const sections = buildNavSections({ activeTab: 'assessment', activeSubView: 'voice-defense', go: () => {} });
  const entries = sections.flatMap((s) => s.entries);
  assert.deepEqual(entries.map((e) => e.id), ['nav-tab-leads', 'nav-tab-assessment', 'nav-subview-voice', 'nav-subview-leaderboard']);
  assert.deepEqual(entries.filter((e) => e.active).map((e) => e.id), ['nav-subview-voice']);
});

test('breadcrumbs', () => {
  assert.deepEqual(getBreadcrumb('leads', 'radar'), { section: 'Job Lead Radar', page: 'Lead Stream' });
  assert.deepEqual(getBreadcrumb('assessment', 'leaderboard'), { section: 'Assessment Hub', page: 'Leaderboard' });
});
