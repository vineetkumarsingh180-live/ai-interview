import React from 'react';
import { Award, CheckCircle2, TrendingUp, X, RotateCcw } from 'lucide-react';
import type { VoiceCompleteResult } from '../types';

interface ScorecardModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: VoiceCompleteResult | null;
  candidateName?: string;
  repoName?: string;
  onRestart?: () => void;
}

export const ScorecardModal: React.FC<ScorecardModalProps> = ({
  isOpen,
  onClose,
  result,
  candidateName = 'Candidate',
  repoName = 'Project',
  onRestart,
}) => {
  if (!isOpen || !result) return null;

  const score = result.overallScore;
  const scorePercent = Math.min(100, Math.max(0, score * 10));

  const scoreColor =
    score >= 8.5
      ? 'text-success border-success'
      : score >= 7.0
      ? 'text-mocha border-mocha'
      : 'text-danger border-danger';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div
        className="card max-h-[90vh] w-full max-w-xl overflow-y-auto p-5 sm:p-6 space-y-5"
        role="dialog"
        aria-modal="true"
        aria-labelledby="scorecard-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-mocha text-surface">
              <Award className="h-5 w-5" />
            </span>
            <div>
              <h2 id="scorecard-title" className="text-base font-bold text-ink">
                Voice Defense Assessment Scorecard
              </h2>
              <p className="text-xs text-ink-soft">
                Evaluation results for {candidateName} ({repoName})
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-ink-alt hover:bg-canvas-alt hover:text-ink focus-visible:shadow-focus"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Overall Score Banner */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl border border-line bg-canvas-alt p-5">
          <div className="space-y-1 text-center sm:text-left">
            <span className="eyebrow block">Overall Evaluation Score</span>
            <p className="text-xs text-ink-alt">
              Scored on how correctly and thoroughly you answered the technical questions.
            </p>
            <span className="inline-block mt-2 badge badge-warm font-semibold">
              Scale 1.0 – 10.0
            </span>
          </div>

          <div className="flex flex-col items-center justify-center">
            <div
              className={`flex h-24 w-24 items-center justify-center rounded-full border-4 bg-surface shadow-md ${scoreColor}`}
            >
              <div className="text-center">
                <span className="text-2xl font-black tabular-nums tracking-tight">{score}</span>
                <span className="block text-[10px] text-ink-soft">/ 10</span>
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Metrics */}
        <div className="grid grid-cols-3 gap-2.5">
          <div className="well p-3 text-center">
            <span className="text-[11px] text-ink-alt block">Technical Depth</span>
            <span className="text-base font-bold text-ink tabular-nums">
              {result.technicalDepthScore} <span className="text-xs text-ink-soft">/ 10</span>
            </span>
          </div>
          <div className="well p-3 text-center">
            <span className="text-[11px] text-ink-alt block">Clarity</span>
            <span className="text-base font-bold text-ink tabular-nums">
              {result.clarityArticulationScore} <span className="text-xs text-ink-soft">/ 10</span>
            </span>
          </div>
          <div className="well p-3 text-center">
            <span className="text-[11px] text-ink-alt block">Project Defense</span>
            <span className="text-base font-bold text-ink tabular-nums">
              {result.projectDefenseScore} <span className="text-xs text-ink-soft">/ 10</span>
            </span>
          </div>
        </div>

        {/* Correctness & Summary */}
        <div className="space-y-2">
          <span className="eyebrow block">Answer Correctness & Performance Summary</span>
          <p className="rounded-xl border border-line bg-surface p-3.5 text-xs leading-relaxed text-ink">
            {result.summary}
          </p>
        </div>

        {/* Strengths & Improvements */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="rounded-xl border border-line bg-surface p-3 space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-success">
              <CheckCircle2 className="h-4 w-4" />
              <span>Key Strengths</span>
            </div>
            <ul className="space-y-1 text-ink-alt">
              {result.keyStrengths.map((str, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-success mt-0.5">•</span>
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-line bg-surface p-3 space-y-2">
            <div className="flex items-center gap-1.5 font-bold text-mocha">
              <TrendingUp className="h-4 w-4" />
              <span>Areas for Improvement</span>
            </div>
            <ul className="space-y-1 text-ink-alt">
              {result.areasForImprovement.map((area, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-mocha mt-0.5">•</span>
                  <span>{area}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between border-t border-line pt-3">
          {onRestart && (
            <button
              type="button"
              onClick={() => {
                onClose();
                onRestart();
              }}
              className="btn btn-secondary text-xs"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Retake Interview</span>
            </button>
          )}
          <button type="button" onClick={onClose} className="btn btn-primary text-xs ml-auto font-bold">
            Close Scorecard
          </button>
        </div>
      </div>
    </div>
  );
};
