import React, { useState } from 'react';
import { ShieldCheck, Mic, Trophy, Sparkles, ChevronRight, Play } from 'lucide-react';
import { useRepoEvaluation } from './feature1-code-verifier/hooks/useRepoEvaluation';
import { RepoSubmitCard } from './feature1-code-verifier/components/RepoSubmitCard';
import { CodeHealthGauge } from './feature1-code-verifier/components/CodeHealthGauge';
import { useVoiceStream } from './feature2-voice-interview/hooks/useVoiceStream';
import { VoiceOrb } from './feature2-voice-interview/components/VoiceOrb';
import { LiveTranscript } from './feature2-voice-interview/components/LiveTranscript';
import { useLeaderboard } from './feature2-voice-interview/hooks/useLeaderboard';
import { LeaderboardTable } from './feature2-voice-interview/components/LeaderboardTable';
import { SubView } from '../components/LeftNavbar';

interface AssessmentViewProps {
  activeSubView: SubView;
  setActiveSubView: (view: SubView) => void;
}

export const AssessmentView: React.FC<AssessmentViewProps> = ({
  activeSubView,
  setActiveSubView,
}) => {
  const {
    repos,
    activeRepo,
    selectedRepoId,
    setSelectedRepoId,
    submitRepo,
    isSubmitting,
  } = useRepoEvaluation();

  const candidateName = activeRepo?.candidateName || 'Alex Vance';
  const repoName = activeRepo?.repoName || 'distributed-raft-kv';

  const {
    isSessionActive,
    startSession,
    endSession,
    isListening,
    toggleListening,
    isAiSpeaking,
    userSpeechInput,
    setUserSpeechInput,
    submitCandidateTurn,
    compositeScore,
    verdict,
    audioLevel,
    transcript,
  } = useVoiceStream(candidateName, activeRepo?.id);

  const { leaderboard, isLoading: isLoadingLeaderboard } = useLeaderboard();

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Sub-view switcher tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3 rounded-2xl clay border border-slate-800/60">
        <div className="flex flex-wrap items-center gap-2">
          <button
            id="subview-tab-code"
            onClick={() => setActiveSubView('code-verifier')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-semibold transition-all border cursor-pointer ${
              activeSubView === 'code-verifier'
                ? 'bg-slate-800 text-cyan-400 border-cyan-400/40 shadow-[0_0_12px_rgba(34,211,238,0.25)]'
                : 'bg-slate-900/60 backdrop-blur-md text-slate-400 border-slate-800/60 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>1. Code Verifier &amp; AST</span>
          </button>

          <button
            id="subview-tab-voice"
            onClick={() => setActiveSubView('voice-defense')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-semibold transition-all border cursor-pointer ${
              activeSubView === 'voice-defense'
                ? 'bg-slate-800 text-cyan-400 border-cyan-400/40 shadow-[0_0_12px_rgba(34,211,238,0.25)]'
                : 'bg-slate-900/60 backdrop-blur-md text-slate-400 border-slate-800/60 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Mic className="w-3.5 h-3.5 text-cyan-400" />
            <span>2. Live Voice Defense</span>
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
          </button>

          <button
            id="subview-tab-leaderboard"
            onClick={() => setActiveSubView('leaderboard')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-mono font-semibold transition-all border cursor-pointer ${
              activeSubView === 'leaderboard'
                ? 'bg-slate-800 text-cyan-400 border-cyan-400/40 shadow-[0_0_12px_rgba(34,211,238,0.25)]'
                : 'bg-slate-900/60 backdrop-blur-md text-slate-400 border-slate-800/60 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Trophy className="w-3.5 h-3.5 text-amber-400" />
            <span>3. Live Leaderboard</span>
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-2 font-mono text-xs text-slate-300">
          <span className="text-slate-400">Candidate Target:</span>
          <span className="px-3 py-1 rounded-xl bg-slate-900/80 border border-slate-700/50 text-white font-bold">
            {candidateName} ({repoName})
          </span>
        </div>
      </div>

      {/* Sub-view 1: Code Verifier */}
      {activeSubView === 'code-verifier' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 space-y-6">
            <RepoSubmitCard
              repos={repos}
              selectedRepoId={selectedRepoId}
              onSelectRepo={(id) => setSelectedRepoId(id)}
              onSubmitRepo={submitRepo}
              isSubmitting={isSubmitting}
            />

            <div className="p-5 rounded-2xl clay border border-slate-800/60 flex items-center justify-between">
              <div>
                <span className="text-xs font-mono text-cyan-400 block">
                  Step 2 Unlocked:
                </span>
                <span className="text-sm font-bold text-white">
                  Proceed to Voice Interrogation
                </span>
              </div>
              <button
                onClick={() => setActiveSubView('voice-defense')}
                className="flex items-center gap-2 px-4 py-2 rounded-xl btn-secondary-clay text-xs font-bold cursor-pointer"
              >
                <span>Launch Voice Defense</span>
                <ChevronRight className="w-4 h-4 text-slate-950" />
              </button>
            </div>
          </div>

          <div className="lg:col-span-7">
            <CodeHealthGauge
              evaluation={activeRepo?.evaluation}
              benchmark={activeRepo?.benchmark}
              candidateName={candidateName}
              repoName={repoName}
            />
          </div>
        </div>
      )}

      {/* Sub-view 2: Live AI Voice Defense */}
      {activeSubView === 'voice-defense' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 space-y-6">
            <VoiceOrb
              isSessionActive={isSessionActive}
              isListening={isListening}
              isAiSpeaking={isAiSpeaking}
              audioLevel={audioLevel}
              onToggleListening={toggleListening}
              onStartSession={startSession}
              onEndSession={endSession}
              compositeScore={compositeScore}
              verdict={verdict}
            />

            {/* Candidate Context Pill Box */}
            <div className="p-4 rounded-xl inset-well border border-slate-800/60 font-mono text-xs text-slate-300 space-y-1.5">
              <div className="flex items-center justify-between text-slate-400">
                <span>Interrogating Defense Subject:</span>
                <span className="text-cyan-400 font-bold">Active AST Verified</span>
              </div>
              <p className="text-sm font-bold text-white">
                {candidateName} • {activeRepo?.targetRole || 'Staff Distributed Systems Engineer'}
              </p>
              <p className="text-[11px] text-violet-400">
                Repo: {repoName} (Commit: {activeRepo?.commitSha || 'd81a9f4'})
              </p>
            </div>
          </div>

          <div className="lg:col-span-7">
            <LiveTranscript
              transcript={transcript}
              candidateName={candidateName}
              userSpeechInput={userSpeechInput}
              onChangeUserSpeech={setUserSpeechInput}
              onSubmitTurn={submitCandidateTurn}
              isSessionActive={isSessionActive}
              compositeScore={compositeScore}
              verdict={verdict}
            />
          </div>
        </div>
      )}

      {/* Sub-view 3: Leaderboard */}
      {activeSubView === 'leaderboard' && (
        <LeaderboardTable
          leaderboard={leaderboard}
          isLoading={isLoadingLeaderboard}
        />
      )}
    </div>
  );
};
