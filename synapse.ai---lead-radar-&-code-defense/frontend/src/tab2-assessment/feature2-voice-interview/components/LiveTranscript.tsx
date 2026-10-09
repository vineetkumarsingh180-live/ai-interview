import React, { useRef, useEffect } from 'react';
import { Bot, User, Send, Award, CheckCircle2, ShieldAlert } from 'lucide-react';
import { TranscriptTurn } from '../hooks/useVoiceStream';

interface LiveTranscriptProps {
  transcript: TranscriptTurn[];
  candidateName: string;
  userSpeechInput: string;
  onChangeUserSpeech: (val: string) => void;
  onSubmitTurn: (text: string) => void;
  isSessionActive: boolean;
  compositeScore: number;
  verdict: string;
}

export const LiveTranscript: React.FC<LiveTranscriptProps> = ({
  transcript,
  candidateName,
  userSpeechInput,
  onChangeUserSpeech,
  onSubmitTurn,
  isSessionActive,
  compositeScore,
  verdict,
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

  const isAutoHire = compositeScore >= 89.0;

  return (
    <div
      id="live-defense-transcript-card"
      className="clay p-6 border border-slate-800/60 flex flex-col justify-between h-[520px] font-sans"
    >
      {/* Header with Verdict Pill */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800/50">
        <div>
          <h3 className="text-base font-bold text-white">
            Live Defense Dialogue Stream
          </h3>
          <p className="text-xs text-slate-400 font-mono">
            Direct Speech-to-Speech Interrogation with Gemini
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isAutoHire ? (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-cyan-400/10 text-cyan-400 border border-cyan-400/30 cyan-glow">
              <Award className="w-3.5 h-3.5" />
              Auto-Hire Qualified ({compositeScore.toFixed(1)}%)
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-amber-400/10 text-amber-400 border border-amber-400/30">
              <ShieldAlert className="w-3.5 h-3.5" />
              Under Evaluation ({compositeScore.toFixed(1)}%)
            </span>
          )}
        </div>
      </div>

      {/* Transcript Scroll Container */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-4 my-4 pr-2 text-xs font-mono"
      >
        {transcript.map((turn, i) => {
          const isAi = turn.speaker === 'ai_interviewer';
          return (
            <div
              key={i}
              className={`flex gap-3 ${isAi ? 'items-start' : 'items-start flex-row-reverse'}`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border ${
                  isAi
                    ? 'bg-violet-600/20 border-violet-500/40 text-violet-300'
                    : 'bg-cyan-400/20 border-cyan-400/40 text-cyan-300'
                }`}
              >
                {isAi ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
              </div>

              {/* Message Bubble */}
              <div
                className={`max-w-[82%] p-3.5 rounded-2xl ${
                  isAi
                    ? 'bg-slate-900/80 border border-slate-800/60 text-slate-200'
                    : 'bg-violet-950/40 border border-violet-500/30 text-white'
                }`}
              >
                <div className="flex items-center justify-between gap-4 mb-1 text-[10px] text-slate-400">
                  <span className="font-bold text-slate-300">
                    {isAi ? 'AI Technical Auditor' : candidateName}
                  </span>
                  <span>{turn.timestamp}</span>
                </div>

                <p className="leading-relaxed whitespace-pre-wrap">{turn.text}</p>

                {turn.technicalAssessmentNote && (
                  <div className="mt-2 pt-2 border-t border-slate-800/50 text-[10px] text-cyan-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>{turn.technicalAssessmentNote}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Candidate Input Form (Voice transcribed or manual text fallback) */}
      <form onSubmit={handleSubmit} className="pt-3 border-t border-slate-800/50">
        <div className="relative flex items-center">
          <input
            id="candidate-verbal-response-input"
            type="text"
            value={userSpeechInput}
            onChange={(e) => onChangeUserSpeech(e.target.value)}
            disabled={!isSessionActive}
            placeholder={
              isSessionActive
                ? 'Speak through microphone or type technical defense response here...'
                : 'Click "Initiate AI Voice Defense" to begin technical interrogation...'
            }
            className="w-full pl-4 pr-12 py-3 rounded-xl inset-well border border-slate-800/60 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!isSessionActive || !userSpeechInput.trim()}
            className="absolute right-2 p-2 rounded-lg btn-secondary-clay text-slate-950 disabled:opacity-30 transition-transform active:scale-95 cursor-pointer"
            title="Submit Defense"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
};
