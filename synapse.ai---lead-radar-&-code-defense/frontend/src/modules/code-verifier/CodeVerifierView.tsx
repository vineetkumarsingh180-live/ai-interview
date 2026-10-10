import React from 'react';
import { ChevronRight } from 'lucide-react';
import { RepoSubmitCard } from './components/RepoSubmitCard';
import { CodeHealthGauge } from './components/CodeHealthGauge';
import type { RepoEvaluationState } from './hooks/useRepoEvaluation';

interface CodeVerifierViewProps {
  /** Result of `useRepoEvaluation()`, owned by the host so the selection survives tab switches. */
  state: RepoEvaluationState;
  /** Called when the user chooses to continue to the next assessment step. */
  onContinue?: () => void;
}

export const CodeVerifierView: React.FC<CodeVerifierViewProps> = ({ state, onContinue }) => {
  const { repos, reposError, activeRepo, selectedRepoId, setSelectedRepoId, submitRepo, isSubmitting, submissionError } = state;

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
      <div className="min-w-0 space-y-5 xl:col-span-5">
        <RepoSubmitCard
          repos={repos}
          selectedRepoId={selectedRepoId}
          onSelectRepo={(id) => setSelectedRepoId(id)}
          onSubmitRepo={submitRepo}
          isSubmitting={isSubmitting}
          error={submissionError?.message ?? null}
          loadError={reposError?.message ?? null}
        />

        <div className="card flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5">
          <div className="min-w-0">
            <span className="eyebrow block">Next step</span>
            <span className="text-sm font-bold text-ink">Continue to voice interview</span>
          </div>
          <button type="button" onClick={onContinue} className="btn btn-primary">
            <span>Open voice defense</span>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="min-w-0 xl:col-span-7">
        <CodeHealthGauge
          evaluation={activeRepo?.evaluation}
          benchmark={activeRepo?.benchmark}
          status={activeRepo?.status}
          isDemo={activeRepo?.isDemo}
        />
      </div>
    </div>
  );
};
