import React from 'react';
import { ShieldCheck, Mic, Trophy } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { CodeVerifierView, useRepoEvaluation } from '@modules/code-verifier';
import { VoiceDefenseView, useVoiceStream, type VoiceCandidate } from '@modules/voice-defense';
import { LeaderboardView, LEADERBOARD_QUERY_KEY } from '@modules/leaderboard';
import type { SubView } from './navigation';

interface AssessmentWorkspaceProps {
  activeSubView: SubView;
  setActiveSubView: (view: SubView) => void;
}

const SUB_TABS: { id: SubView; domId: string; label: string; icon: typeof ShieldCheck }[] = [
  { id: 'code-verifier', domId: 'subview-tab-code', label: 'Code Verifier', icon: ShieldCheck },
  { id: 'voice-defense', domId: 'subview-tab-voice', label: 'Voice Defense', icon: Mic },
  { id: 'leaderboard', domId: 'subview-tab-leaderboard', label: 'Leaderboard', icon: Trophy },
];

/**
 * Composes the three assessment modules. This is the only place that connects them:
 *  - Code Verifier's selected repository becomes Voice Defense's candidate (via the narrow
 *    `VoiceCandidate` shape, never by importing Code Verifier types into Voice Defense).
 *  - A finished voice turn invalidates the Leaderboard's query (via its exported key).
 */
export const AssessmentWorkspace: React.FC<AssessmentWorkspaceProps> = ({ activeSubView, setActiveSubView }) => {
  const queryClient = useQueryClient();
  const repoState = useRepoEvaluation();
  const { activeRepo } = repoState;

  const candidate: VoiceCandidate | null = activeRepo
    ? {
        id: activeRepo.id,
        name: activeRepo.candidateName,
        repoName: activeRepo.repoName,
        targetRole: activeRepo.targetRole,
        commitSha: activeRepo.commitSha,
      }
    : null;

  const voiceSession = useVoiceStream(candidate?.name, candidate?.id, {
    onTurnCompleted: () => queryClient.invalidateQueries({ queryKey: LEADERBOARD_QUERY_KEY }),
  });

  return (
    <div className="space-y-5">
      {/* Sub-view switcher */}
      <div className="card flex flex-col gap-3 p-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="grid grid-cols-3 gap-2 sm:flex" role="tablist" aria-label="Assessment sections">
          {SUB_TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                id={tab.domId}
                type="button"
                role="tab"
                aria-selected={activeSubView === tab.id}
                aria-pressed={activeSubView === tab.id}
                onClick={() => setActiveSubView(tab.id)}
                className="chip min-w-0 justify-center px-2 text-center text-xs leading-tight sm:px-3.5 sm:text-[0.8125rem]"
              >
                <Icon className="hidden h-3.5 w-3.5 shrink-0 sm:block" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <div className="flex min-w-0 items-start gap-2 text-sm xl:max-w-[26rem] xl:items-center">
          <span className="shrink-0 py-1 text-ink-soft">Candidate</span>
          <span className="min-w-0 break-words rounded-lg border border-line-strong bg-canvas-alt px-3 py-1 font-semibold text-ink">
            {candidate ? `${candidate.name} (${candidate.repoName})` : 'None selected'}
          </span>
        </div>
      </div>

      {activeSubView === 'code-verifier' && (
        <CodeVerifierView state={repoState} onContinue={() => setActiveSubView('voice-defense')} />
      )}
      {activeSubView === 'voice-defense' && <VoiceDefenseView session={voiceSession} candidate={candidate} />}
      {activeSubView === 'leaderboard' && <LeaderboardView />}
    </div>
  );
};
