import React from 'react';
import { ShieldCheck, Cpu, CheckCircle2, Terminal, Wrench, Flame, Info } from 'lucide-react';
import { CodeEvaluation, BenchmarkSuite } from '../types';

interface CodeHealthGaugeProps {
  evaluation?: CodeEvaluation | null;
  benchmark?: BenchmarkSuite | null;
  /** Pipeline state of the selected repository, e.g. awaiting_analysis. */
  status?: string | null;
  isDemo?: boolean;
}

const NOT_MEASURED = 'Not measured';

interface MetricTileProps {
  label: string;
  value: string | null;
  icon: React.ReactNode;
  note?: string;
}

const MetricTile: React.FC<MetricTileProps> = ({ label, value, icon, note }) => (
  <div className="min-w-0 rounded-2xl border border-line bg-surface p-3.5 shadow-clay">
    <div className="mb-1 flex items-center justify-between gap-2 text-xs text-ink-soft">
      <span className="truncate">{label}</span>
      {icon}
    </div>
    <div className={`break-words font-bold tabular-nums ${value ? 'text-xl text-ink' : 'text-sm text-ink-soft'}`}>
      {value ?? NOT_MEASURED}
    </div>
    {note && <div className="mt-0.5 text-xs text-ink-soft">{note}</div>}
  </div>
);

export const CodeHealthGauge: React.FC<CodeHealthGaugeProps> = ({ evaluation, benchmark, status, isDemo }) => {
  const score = evaluation?.compositeHealthScore ?? null;
  const coverage = benchmark?.testCoveragePct ?? null;
  const complexity = benchmark?.cyclomaticComplexity ?? null;
  const concurrency = evaluation?.concurrencySafetyScore ?? null;
  const maintainability = evaluation?.maintainabilityScore ?? null;

  // SVG gauge geometry
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - ((score ?? 0) / 100) * circumference;

  const topics = evaluation?.recommendedDefenseTopics ?? [];

  return (
    <section id="code-health-gauge-card" className="card space-y-5 p-4 sm:p-6" aria-label="Code assessment">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-canvas-alt text-mocha">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-base font-bold leading-tight text-ink">Code assessment</h3>
            <p className="text-sm text-ink-soft">Measured results for the selected repository.</p>
          </div>
        </div>
        {isDemo && <span className="badge badge-warm shrink-0">Demo fixture</span>}
      </div>

      {/* Honest provenance note */}
      <p className="flex items-start gap-2 rounded-xl border border-line-strong bg-canvas-alt p-3 text-sm text-ink">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-warm" aria-hidden="true" />
        <span>
          Repository analysis is not available in this build: submissions are stored and wait for an analysis
          engine. A value appears here only when it was actually measured; scores are never a hiring decision.
        </span>
      </p>

      {!evaluation && !benchmark ? (
        <div className="well p-6 text-center text-sm text-ink-alt">
          {status === 'failed'
            ? 'Analysis failed for this repository.'
            : status
            ? 'Awaiting analysis: nothing has been measured for this repository yet.'
            : 'Select or submit a repository to see its assessment.'}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 items-stretch gap-4 md:grid-cols-12">
            {/* Radial gauge */}
            <div className="well flex flex-col items-center justify-center p-5 md:col-span-4">
              <div className="relative flex h-36 w-36 items-center justify-center">
                <svg className="h-full w-full -rotate-90" viewBox="0 0 140 140" aria-hidden="true">
                  <circle cx="70" cy="70" r={radius} className="text-sand" strokeWidth="10" stroke="currentColor" fill="transparent" />
                  <circle
                    cx="70"
                    cy="70"
                    r={radius}
                    className="text-mocha transition-all duration-700 ease-out"
                    strokeWidth="10"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                  />
                </svg>
                <div className="absolute flex flex-col items-center">
                  <span className="text-3xl font-extrabold tabular-nums text-ink">{score != null ? score.toFixed(0) : '—'}</span>
                  <span className="text-xs font-medium text-ink-alt">/ 100</span>
                </div>
              </div>
              <p className="mt-3 text-center text-xs text-ink-alt">
                {score != null ? 'Overall index (reported by the evaluation)' : NOT_MEASURED}
              </p>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-1 gap-3 min-[420px]:grid-cols-2 md:col-span-8">
              <MetricTile
                label="Test coverage"
                value={coverage != null ? `${coverage.toFixed(1)}%` : null}
                icon={<CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />}
              />
              <MetricTile
                label="Cyclomatic complexity"
                value={complexity != null ? complexity.toFixed(1) : null}
                icon={<Cpu className="h-3.5 w-3.5 shrink-0 text-warm" />}
              />
              <MetricTile
                label="Concurrency score"
                value={concurrency != null ? `${concurrency.toFixed(0)} / 100` : null}
                icon={<Flame className="h-3.5 w-3.5 shrink-0 text-warm" />}
              />
              <MetricTile
                label="Maintainability score"
                value={maintainability != null ? `${maintainability.toFixed(0)} / 100` : null}
                icon={<Wrench className="h-3.5 w-3.5 shrink-0 text-mocha" />}
              />
            </div>
          </div>

          {/* Summary */}
          <div className="well p-4 text-sm leading-relaxed text-ink">
            <span className="mb-1 block text-xs font-bold uppercase tracking-wider text-ink-alt">Reviewer summary</span>
            <p className="break-words">{evaluation?.summaryVerdict || 'No written evaluation available.'}</p>
          </div>

          {/* Topics */}
          <div>
            <span className="eyebrow mb-2 block">Suggested interview topics</span>
            {topics.length === 0 ? (
              <p className="text-sm text-ink-soft">No topics available.</p>
            ) : (
              <ul className="space-y-2">
                {topics.map((topic, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2.5 rounded-xl border border-line-strong bg-surface p-3 text-sm text-ink"
                  >
                    <Terminal className="mt-0.5 h-4 w-4 shrink-0 text-mocha" />
                    <span className="min-w-0 break-words">{topic}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
};
