import React, { useRef, useEffect } from 'react';
import { Bot, User, Send, Info, AlertCircle, Award } from 'lucide-react';
import type { TranscriptTurn, VoiceCompleteResult } from '../types';

interface LiveTranscriptProps {
  transcript: TranscriptTurn[];
  candidateName: string;
  userSpeechInput: string;
  onChangeUserSpeech: (val: string) => void;
  onSubmitTurn: (text: string) => void;
  isSessionActive: boolean;
  isSubmitting: boolean;
  hasAnswered: boolean;
  error: string | null;
  notice: string | null;
  interviewStage?: string;
  evaluationResult?: VoiceCompleteResult | null;
  onCompleteSession?: () => void;
  isCompleting?: boolean;
  onOpenScorecard?: () => void;
}

export const LiveTranscript: React.FC<LiveTranscriptProps> = ({
  transcript,
  candidateName,
  userSpeechInput,
  onChangeUserSpeech,
  onSubmitTurn,
  isSessionActive,
  isSubmitting,
  hasAnswered,
  error,
  notice,
  interviewStage,
  evaluationResult,
  onCompleteSession,
  isCompleting,
  onOpenScorecard,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (userSpeechInput.trim()) {
      onSubmitTurn(userSpeechInput);
    }
  };

  return (
    <section
      id="live-defense-transcript-card"
      className="card flex h-[34rem] max-h-[80dvh] min-h-[22rem] flex-col gap-3 p-4 sm:p-6"
      aria-label="Interview transcript"
    >
      {/* Header: neutral status. No hire/no-hire label is ever shown. */}
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line pb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-ink">Interview transcript</h3>
            {isSessionActive && (
              <span className="badge badge-neutral text-[11px]">
                {interviewStage === 'intro'
                  ? 'Stage 1: Intro'
                  : interviewStage === 'skills'
                  ? 'Stage 2: Skills'
                  : interviewStage === 'project_defense'
                  ? 'Stage 3: Repo Architecture'
                  : interviewStage === 'project_deep_dive'
                  ? 'Stage 4: Deep Dive'
                  : interviewStage === 'completed'
                  ? 'Completed'
                  : 'Active'}
              </span>
            )}
          </div>
          <p className="text-sm text-ink-soft">Turn-based: speak or type your answer, then submit.</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {evaluationResult && onOpenScorecard ? (
            <button
              type="button"
              onClick={onOpenScorecard}
              className="btn btn-primary min-h-7 py-1 px-2.5 text-xs font-bold inline-flex items-center gap-1.5 shadow-sm"
            >
              <Award className="h-3.5 w-3.5" />
              <span>Score: {evaluationResult.overallScore} / 10</span>
            </button>
          ) : isSessionActive && hasAnswered && onCompleteSession ? (
            <button
              type="button"
              onClick={onCompleteSession}
              disabled={isCompleting || isSubmitting}
              className="btn btn-secondary min-h-7 py-1 px-2.5 text-xs font-semibold"
            >
              {isCompleting ? 'Evaluating…' : 'Complete & Score'}
            </button>
          ) : null}

          <span className={`badge ${hasAnswered ? 'badge-warm' : 'badge-neutral'}`}>
            {evaluationResult
              ? `Score: ${evaluationResult.overallScore}/10`
              : hasAnswered
              ? 'Needs human review'
              : 'Not scored'}
          </span>
        </div>
      </div>

      <p className="flex items-start gap-2 text-xs text-ink-alt">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>Answers are recorded for a human reviewer. This interview does not produce a score or a hiring decision.</span>
      </p>

      {/* Transcript */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1" role="log" aria-live="polite">
        {transcript.length === 0 && (
          <p className="well p-4 text-sm text-ink-alt">
            No interview in progress. Start the interview to receive the opening question.
          </p>
        )}
        {transcript.map((turn, i) => {
          const isAi = turn.speaker === 'ai_interviewer';
          return (
            <div key={i} className={`flex min-w-0 items-start gap-2.5 ${isAi ? '' : 'flex-row-reverse'}`}>
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${
                  isAi ? 'border-line-strong bg-canvas-alt text-mocha' : 'border-mocha bg-mocha text-surface'
                }`}
              >
                {isAi ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
              </span>

              <div
                className={`min-w-0 max-w-[85%] rounded-2xl border p-3 text-sm ${
                  isAi ? 'border-line bg-surface text-ink' : 'border-line-strong bg-mocha-tint text-ink'
                }`}
              >
                <div className="mb-1 flex items-center justify-between gap-4 text-xs text-ink-alt">
                  <span className="font-semibold text-ink">{isAi ? 'Interviewer' : candidateName}</span>
                  <span>{turn.timestamp}</span>
                </div>
                <p className="whitespace-pre-wrap break-words leading-relaxed">{turn.text}</p>
                {turn.technicalAssessmentNote && (
                  <p className="mt-2 border-t border-line pt-2 text-xs text-ink-alt">{turn.technicalAssessmentNote}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <p role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2.5 text-sm text-danger">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </p>
      )}
      {notice && (
        <p role="status" className="flex items-start gap-2 rounded-lg border border-line-strong bg-canvas-alt p-2.5 text-sm text-ink">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-warm" />
          <span>{notice}</span>
        </p>
      )}

      {/* Answer input */}
      <form onSubmit={handleSubmit} className="border-t border-line pt-3">
        <label htmlFor="candidate-verbal-response-input" className="sr-only">
          Your answer
        </label>
        <div className="relative flex items-center">
          <input
            id="candidate-verbal-response-input"
            type="text"
            value={userSpeechInput}
            onChange={(e) => onChangeUserSpeech(e.target.value)}
            disabled={!isSessionActive}
            placeholder={
              isSessionActive
                ? 'Speak with the microphone or type your answer here'
                : 'Start the interview to begin'
            }
            className="field pr-12"
          />
          <button
            type="submit"
            disabled={!isSessionActive || isSubmitting || !userSpeechInput.trim()}
            className="btn btn-primary absolute right-1 h-8 min-h-0 w-8 p-0"
            title="Submit answer"
            aria-label="Submit answer"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
    </section>
  );
};
