#!/usr/bin/env node
/**
 * Architecture boundary check for the React/TypeScript code in `src/`.
 * Dependency-free. Exit code 1 when a rule is violated.
 *
 * Layering (arrows = "may import"):
 *   app/ ──▶ modules/<name> (public index only) ──▶ shared/
 *   modules/<a> ──✗──▶ modules/<b>        shared/ ──✗──▶ modules/, app/
 *
 * Usage: node scripts/check-architecture.mjs [--root <dir>]
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const argRoot = process.argv.indexOf('--root');
const ROOT = argRoot > -1 ? path.resolve(process.argv[argRoot + 1]) : path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// Words that signal module business logic. They must not appear in identifiers or imports inside shared/.
const DOMAIN_WORDS = /\b\w*(lead|repo|repository|voice|interview|leaderboard|candidate|outreach|ingest|ingestion|verdict)\w*\b/i;

const violations = [];
const report = (rule, file, detail) => violations.push({ rule, file: path.relative(ROOT, file), detail });

function listFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== 'node_modules' && e.name !== '__tests__') out.push(...listFiles(p)); }
    else if (/\.(ts|tsx)$/.test(e.name) && !/\.test\.(ts|tsx)$/.test(e.name)) out.push(p);
  }
  return out;
}

function importsOf(text) {
  const re = /(?:^|\n)\s*(?:import|export)\s+(?:type\s+)?(?:[^'"\n;]*?\sfrom\s+)?['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)/g;
  const out = []; let m;
  while ((m = re.exec(text))) out.push(m[1] || m[2]);
  return out;
}

const stripNoise = (t) =>
  t.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/.*$/gm, '$1')
   .replace(/`(?:\\.|[^`\\])*`/g, '``').replace(/'(?:\\.|[^'\\\n])*'/g, "''").replace(/"(?:\\.|[^"\\\n])*"/g, '""');

// ---- one "area" = a source tree with the same layering rules -----------------------------------
function checkArea({ name, base, alias }) {
  // base: directory containing app|modules|shared (src/ or server/)
  const files = listFiles(base);
  const layerOf = (file) => {
    const rel = path.relative(base, file).split(path.sep);
    if (rel[0] === 'modules') return { layer: 'module', module: rel[1] };
    if (rel[0] === 'shared') return { layer: 'shared' };
    if (rel[0] === 'app' || rel.length === 1) return { layer: 'app' };   // app/ or entry files at the root (main.tsx)
    return { layer: 'other' };
  };
  const resolveSpec = (from, spec) => {
    let target = null;
    if (spec.startsWith('.')) target = path.resolve(path.dirname(from), spec);
    else if (alias) {
      for (const [prefix, dir] of Object.entries(alias)) {
        if (spec === prefix || spec.startsWith(prefix + '/')) { target = path.join(dir, spec.slice(prefix.length)); break; }
      }
    }
    if (!target) return null;           // third-party / node built-in
    for (const cand of [target, target + '.ts', target + '.tsx', path.join(target, 'index.ts'), path.join(target, 'index.tsx')]) {
      if (fs.existsSync(cand) && fs.statSync(cand).isFile()) return cand;
    }
    return target;                      // unresolved: still useful for layer checks
  };

  const graph = new Map();
  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8');
    const me = layerOf(file);
    const deps = [];
    for (const spec of importsOf(text)) {
      const target = resolveSpec(file, spec);
      if (!target) continue;
      const t = layerOf(target);
      const inside = target.startsWith(base + path.sep);
      if (!inside) continue;
      deps.push(target);

      if (me.layer === 'shared') {
        if (t.layer !== 'shared') report('shared-must-be-independent', file, `shared/ imports ${path.relative(base, target)} (${t.layer})`);
      } else if (me.layer === 'module') {
        if (t.layer === 'app') report('modules-must-not-import-app', file, `imports ${path.relative(base, target)}`);
        if (t.layer === 'module' && t.module !== me.module) {
          report('no-cross-module-import', file, `module "${me.module}" imports module "${t.module}" via "${spec}" (use composition in app/ with a narrow interface)`);
        }
      } else if (me.layer === 'app') {
        if (t.layer === 'module') {
          const rel = path.relative(path.join(base, 'modules', t.module), target).replace(/\\/g, '/');
          if (!/^index\.(ts|tsx)$/.test(rel) && rel !== '') {
            report('only-public-api', file, `imports module internals "${spec}"; import "${t.module}" via its index`);
          }
        }
      }
    }
    graph.set(file, deps);

    // shared must not contain domain logic
    if (me.layer === 'shared') {
      const code = stripNoise(text);
      const m = code.match(DOMAIN_WORDS);
      if (m) report('no-business-logic-in-shared', file, `domain term "${m[0]}" found in shared code`);
    }
    // all HTTP calls go through shared/api/client (frontend only)
    if (name === 'frontend' && /\bfetch\s*\(/.test(stripNoise(text)) && !/shared[\\/]api[\\/]client\.ts$/.test(file)) {
      report('http-via-shared-client', file, 'direct fetch(); use requestJson from @shared/api/client inside the module api.ts');
    }
  }

  // cycles (DFS)
  const color = new Map(); const stack = [];
  const dfs = (n) => {
    color.set(n, 1); stack.push(n);
    for (const d of graph.get(n) || []) {
      if (!graph.has(d)) continue;
      if (color.get(d) === 1) {
        const cyc = stack.slice(stack.indexOf(d)).concat(d).map((f) => path.relative(base, f)).join(' -> ');
        report('no-circular-imports', n, cyc);
      } else if (!color.get(d)) dfs(d);
    }
    stack.pop(); color.set(n, 2);
  };
  for (const f of graph.keys()) if (!color.get(f)) dfs(f);
  return files.length;
}

const areas = [];
const srcDir = path.join(ROOT, 'src');
if (fs.existsSync(srcDir)) {
  areas.push({
    name: 'frontend', base: srcDir,
    alias: { '@shared': path.join(srcDir, 'shared'), '@modules': path.join(srcDir, 'modules'), '@app': path.join(srcDir, 'app') },
  });
}
let total = 0;
for (const a of areas) total += checkArea(a);

if (violations.length) {
  console.error(`Architecture check FAILED (${violations.length} violation${violations.length > 1 ? 's' : ''}):`);
  for (const v of violations) console.error(`  [${v.rule}] ${v.file}: ${v.detail}`);
  process.exit(1);
}
console.log(`Architecture check passed: ${total} files in ${areas.map((a) => a.name).join(' + ')}; no boundary, cycle or shared-logic violations.`);
