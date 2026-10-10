/** Runs the boundary checker on the real tree (React src/), and proves it detects violations. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = path.join(ROOT, 'scripts', 'check-architecture.mjs');
const run = (root: string) => spawnSync(process.execPath, [SCRIPT, '--root', root], { encoding: 'utf8' });

function scratch(files: Record<string, string>) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'arch-'));
  fs.cpSync(path.join(ROOT, 'src'), path.join(dir, 'src'), { recursive: true });
  for (const [rel, content] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(dir, rel)), { recursive: true });
    fs.writeFileSync(path.join(dir, rel), content);
  }
  return dir;
}

test('repository respects module boundaries', () => {
  const res = run(ROOT);
  assert.equal(res.status, 0, res.stderr);
});

const cases: Array<[string, Record<string, string>, string]> = [
  ['cross-module import (frontend)', { 'src/modules/voice-defense/bad.ts': "import { LeaderboardView } from '@modules/leaderboard';\nexport const x = LeaderboardView;\n" }, 'no-cross-module-import'],
  ['relative cross-module import (frontend)', { 'src/modules/voice-defense/bad.ts': "import { useLeaderboard } from '../leaderboard/hooks/useLeaderboard';\nexport const x = useLeaderboard;\n" }, 'no-cross-module-import'],
  ['app importing module internals', { 'src/app/bad.ts': "import { LeadCard } from '@modules/job-lead-radar/components/LeadCard';\nexport const x = LeadCard;\n" }, 'only-public-api'],
  ['shared importing a module', { 'src/shared/bad.ts': "import { LeadRadarView } from '@modules/job-lead-radar';\nexport const x = LeadRadarView;\n" }, 'shared-must-be-independent'],
  ['business logic in shared', { 'src/shared/bad.ts': 'export const scoreCandidate = (n: number) => n * 2;\n' }, 'no-business-logic-in-shared'],
  ['direct fetch in a module', { 'src/modules/leaderboard/bad.ts': "export const load = () => fetch('/api/v1/x');\n" }, 'http-via-shared-client'],
  ['circular import', { 'src/modules/leaderboard/a.ts': "import { b } from './b';\nexport const a = b;\n", 'src/modules/leaderboard/b.ts': "import { a } from './a';\nexport const b = a;\n" }, 'no-circular-imports'],
];
for (const [name, files, rule] of cases) {
  test(`detects: ${name}`, () => {
    const res = run(scratch(files));
    assert.equal(res.status, 1, 'expected a failure');
    assert.ok(res.stderr.includes(rule), res.stderr);
  });
}
