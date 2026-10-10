import React from 'react';
import { Mic, MicOff, Volume2, Radio, Play, Square } from 'lucide-react';

interface VoiceOrbProps {
  isSessionActive: boolean;
  isListening: boolean;
  isAiSpeaking: boolean;
  audioLevel: number;
  isStarting: boolean;
  /** Whether this browser can capture speech; otherwise answers are typed. */
  canListen: boolean;
  onToggleListening: () => void;
  onStartSession: () => void;
  onEndSession: () => void;
  /** True once the candidate has submitted at least one answer. */
  hasAnswered: boolean;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  isSessionActive,
  isListening,
  isAiSpeaking,
  audioLevel,
  isStarting,
  canListen,
  onToggleListening,
  onStartSession,
  onEndSession,
  hasAnswered,
}) => {
  // The level is a simulated animation value, not a real microphone measurement.
  const scale = 1 + audioLevel * 0.18;
  const haloScale = 1 + audioLevel * 0.35;

  const statusLabel = isSessionActive
    ? isAiSpeaking
      ? 'Interviewer speaking'
      : isListening
      ? 'Listening to candidate'
      : 'Session active'
    : 'Not started';

  return (
    <section
      id="voice-defense-orb-card"
      className="card relative flex min-h-[380px] flex-col items-center justify-between overflow-hidden p-4 sm:p-6"
      aria-label="Voice interview controls"
    >
      {/* Status */}
      <div className="flex w-full flex-wrap items-center justify-between gap-2 border-b border-line pb-3 text-sm">
        <div className="flex items-center gap-2" role="status">
          <span
            className={`h-2.5 w-2.5 rounded-full ${isSessionActive ? 'bg-success' : 'bg-taupe'}`}
            aria-hidden="true"
          />
          <span className="font-semibold text-ink">{statusLabel}</span>
        </div>
        <span className={`badge ${hasAnswered ? 'badge-warm' : 'badge-neutral'}`}>
          {hasAnswered ? 'Needs human review' : 'Not scored'}
        </span>
      </div>

      {/* Orb */}
      <div className="relative my-6 flex h-52 w-52 items-center justify-center sm:h-60 sm:w-60" aria-hidden="true">
        <div
          className="absolute inset-4 rounded-full bg-sand/70 transition-transform duration-100 ease-out"
          style={{ transform: `scale(${haloScale})` }}
        />
        <div className="absolute h-40 w-40 rounded-full border border-taupe/60" style={{ transform: `scale(${scale})` }} />
        <div
          className="orb-surface relative flex h-32 w-32 items-center justify-center rounded-full transition-transform duration-150 ease-out"
          style={{ transform: `scale(${scale})` }}
        >
          <div className="flex h-28 w-28 items-center justify-center rounded-full border border-white/30">
            {isAiSpeaking ? (
              <Volume2 className="h-10 w-10 text-surface" />
            ) : isListening ? (
              <Radio className="h-10 w-10 text-surface" />
            ) : (
              <Mic className="h-10 w-10 text-surface" />
            )}
          </div>
        </div>
      </div>

      {/* Decorative level bars */}
      <div className="mb-4 flex h-8 items-end gap-1.5" aria-hidden="true">
        {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7, 0.3, 0.85, 0.65].map((factor, i) => {
          const barHeight = isSessionActive ? Math.max(6, audioLevel * factor * 32) : 4;
          return (
            <div
              key={i}
              className="w-1.5 rounded-full bg-taupe transition-all duration-100 ease-out"
              style={{ height: `${barHeight}px` }}
            />
          );
        })}
      </div>

      {/* Controls */}
      <div className="flex w-full flex-wrap items-center justify-center gap-3 border-t border-line pt-4">
        {!isSessionActive ? (
          <button
            id="start-voice-defense-btn"
            type="button"
            onClick={onStartSession}
            disabled={isStarting}
            className="btn btn-primary"
          >
            <Play className="h-4 w-4" />
            <span>{isStarting ? 'Starting…' : 'Start interview'}</span>
          </button>
        ) : (
          <>
            <button
              id="mic-toggle-btn"
              type="button"
              onClick={onToggleListening}
              disabled={!canListen}
              title={canListen ? undefined : 'Speech capture is not supported in this browser; type your answer instead.'}
              aria-pressed={isListening}
              className={`btn ${isListening ? 'btn-primary' : 'btn-secondary'}`}
            >
              {isListening ? (
                <>
                  <Mic className="h-4 w-4" />
                  <span>Done speaking</span>
                </>
              ) : (
                <>
                  <MicOff className="h-4 w-4" />
                  <span>Answer by voice</span>
                </>
              )}
            </button>

            <button id="terminate-defense-session-btn" type="button" onClick={onEndSession} className="btn btn-danger">
              <Square className="h-3.5 w-3.5 fill-current" />
              <span>End interview</span>
            </button>
          </>
        )}
      </div>
    </section>
  );
};
