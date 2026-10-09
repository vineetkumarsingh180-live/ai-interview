import React from 'react';
import { ShieldCheck, Cpu, CheckCircle2, AlertTriangle, Terminal, Code2, Flame } from 'lucide-react';
import { CodeEvaluation, BenchmarkSuite } from '../hooks/useRepoEvaluation';

interface CodeHealthGaugeProps {
  evaluation?: CodeEvaluation;
  benchmark?: BenchmarkSuite;
  candidateName?: string;
  repoName?: string;
}

export const CodeHealthGauge: React.FC<CodeHealthGaugeProps> = ({
  evaluation,
  benchmark,
  candidateName = 'Alex Vance',
  repoName = 'distributed-raft-kv',
}) => {
  const score = evaluation?.compositeHealthScore ?? 94;
  const coverage = benchmark?.testCoveragePct ?? 94.2;
  const antiCheat = evaluation?.antiCheatConfidence ?? 98.1;
  const complexity = benchmark?.cyclomaticComplexity ?? 3.8;

  // Compute SVG circle parameters
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div
      id="code-health-gauge-card"
      className="clay p-6 border border-slate-800/60 space-y-6 font-sans"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-400/10 text-cyan-400 border border-cyan-400/30 cyan-glow">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">
              Static &amp; Sandbox Code Audit
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              AST Anomaly Detection • Coverage • Concurrency Proofs
            </p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-cyan-400/10 text-cyan-400 border border-cyan-400/30">
          Ready for Voice Defense
        </span>
      </div>

      {/* Main Gauge + Core Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        {/* Radial SVG Gauge */}
        <div className="md:col-span-4 flex flex-col items-center justify-center p-5 rounded-2xl inset-well border border-slate-800/50">
          <div className="relative w-36 h-36 flex items-center justify-center cyan-glow rounded-full">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 140 140">
              <circle
                cx="70"
                cy="70"
                r={radius}
                className="text-slate-800"
                strokeWidth="10"
                stroke="currentColor"
                fill="transparent"
              />
              <circle
                cx="70"
                cy="70"
                r={radius}
                className="text-cyan-400 transition-all duration-1000 ease-out drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]"
                strokeWidth="10"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                stroke="currentColor"
                fill="transparent"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-3xl font-black font-mono text-white tracking-tight">
                {score.toFixed(0)}
              </span>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                Overall Index
              </span>
            </div>
          </div>
          <div className="mt-3 text-center">
            <span className="text-xs font-semibold text-cyan-400 font-mono">
              Grade: A+ (Production Ready)
            </span>
          </div>
        </div>

        {/* 4 Quantitative Metrics */}
        <div className="md:col-span-8 grid grid-cols-2 gap-3 font-mono">
          <div className="p-3.5 rounded-2xl clay border border-slate-800/50">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Test Coverage</span>
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-xl font-bold text-white">
              {coverage.toFixed(1)}%
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              32/32 unit &amp; partition tests passed
            </div>
          </div>

          <div className="p-3.5 rounded-2xl clay border border-slate-800/50">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Anti-Cheat AI Score</span>
              <ShieldCheck className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <div className="text-xl font-bold text-violet-400">
              {antiCheat.toFixed(1)}%
            </div>
            <div className="text-[10px] text-cyan-400 mt-0.5">
              Verified Human Author AST
            </div>
          </div>

          <div className="p-3.5 rounded-2xl clay border border-slate-800/50">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Cyclomatic Index</span>
              <Cpu className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-xl font-bold text-white">
              {complexity.toFixed(1)}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Low branching hazard
            </div>
          </div>

          <div className="p-3.5 rounded-2xl clay border border-slate-800/50">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>Concurrency Safety</span>
              <Flame className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-xl font-bold text-cyan-400">
              98.0 / 100
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Zero data races detected
            </div>
          </div>
        </div>
      </div>

      {/* Summary Verdict Quote */}
      <div className="p-4 rounded-2xl inset-well border border-slate-800/50 text-xs text-slate-300 font-mono leading-relaxed">
        <span className="text-violet-400 font-bold block mb-1">
          Architectural Auditor Verdict:
        </span>
        <p>
          {evaluation?.summaryVerdict ||
            'Exemplary implementation of the Raft consensus state machine in Rust. Clean zero-allocation serialization in the networking layer, though the heartbeat election timeout jitter could benefit from cryptographic seed randomization under adversarial network partition.'}
        </p>
      </div>

      {/* Recommended Defense Topics */}
      <div>
        <span className="text-xs font-mono uppercase text-slate-400 block mb-2">
          Recommended Topics For Live Voice Interrogation:
        </span>
        <div className="space-y-2">
          {(
            evaluation?.recommendedDefenseTopics || [
              'Log compaction and snapshot transmission under asymmetric split-brain partitions',
              'Zero-copy buffer reclamation in custom circular ring buffer',
              'Handling Byzantine or sluggish followers during joint consensus reconfiguration',
            ]
          ).map((topic, idx) => (
            <div
              key={idx}
              className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-900/60 border border-slate-800/50 text-xs font-mono text-slate-200"
            >
              <Terminal className="w-4 h-4 text-violet-400 shrink-0 mt-0.5" />
              <span>{topic}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
