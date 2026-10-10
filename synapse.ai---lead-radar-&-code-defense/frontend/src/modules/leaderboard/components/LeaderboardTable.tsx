import React from 'react';
import { Trophy, GitBranch, User, Info, AlertCircle } from 'lucide-react';
import type { LeaderboardItem } from '../types';

interface LeaderboardTableProps {
  leaderboard: LeaderboardItem[];
  isLoading: boolean;
  error?: string | null;
  onRetry?: () => void;
}

const NOT_SCORED = 'Not scored';

const statusLabel = (tag: string) =>
  tag === 'needs_human_review' ? 'Needs human review' : tag.replace(/_/g, ' ');

const fmt = (value: number | null, suffix = '') => (value != null ? `${value.toFixed(1)}${suffix}` : NOT_SCORED);

const Avatar: React.FC<{ item: LeaderboardItem }> = ({ item }) => (
  <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-line-strong bg-canvas-alt">
    {item.candidateAvatarUrl ? (
      <img src={item.candidateAvatarUrl} alt="" className="h-full w-full object-cover" />
    ) : (
      <User className="h-4 w-4 text-mocha" />
    )}
  </span>
);

export const LeaderboardTable: React.FC<LeaderboardTableProps> = ({ leaderboard, isLoading, error, onRetry }) => {
  return (
    <section id="live-assessment-leaderboard-card" className="card space-y-4 p-4 sm:p-6" aria-label="Assessment results">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-canvas-alt text-mocha">
            <Trophy className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-base font-bold leading-tight text-ink">Assessment leaderboard</h3>
            <p className="text-sm text-ink-soft">Interviewed candidates and their review status.</p>
          </div>
        </div>
      </div>

      <p className="flex items-start gap-2 rounded-xl border border-line-strong bg-canvas-alt p-3 text-sm text-ink">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-warm" aria-hidden="true" />
        <span>
          Interviews are not scored automatically, so candidates are listed by recency, not rank. A value appears
          only when someone or something actually measured it. Nothing here is a hiring recommendation.
        </span>
      </p>

      {error ? (
        <div className="well p-6 text-center" role="alert">
          <AlertCircle className="mx-auto mb-2 h-6 w-6 text-danger" />
          <p className="text-sm text-danger">{error}</p>
          {onRetry && (
            <button type="button" onClick={onRetry} className="btn btn-secondary mt-3">
              Try again
            </button>
          )}
        </div>
      ) : isLoading ? (
        <div className="space-y-2" aria-busy="true" aria-label="Loading results">
          {[1, 2, 3].map((n) => (
            <div key={n} className="h-14 animate-pulse rounded-xl bg-canvas-alt" />
          ))}
        </div>
      ) : leaderboard.length === 0 ? (
        <p className="well p-6 text-center text-sm text-ink-alt">
          No interviews recorded yet. Results appear here after a candidate answers in Voice Defense.
        </p>
      ) : (
        <>
          {/* Small screens: one card per candidate, nothing hidden or clipped */}
          <ul className="space-y-3 md:hidden">
            {leaderboard.map((item) => (
              <li key={item.id} className="well space-y-3 p-3">
                <div className="flex items-center gap-3">
                  <Avatar item={item} />
                  <div className="min-w-0">
                    <span className="block truncate text-sm font-bold text-ink">{item.candidateName}</span>
                    <span className="block break-words text-xs text-ink-alt">
                      {[item.candidateHandle && `@${item.candidateHandle}`, item.targetRole].filter(Boolean).join(' • ') || 'No profile details'}
                    </span>
                  </div>
                </div>
                <p className="flex min-w-0 items-center gap-1.5 text-xs text-mocha">
                  <GitBranch className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{item.repoName ?? 'No repository linked'}</span>
                </p>
                <dl className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-lg bg-surface p-2">
                    <dt className="text-ink-soft">Code health</dt>
                    <dd className="font-bold tabular-nums text-ink">{fmt(item.codeHealthScore)}</dd>
                  </div>
                  <div className="rounded-lg bg-surface p-2">
                    <dt className="text-ink-soft">Interview score</dt>
                    <dd className="font-bold tabular-nums text-ink">{fmt(item.voiceDefenseScore)}</dd>
                  </div>
                  <div className="col-span-2 rounded-lg bg-surface p-2">
                    <dt className="text-ink-soft">Status</dt>
                    <dd className="font-semibold text-ink">{statusLabel(item.statusTag)}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>

          {/* md and up: table that scrolls inside its own container */}
          <div className="hidden overflow-x-auto rounded-xl border border-line md:block" tabIndex={0} aria-label="Results table, scrollable">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-canvas-alt text-xs uppercase tracking-wider text-ink-alt">
                  <th scope="col" className="px-3 py-3">Candidate &amp; role</th>
                  <th scope="col" className="px-3 py-3">Repo</th>
                  <th scope="col" className="px-3 py-3 text-right">Code health</th>
                  <th scope="col" className="px-3 py-3 text-right">Interview score</th>
                  <th scope="col" className="px-3 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {leaderboard.map((item) => (
                  <tr key={item.id} className="transition-colors hover:bg-mocha-tint">
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2.5">
                        <Avatar item={item} />
                        <div className="min-w-0">
                          <span className="block font-bold text-ink">{item.candidateName}</span>
                          <span className="block text-xs text-ink-alt">
                            {[item.candidateHandle && `@${item.candidateHandle}`, item.targetRole].filter(Boolean).join(' • ') || 'No profile details'}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-mocha">
                      <span className="inline-flex items-center gap-1.5">
                        <GitBranch className="h-3.5 w-3.5 text-ink-alt" />
                        {item.repoName ?? <span className="text-ink-alt">No repository</span>}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-ink">{fmt(item.codeHealthScore)}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-right tabular-nums text-ink">{fmt(item.voiceDefenseScore)}</td>
                    <td className="px-3 py-3">
                      <span className="badge badge-warm">{statusLabel(item.statusTag)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
};
