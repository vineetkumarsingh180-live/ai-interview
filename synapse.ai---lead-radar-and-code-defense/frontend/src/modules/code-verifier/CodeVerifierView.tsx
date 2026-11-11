import React, { useState } from 'react';
import { ChevronRight, Github, List } from 'lucide-react';
import { RepoSubmitCard } from './components/RepoSubmitCard';
import { CodeHealthGauge } from './components/CodeHealthGauge';
import { RepoFacts } from './components/RepoFacts';
import { GitHubRepoVerifier } from './components/GitHubRepoVerifier';
import type { RepoEvaluationState } from './hooks/useRepoEvaluation';

interface CodeVerifierViewProps {
  /** Result of `useRepoEvaluation()`, owned by the host so the selection survives tab switches. */
  state: RepoEvaluationState;
  /** Called when the user chooses to continue to the next assessment step. */
  onContinue?: () => void;
}

export const CodeVerifierView: React.FC<CodeVerifierViewProps> = ({ state, onContinue }) => {
  const [activeTab, setActiveTab] = useState<'github-verifier' | 'repo-list'>('github-verifier');

  const {
    repos,
    reposError,
    activeRepo,
    selectedRepoId,
    setSelectedRepoId,
    submitRepo,
    isSubmitting,
    submissionError,
    deleteRepo,
    isDeleting,
    deleteError,
  } = state;

  return (
    <div className="space-y-5">
      {/* View Switcher Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-line pb-3">
        <button
          type="button"
          onClick={() => setActiveTab('github-verifier')}
          className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all ${
            activeTab === 'github-verifier'
              ? 'bg-mocha text-surface shadow-clay'
              : 'bg-surface text-ink hover:bg-canvas-alt border border-line'
          }`}
        >
          <Github className="h-4 w-4" />
          <span>GitHub Repo AI Verifier (Vulgarity, Bug, Advance)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('repo-list')}
          className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold rounded-xl transition-all ${
            activeTab === 'repo-list'
              ? 'bg-mocha text-surface shadow-clay'
              : 'bg-surface text-ink hover:bg-canvas-alt border border-line'
          }`}
        >
          <List className="h-4 w-4" />
          <span>All Submissions ({repos.length})</span>
        </button>
      </div>

      {/* Tab 1: GitHub Repo AI Verifier */}
      {activeTab === 'github-verifier' && (
        <div className="space-y-5">
          <GitHubRepoVerifier />

          <div className="card flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5">
            <div className="min-w-0">
              <span className="eyebrow block">Next step</span>
              <span className="text-sm font-bold text-ink">Ready to defend this repository live in voice interview?</span>
            </div>
            <button type="button" onClick={onContinue} className="btn btn-primary">
              <span>Open Voice Defense</span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Tab 2: Detailed Repo Submissions & Facts */}
      {activeTab === 'repo-list' && (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
          <div className="min-w-0 space-y-5 xl:col-span-5">
            <RepoSubmitCard
              repos={repos}
              selectedRepoId={selectedRepoId}
              onSelectRepo={(id) => setSelectedRepoId(id)}
              onSubmitRepo={submitRepo}
              isSubmitting={isSubmitting}
              onDeleteRepo={deleteRepo}
              isDeleting={isDeleting}
              error={submissionError?.message ?? null}
              deleteError={deleteError?.message ?? null}
              loadError={reposError?.message ?? null}
            />

            <div className="card flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5">
              <div className="min-w-0">
                <span className="eyebrow block">Next step</span>
                <span className="text-sm font-bold text-ink">Continue to Voice Defense</span>
              </div>
              <button type="button" onClick={onContinue} className="btn btn-primary">
                <span>Open Voice Defense</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="min-w-0 space-y-5 xl:col-span-7">
            {activeRepo && (
              <RepoFacts
                repo={activeRepo}
                onDeleteRepo={deleteRepo}
                isDeleting={isDeleting}
              />
            )}
            <CodeHealthGauge
              evaluation={activeRepo?.evaluation}
              benchmark={activeRepo?.benchmark}
              status={activeRepo?.status}
              isDemo={activeRepo?.isDemo}
            />
          </div>
        </div>
      )}
    </div>
  );
};
