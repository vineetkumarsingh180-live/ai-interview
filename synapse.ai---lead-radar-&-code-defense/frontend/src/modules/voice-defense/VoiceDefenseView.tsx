import React, { useState, useEffect } from 'react';
import { VoiceOrb } from './components/VoiceOrb';
import { LiveTranscript } from './components/LiveTranscript';
import { ResumeUploadModal } from './components/ResumeUploadModal';
import { ScorecardModal } from './components/ScorecardModal';
import type { VoiceInterviewState } from './hooks/useVoiceStream';
import type { VoiceCandidate } from './types';

interface VoiceDefenseViewProps {
  /** Result of `useVoiceStream()`, owned by the host so the session survives tab switches. */
  session: VoiceInterviewState;
  /** Who is being interviewed. `null` when the host has no candidate selected. */
  candidate: VoiceCandidate | null;
}

export const VoiceDefenseView: React.FC<VoiceDefenseViewProps> = ({ session, candidate }) => {
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);
  const [isScorecardOpen, setIsScorecardOpen] = useState(false);

  const hasAnswered = session.transcript.some((t) => t.speaker === 'candidate');

  // Automatically open the scorecard when evaluation completes
  useEffect(() => {
    if (session.evaluationResult) {
      setIsScorecardOpen(true);
    }
  }, [session.evaluationResult]);

  const handleStartFromModal = (params: { resumeText: string; geminiApiKey1?: string }) => {
    setIsResumeModalOpen(false);
    session.startSession(params);
  };

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-12">
      <div className="min-w-0 space-y-5 xl:col-span-5">
        <VoiceOrb
          isSessionActive={session.isSessionActive}
          isStarting={session.isStarting}
          isListening={session.isListening}
          isAiSpeaking={session.isAiSpeaking}
          audioLevel={session.audioLevel}
          canListen={session.canListen}
          onToggleListening={session.toggleListening}
          onStartSession={() => setIsResumeModalOpen(true)}
          onEndSession={session.endSession}
          hasAnswered={hasAnswered}
        />

        <div className="well space-y-1.5 p-4 text-sm">
          <span className="eyebrow block">Interview subject</span>
          <p className="break-words font-bold text-ink">
            {candidate?.name ?? 'No candidate selected'}
            {candidate?.targetRole ? ` • ${candidate.targetRole}` : ''}
          </p>
          {candidate?.repoName && (
            <p className="break-words text-xs text-ink-alt">
              Repo: {candidate.repoName}
              {candidate.commitSha ? ` (commit ${candidate.commitSha})` : ''}
            </p>
          )}
        </div>
      </div>

      <div className="min-w-0 xl:col-span-7">
        <LiveTranscript
          transcript={session.transcript}
          candidateName={candidate?.name ?? 'Candidate'}
          userSpeechInput={session.userSpeechInput}
          onChangeUserSpeech={session.setUserSpeechInput}
          onSubmitTurn={session.submitCandidateTurn}
          isSessionActive={session.isSessionActive}
          isSubmitting={session.isSubmitting}
          hasAnswered={hasAnswered}
          error={session.error}
          notice={session.notice}
          interviewStage={session.interviewStage}
          evaluationResult={session.evaluationResult}
          onCompleteSession={session.completeSession}
          isCompleting={session.isCompleting}
          onOpenScorecard={() => setIsScorecardOpen(true)}
        />
      </div>

      {/* Resume Setup Modal */}
      <ResumeUploadModal
        isOpen={isResumeModalOpen}
        onClose={() => setIsResumeModalOpen(false)}
        candidate={candidate}
        initialResumeText={session.resumeText}
        onStartInterview={handleStartFromModal}
        isStarting={session.isStarting}
        error={session.error}
      />

      {/* Assessment Scorecard Modal */}
      <ScorecardModal
        isOpen={isScorecardOpen}
        onClose={() => setIsScorecardOpen(false)}
        result={session.evaluationResult}
        candidateName={candidate?.name ?? 'Candidate'}
        repoName={candidate?.repoName ?? 'Project'}
        onRestart={() => setIsResumeModalOpen(true)}
      />
    </div>
  );
};
