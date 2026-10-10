import React from 'react';
import { VoiceOrb } from './components/VoiceOrb';
import { LiveTranscript } from './components/LiveTranscript';
import type { VoiceInterviewState } from './hooks/useVoiceStream';
import type { VoiceCandidate } from './types';

interface VoiceDefenseViewProps {
  /** Result of `useVoiceStream()`, owned by the host so the session survives tab switches. */
  session: VoiceInterviewState;
  /** Who is being interviewed. `null` when the host has no candidate selected. */
  candidate: VoiceCandidate | null;
}

export const VoiceDefenseView: React.FC<VoiceDefenseViewProps> = ({ session, candidate }) => {
  const hasAnswered = session.transcript.some((t) => t.speaker === 'candidate');

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
          onStartSession={session.startSession}
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
        />
      </div>
    </div>
  );
};
