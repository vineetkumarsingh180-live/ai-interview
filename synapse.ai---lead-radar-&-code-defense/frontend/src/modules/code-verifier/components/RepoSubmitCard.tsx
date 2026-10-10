import React, { useState } from 'react';
import { GitBranch, Github, Play, Loader2, User, AlertCircle } from 'lucide-react';
import { CandidateRepo } from '../types';

interface RepoSubmitCardProps {
  repos: CandidateRepo[];
  selectedRepoId: string | null;
  onSelectRepo: (id: string) => void;
  onSubmitRepo: (payload: {
    candidateName: string;
    candidateGithubHandle: string;
    repoUrl: string;
    targetRole?: string;
  }) => Promise<any>;
  isSubmitting: boolean;
  error?: string | null;
  /** Error from loading the list (shown instead of an empty-state). */
  loadError?: string | null;
}

export const RepoSubmitCard: React.FC<RepoSubmitCardProps> = ({
  repos,
  selectedRepoId,
  onSelectRepo,
  onSubmitRepo,
  isSubmitting,
  error,
  loadError,
}) => {
  const [candidateName, setCandidateName] = useState('');
  const [githubHandle, setGithubHandle] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [showSubmitForm, setShowSubmitForm] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidateName || !repoUrl) return;
    try {
      await onSubmitRepo({
        candidateName,
        candidateGithubHandle: githubHandle || 'candidate',
        repoUrl,
        targetRole,
      });
      setShowSubmitForm(false);
    } catch {
      // The error is surfaced through the `error` prop; keep the form open.
    }
  };

  return (
    <section id="repo-submit-card" className="card space-y-4 p-4 sm:p-5" aria-label="Candidate repositories">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-canvas-alt text-mocha">
            <Github className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-base font-bold leading-tight text-ink">Candidate repositories</h3>
            <p className="text-sm text-ink-soft">Submit a repo and review its assessment.</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowSubmitForm(!showSubmitForm)}
          className="btn btn-secondary"
          aria-expanded={showSubmitForm}
        >
          {showSubmitForm ? 'Hide form' : '+ New submission'}
        </button>
      </div>

      {showSubmitForm && (
        <form onSubmit={handleSubmit} className="well space-y-3 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="repo-candidate-name" className="field-label">
                Candidate full name
              </label>
              <input
                id="repo-candidate-name"
                type="text"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                className="field"
                required
              />
            </div>
            <div>
              <label htmlFor="repo-github-handle" className="field-label">
                GitHub username
              </label>
              <input
                id="repo-github-handle"
                type="text"
                value={githubHandle}
                onChange={(e) => setGithubHandle(e.target.value)}
                className="field"
                required
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="repo-url" className="field-label">
                Public GitHub repository URL
              </label>
              <input
                id="repo-url"
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/org/repo"
                className="field"
                required
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="repo-target-role" className="field-label">
                Target role (optional)
              </label>
              <input
                id="repo-target-role"
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g. Backend engineer"
                className="field"
              />
            </div>
          </div>

          {error && (
            <p role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2.5 text-sm text-danger">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          <button type="submit" disabled={isSubmitting} className="btn btn-primary w-full">
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Submitting…</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                <span>Submit for assessment</span>
              </>
            )}
          </button>
        </form>
      )}

      <div className="space-y-2">
        <span className="eyebrow block">Submissions ({repos.length})</span>
        {loadError ? (
          <p role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2.5 text-sm text-danger">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{loadError}</span>
          </p>
        ) : repos.length === 0 ? (
          <p className="well p-4 text-sm text-ink-alt">No repositories submitted yet.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-2">
            {repos.map((r) => {
              const isSelected = selectedRepoId === r.id || (!selectedRepoId && r === repos[0]);
              const score = r.evaluation?.compositeHealthScore ?? null;
              const coverage = r.benchmark?.testCoveragePct ?? null;
              const statusLabel =
                r.status === 'awaiting_analysis' ? 'Awaiting analysis' : r.status === 'failed' ? 'Analysis failed' : null;
              return (
                <li key={r.id}>
                  <button
                    id={`candidate-repo-item-${r.id}`}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => onSelectRepo(r.id)}
                    className={`flex w-full cursor-pointer items-center justify-between gap-3 rounded-xl border p-3 text-left transition-colors focus-visible:shadow-focus ${
                      isSelected
                        ? 'border-mocha bg-mocha-tint'
                        : 'border-line-strong bg-surface hover:bg-canvas-alt'
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-line-strong bg-canvas-alt">
                        {r.candidateAvatarUrl ? (
                          <img src={r.candidateAvatarUrl} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <User className="h-4 w-4 text-mocha" />
                        )}
                      </span>
                      <div className="min-w-0">
                        <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
                          <span className="truncate text-sm font-semibold text-ink">{r.candidateName}</span>
                          <span className={`truncate text-xs text-ink-alt`}>@{r.candidateGithubHandle}</span>
                        </div>
                        <p className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-mocha">
                          <GitBranch className="h-3 w-3 shrink-0" />
                          <span className="truncate">{r.repoName}</span>
                          <span className="shrink-0 text-ink-alt">· {r.language ?? 'language unknown'}</span>
                          {r.isDemo && <span className="badge badge-warm shrink-0">Demo fixture</span>}
                        </p>
                      </div>
                    </div>

                    <div className="shrink-0 text-right">
                      <div className="text-sm font-bold tabular-nums text-ink">
                        {score != null ? `${score} / 100` : statusLabel ?? 'Not measured'}
                      </div>
                      <span className={`block text-xs text-ink-alt`}>
                        {coverage != null ? `${coverage}% coverage` : 'Coverage not measured'}
                      </span>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
};
