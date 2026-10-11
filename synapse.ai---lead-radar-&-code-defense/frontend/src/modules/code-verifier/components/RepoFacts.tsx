import React from 'react';
import { Github, ExternalLink } from 'lucide-react';
import type { CandidateRepo } from '../types';

const fmtDate = (iso?: string | null) => {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d.toLocaleString();
};

/**
 * Facts about the selected repository, shown only for what is actually known. Metadata that came
 * from GitHub is labelled as such; typed-in or fixture rows show their provenance instead.
 */
export const RepoFacts: React.FC<{ repo: CandidateRepo }> = ({ repo }) => {
  const meta = repo.githubMetadata ?? null;
  const fromGithub = repo.sourceType === 'github_api' && meta !== null;
  const rows: Array<[string, React.ReactNode]> = [
    ['Language', repo.language ?? 'Not reported'],
    ['Default branch', repo.branch ?? 'Not recorded'],
    ['Head commit', repo.commitSha ? <code className="font-mono text-xs">{repo.commitSha.slice(0, 12)}</code> : 'Not recorded'],
  ];
  if (meta) {
    rows.push(['Stars / forks', `${meta.stars ?? 0} / ${meta.forks ?? 0}`]);
    rows.push(['Last pushed', fmtDate(meta.pushed_at) ?? 'Not reported']);
    rows.push(['License', meta.license ?? 'None reported']);
  }

  return (
    <section className="card space-y-3 p-4 sm:p-5" aria-label="Repository facts">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Github className="mt-0.5 h-4 w-4 shrink-0 text-mocha" aria-hidden="true" />
          <h3 className="min-w-0 break-all text-sm font-bold text-ink">{repo.repoName}</h3>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {repo.isDemo && <span className="badge badge-warm">Demo fixture</span>}
          <span className="badge badge-neutral">
            {fromGithub
              ? 'Metadata fetched from GitHub'
              : repo.sourceType === 'demo_fixture'
              ? meta
                ? 'Demo values: not fetched from GitHub'
                : 'Fixture: no GitHub facts'
              : 'Typed in: not fetched from GitHub'}
          </span>
        </div>
      </div>

      {meta?.description && <p className="break-words text-sm text-ink">{meta.description}</p>}

      {meta?.topics && meta.topics.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label="Topics">
          {meta.topics.map((t) => (
            <li key={t} className="badge badge-neutral">{t}</li>
          ))}
        </ul>
      )}

      <dl className="grid grid-cols-1 gap-x-4 gap-y-1.5 text-sm sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3 border-b border-line py-1">
            <dt className="text-ink-alt">{label}</dt>
            <dd className="min-w-0 break-words text-right font-medium text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      {fromGithub && repo.metadataFetchedAt && (
        <p className="text-xs text-ink-soft">
          Fetched {fmtDate(repo.metadataFetchedAt)}. Metadata only: the code has not been analysed.
        </p>
      )}
      {/^https:\/\/github\.com\//.test(repo.repoUrl) && (
        <a
          href={repo.repoUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-8 items-center gap-1 text-xs font-medium text-mocha underline underline-offset-2"
        >
          Open on GitHub <ExternalLink className="h-3 w-3" aria-hidden="true" />
        </a>
      )}
    </section>
  );
};
