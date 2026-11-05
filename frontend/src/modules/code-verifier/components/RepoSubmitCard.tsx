import React, { useState } from 'react';
import { GitBranch, Github, Play, Loader2, User, AlertCircle, Trash2 } from 'lucide-react';
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
  onDeleteRepo?: (id: string) => Promise<any>;
  isDeleting?: boolean;
  error?: string | null;
  deleteError?: string | null;
  /** Error from loading the list (shown instead of an empty-state). */
  loadError?: string | null;
}

export const RepoSubmitCard: React.FC<RepoSubmitCardProps> = ({
  repos,
  selectedRepoId,
  onSelectRepo,
  onSubmitRepo,
  isSubmitting,
  onDeleteRepo,
  isDeleting,
  error,
  deleteError,
  loadError,
}) => {
  const [candidateName, setCandidateName] = useState('');
  const [githubHandle, setGithubHandle] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

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
        <span className="eyebrow block">Submissions{loadError ? '' : ` (${repos.length})`}</span>
        {loadError ? (
          <p role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2.5 text-sm text-danger">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{loadError}</span>
          </p>
        ) : deleteError ? (
          <p role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2.5 text-sm text-danger">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{deleteError}</span>
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
                  <div
                    id={`candidate-repo-item-${r.id}`}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isSelected}
                    onClick={() => onSelectRepo(r.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelectRepo(r.id);
                      }
                    }}
                    className={`block w-full cursor-pointer rounded-xl border p-3 text-left transition-colors focus-visible:shadow-focus ${
                      isSelected
                        ? 'border-mocha bg-mocha-tint'
                        : 'border-line-strong bg-surface hover:bg-canvas-alt'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="flex items-start gap-3 min-w-0 flex-1">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-line-strong bg-canvas-alt">
                          {r.candidateAvatarUrl ? (
                            <img src={r.candidateAvatarUrl} alt="" className="h-full w-full object-cover" />
                          ) : (
                            <User className="h-4 w-4 text-mocha" />
                          )}
                        </span>
                        <span className="block min-w-0 flex-1">
                          <span className="block break-words text-sm font-semibold text-ink">{r.candidateName}</span>
                          <span className="block break-all text-xs text-ink-alt">@{r.candidateGithubHandle}</span>
                          <span className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-mocha">
                            <GitBranch className="h-3 w-3 shrink-0" />
                            <span className="min-w-0 break-all">{r.repoName}</span>
                            <span className="text-ink-alt">· {r.language ?? 'language unknown'}</span>
                            {r.isDemo && <span className="badge badge-warm">Demo fixture</span>}
                          </span>
                        </span>
                      </span>

                      {onDeleteRepo && (
                        <button
                          type="button"
                          title="Unsubmit repository"
                          aria-label={`Unsubmit repository ${r.repoName}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmDeleteId((prev) => (prev === r.id ? null : r.id));
                          }}
                          className="rounded-lg p-1.5 text-ink-alt hover:bg-danger-tint hover:text-danger focus-visible:shadow-focus transition-colors shrink-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>

                    {confirmDeleteId === r.id && (
                      <div
                        className="mt-2.5 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2 text-xs text-danger"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span className="font-medium">Unsubmit this repository?</span>
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            disabled={deletingId === r.id || isDeleting}
                            onClick={async (e) => {
                              e.stopPropagation();
                              setDeletingId(r.id);
                              try {
                                await onDeleteRepo?.(r.id);
                              } finally {
                                setDeletingId(null);
                                setConfirmDeleteId(null);
                              }
                            }}
                            className="btn btn-danger min-h-6 py-0.5 px-2 text-xs font-bold"
                          >
                            {deletingId === r.id ? 'Deleting…' : 'Yes, unsubmit'}
                          </button>
                          <button
                            type="button"
                            disabled={deletingId === r.id}
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmDeleteId(null);
                            }}
                            className="btn btn-secondary min-h-6 py-0.5 px-2 text-xs"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    <span className="mt-2 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-t border-line pt-2">
                      <span className="text-sm font-bold tabular-nums text-ink">
                        {score != null ? `${score} / 100` : statusLabel ?? 'Not measured'}
                      </span>
                      <span className="text-xs text-ink-alt">
                        {coverage != null ? `${coverage}% coverage` : 'Coverage not measured'}
                      </span>
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
};
