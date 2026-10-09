import React from 'react';
import { Mic, MicOff, Volume2, Radio, Play, Square, Sparkles } from 'lucide-react';

interface VoiceOrbProps {
  isSessionActive: boolean;
  isListening: boolean;
  isAiSpeaking: boolean;
  audioLevel: number;
  onToggleListening: () => void;
  onStartSession: () => void;
  onEndSession: () => void;
  compositeScore: number;
  verdict: string;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  isSessionActive,
  isListening,
  isAiSpeaking,
  audioLevel,
  onToggleListening,
  onStartSession,
  onEndSession,
  compositeScore,
  verdict,
}) => {
  // Orb scaling and glow calculations
  const scale = 1 + audioLevel * 0.25;
  const outerScale = 1 + audioLevel * 0.45;
  const glowOpacity = Math.min(0.9, 0.2 + audioLevel * 0.7);

  return (
    <div
      id="voice-defense-orb-card"
      className="clay p-6 border border-slate-800/60 flex flex-col items-center justify-between min-h-[380px] relative overflow-hidden font-sans"
    >
      {/* Top Session Status Bar */}
      <div className="w-full flex items-center justify-between pb-4 border-b border-slate-800/50 font-mono text-xs z-10">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full ${
                isSessionActive ? 'bg-cyan-400' : 'bg-slate-500'
              } opacity-75`}
            />
            <span
              className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                isSessionActive ? 'bg-cyan-400' : 'bg-slate-500'
              }`}
            />
          </span>
          <span className="text-slate-200 font-bold">
            {isSessionActive
              ? isAiSpeaking
                ? 'AI Interrogating...'
                : isListening
                ? 'Candidate Defending...'
                : 'Session Active'
              : 'Standby Mode'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-400">Live Defense Score:</span>
          <span className="text-sm font-bold text-cyan-400 bg-cyan-400/10 px-2.5 py-0.5 rounded-lg border border-cyan-400/30 cyan-glow">
            {compositeScore.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Central Visual Orb Area */}
      <div className="relative my-8 flex items-center justify-center w-60 h-60">
        {/* Deep ambient background pulse */}
        <div
          className="absolute inset-0 rounded-full blur-3xl transition-transform duration-100 ease-out bg-violet-600/20"
          style={{
            transform: `scale(${outerScale})`,
            opacity: glowOpacity,
          }}
        />

        {/* Outer Ripple Wave */}
        <div
          className="absolute w-48 h-48 rounded-full border border-violet-500/30 animate-ping opacity-25"
        />

        {/* Middle Ripple Wave */}
        <div
          className="absolute w-40 h-40 rounded-full border border-cyan-400/40 transition-transform duration-100 ease-out"
          style={{
            transform: `scale(${scale})`,
            boxShadow: '0 0 20px rgba(34, 211, 238, 0.25)',
          }}
        />

        {/* Core Frosted Orb Sphere with orb-gradient & violet-glow */}
        <div
          className="relative w-32 h-32 rounded-full orb-gradient violet-glow relative flex items-center justify-center shadow-2xl transition-all duration-150 ease-out"
          style={{
            transform: `scale(${scale})`,
          }}
        >
          <div className="w-28 h-28 rounded-full border border-white/20 flex items-center justify-center">
            {isAiSpeaking ? (
              <Volume2 className="w-10 h-10 text-white animate-bounce" />
            ) : isListening ? (
              <Radio className="w-10 h-10 text-white animate-pulse" />
            ) : (
              <Mic className="w-10 h-10 text-white animate-pulse" />
            )}
          </div>
        </div>
      </div>

      {/* Dynamic Waveform Bars */}
      <div className="flex items-center gap-1.5 h-8 mb-4">
        {[0.4, 0.8, 0.6, 1.0, 0.5, 0.9, 0.7, 0.3, 0.85, 0.65].map((factor, i) => {
          const barHeight = isSessionActive ? Math.max(6, audioLevel * factor * 32) : 4;
          return (
            <div
              key={i}
              className="w-1.5 rounded-full bg-gradient-to-t from-violet-500 to-cyan-400 transition-all duration-100 ease-out"
              style={{ height: `${barHeight}px` }}
            />
          );
        })}
      </div>

      {/* Bottom Session Controls */}
      <div className="w-full flex items-center justify-center gap-4 pt-4 border-t border-slate-800/50 z-10">
        {!isSessionActive ? (
          <button
            id="start-voice-defense-btn"
            onClick={onStartSession}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl btn-primary-clay text-xs font-bold transition-all active:scale-95 cursor-pointer"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>Initiate AI Voice Defense</span>
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <button
              id="mic-toggle-btn"
              onClick={onToggleListening}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                isListening
                  ? 'btn-secondary-clay cyan-glow'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700/50'
              }`}
            >
              {isListening ? (
                <>
                  <Mic className="w-4 h-4 animate-pulse text-slate-950" />
                  <span className="text-slate-950">Speaking (Click when done)</span>
                </>
              ) : (
                <>
                  <MicOff className="w-4 h-4" />
                  <span>Unmute Mic to Answer</span>
                </>
              )}
            </button>

            <button
              id="terminate-defense-session-btn"
              onClick={onEndSession}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-red-950/40 hover:bg-red-950/60 text-red-400 text-xs font-mono border border-red-500/30 transition-colors cursor-pointer"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>End Defense</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
