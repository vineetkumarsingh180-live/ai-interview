import React, { useState } from 'react';
import {
  Github,
  Sparkles,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Bug,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  HelpCircle,
  ExternalLink,
  Code,
} from 'lucide-react';
import { analyzeRepoUrl, RepoAnalysisOutput } from '../api';

const SAMPLE_REPOS = [
  'https://github.com/pallets/click',
  'https://github.com/encode/uvicorn',
  'https://github.com/expressjs/express',
];

interface GitHubRepoVerifierProps {
  onAnalyzed?: () => void;
}

export const GitHubRepoVerifier: React.FC<GitHubRepoVerifierProps> = ({ onAnalyzed }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [candidateName, setCandidateName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RepoAnalysisOutput | null>(null);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await analyzeRepoUrl({
        repo_url: repoUrl.trim(),
        candidate_name: candidateName.trim() || undefined,
      });
      setResult(data);
      onAnalyzed?.();
    } catch (err: any) {
      setError(err?.message || 'Failed to inspect and analyze the repository.');
    } finally {
      setIsLoading(false);
    }
  };

  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const score = result?.overall_score ?? 0;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="space-y-6">
      {/* Search / Paste Input Card */}
      <section className="card p-5 sm:p-6 space-y-4 shadow-clay">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-canvas-alt text-mocha">
              <Github className="h-6 w-6" />
            </span>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-ink">GitHub Repository AI Verifier</h3>
              <p className="text-xs sm:text-sm text-ink-soft">
                Paste any public GitHub repository URL. Synapse will fetch the code and evaluate <strong>Vulgarity</strong>, <strong>Bugs</strong>, and <strong>Advanced Engineering</strong>.
              </p>
            </div>
          </div>
          <span className="badge badge-warm text-xs flex items-center gap-1">
            <Sparkles className="h-3.5 w-3.5" />
            Gemini 3.5 Flash Powered
          </span>
        </div>

        <form onSubmit={handleAnalyze} className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            <div className="sm:col-span-8">
              <label htmlFor="repo-url-input" className="field-label mb-1">
                GitHub Repository URL
              </label>
              <input
                id="repo-url-input"
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                required
                className="field text-xs sm:text-sm"
              />
            </div>
            <div className="sm:col-span-4">
              <label htmlFor="candidate-name-input" className="field-label mb-1">
                Candidate Name (Optional)
              </label>
              <input
                id="candidate-name-input"
                type="text"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                placeholder="e.g. Alex Chen"
                className="field text-xs sm:text-sm"
              />
            </div>
          </div>

          {/* Quick presets */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-xs text-ink-soft">Try example:</span>
            {SAMPLE_REPOS.map((sample) => (
              <button
                key={sample}
                type="button"
                onClick={() => setRepoUrl(sample)}
                className="text-xs px-2.5 py-1 rounded-lg bg-canvas-alt hover:bg-mocha-tint text-ink border border-line transition-colors"
              >
                {sample.replace('https://github.com/', '')}
              </button>
            ))}
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger-tint p-3 text-xs sm:text-sm text-danger">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isLoading || !repoUrl.trim()}
              className="btn btn-primary px-6 py-2.5 text-sm font-bold flex items-center gap-2 shadow-sm"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Fetching Code & Scoring with AI...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 text-warm" />
                  <span>Inspect & Score GitHub Repository</span>
                </>
              )}
            </button>
          </div>
        </form>
      </section>

      {/* Analysis Results View */}
      {result && (
        <section className="space-y-6 animate-fadeIn">
          {/* Top Score Banner */}
          <div className="card p-6 shadow-clay">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
              {/* Radial Gauge */}
              <div className="well flex flex-col items-center justify-center p-5 md:col-span-4 rounded-2xl bg-canvas-alt">
                <div className="relative flex h-36 w-36 items-center justify-center">
                  <svg className="h-full w-full -rotate-90" viewBox="0 0 130 130" aria-hidden="true">
                    <circle cx="65" cy="65" r={radius} className="text-sand/30" strokeWidth="10" stroke="currentColor" fill="transparent" />
                    <circle
                      cx="65"
                      cy="65"
                      r={radius}
                      className="text-mocha transition-all duration-1000 ease-out"
                      strokeWidth="10"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="transparent"
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center text-center">
                    <span className="text-3xl font-extrabold tabular-nums text-ink">{result.overall_score}</span>
                    <span className="text-xs font-bold text-ink-alt">/ 100</span>
                    <span className="mt-0.5 text-xs font-bold tracking-wider text-mocha uppercase">Grade: {result.grade}</span>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5 justify-center">
                  <span className="text-xs font-semibold text-mocha bg-mocha-tint px-2.5 py-0.5 rounded-full">
                    {result.primary_language}
                  </span>
                  <span className="text-xs text-ink-soft bg-surface px-2 py-0.5 rounded-full border border-line">
                    {result.files_analyzed_count} files read
                  </span>
                </div>
              </div>

              {/* Summary Details */}
              <div className="space-y-3 md:col-span-8">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Github className="h-5 w-5 text-mocha" />
                    <h4 className="text-base font-bold text-ink">{result.owner} / {result.repo_name}</h4>
                  </div>
                  <a
                    href={result.repo_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-mocha hover:underline flex items-center gap-1"
                  >
                    <span>View on GitHub</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>

                <div className="p-3.5 bg-surface rounded-xl border border-line">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-ink-alt block mb-1">
                    AI Code Verification Verdict
                  </span>
                  <p className="text-sm leading-relaxed text-ink">{result.summary_verdict}</p>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-lg bg-canvas-alt border border-line">
                    <span className="block text-ink-soft text-[10px] uppercase font-bold">Vulgarity</span>
                    <span className={`text-sm font-extrabold ${result.rubric.vulgarity_score >= 80 ? 'text-success' : 'text-danger'}`}>
                      {result.rubric.vulgarity_score}%
                    </span>
                  </div>
                  <div className="p-2 rounded-lg bg-canvas-alt border border-line">
                    <span className="block text-ink-soft text-[10px] uppercase font-bold">Bug Safety</span>
                    <span className={`text-sm font-extrabold ${result.rubric.bug_score >= 70 ? 'text-success' : 'text-warm'}`}>
                      {result.rubric.bug_score}%
                    </span>
                  </div>
                  <div className="p-2 rounded-lg bg-canvas-alt border border-line">
                    <span className="block text-ink-soft text-[10px] uppercase font-bold">Advance Level</span>
                    <span className="text-sm font-extrabold text-mocha">
                      {result.rubric.advance_score}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 3 Core Evaluation Pillars */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Pillar 1: Vulgarity & Professionalism */}
            <div className="card p-4 space-y-3 border border-line shadow-clay">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {result.rubric.vulgarity_score >= 80 ? (
                    <ShieldCheck className="h-5 w-5 text-success" />
                  ) : (
                    <ShieldAlert className="h-5 w-5 text-danger" />
                  )}
                  <h4 className="text-sm font-bold text-ink">1. Vulgarity & Cleanliness</h4>
                </div>
                <span
                  className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    result.rubric.vulgarity_score >= 80 ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'
                  }`}
                >
                  {result.rubric.vulgarity_score} / 100
                </span>
              </div>
              <p className="text-xs text-ink-soft leading-relaxed">{result.rubric.vulgarity_verdict}</p>
              <div>
                <span className="text-[11px] font-bold text-ink uppercase tracking-wider block mb-1">
                  Profanity / Toxicity Flags
                </span>
                {result.rubric.vulgarity_detected.length > 0 ? (
                  <ul className="space-y-1">
                    {result.rubric.vulgarity_detected.map((item, idx) => (
                      <li key={idx} className="text-xs text-danger bg-danger-tint p-2 rounded border border-danger/30 flex items-start gap-1.5">
                        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-success flex items-center gap-1.5 bg-success/10 p-2 rounded border border-success/20">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Clean code: No vulgar or offensive words detected.</span>
                  </p>
                )}
              </div>
            </div>

            {/* Pillar 2: Bugs & Vulnerabilities */}
            <div className="card p-4 space-y-3 border border-line shadow-clay">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bug className="h-5 w-5 text-warm" />
                  <h4 className="text-sm font-bold text-ink">2. Bugs & Vulnerabilities</h4>
                </div>
                <span
                  className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    result.rubric.bug_score >= 70 ? 'bg-success/15 text-success' : 'bg-warm/15 text-warm'
                  }`}
                >
                  {result.rubric.bug_score} / 100
                </span>
              </div>
              <p className="text-xs text-ink-soft leading-relaxed">{result.rubric.bug_verdict}</p>
              <div>
                <span className="text-[11px] font-bold text-ink uppercase tracking-wider block mb-1">
                  Identified Bugs & Flaws
                </span>
                {result.rubric.detected_bugs.length > 0 ? (
                  <ul className="space-y-1.5 max-h-48 overflow-y-auto">
                    {result.rubric.detected_bugs.map((bug, idx) => (
                      <li key={idx} className="text-xs text-ink bg-canvas-alt p-2 rounded border border-line flex items-start gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-warm mt-1.5 shrink-0" />
                        <span>{bug}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-success flex items-center gap-1.5 bg-success/10 p-2 rounded border border-success/20">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>No critical bugs or vulnerabilities identified.</span>
                  </p>
                )}
              </div>
            </div>

            {/* Pillar 3: Advanced Engineering */}
            <div className="card p-4 space-y-3 border border-line shadow-clay">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="h-5 w-5 text-mocha" />
                  <h4 className="text-sm font-bold text-ink">3. Advanced Engineering</h4>
                </div>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-mocha-tint text-mocha">
                  {result.rubric.advance_score} / 100
                </span>
              </div>
              <p className="text-xs text-ink-soft leading-relaxed">{result.rubric.advance_verdict}</p>
              <div>
                <span className="text-[11px] font-bold text-ink uppercase tracking-wider block mb-1">
                  Architectural Patterns & Depth
                </span>
                {result.rubric.advanced_features.length > 0 ? (
                  <ul className="space-y-1.5 max-h-48 overflow-y-auto">
                    {result.rubric.advanced_features.map((feat, idx) => (
                      <li key={idx} className="text-xs text-ink bg-canvas-alt p-2 rounded border border-line flex items-start gap-1.5">
                        <Code className="h-3.5 w-3.5 text-mocha mt-0.5 shrink-0" />
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-ink-soft bg-canvas-alt p-2 rounded border border-line">
                    Basic coding structure; no advanced design patterns detected.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Defense Questions and Recommendations */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Interview Defense Questions */}
            <div className="card p-4 space-y-3 border border-line">
              <div className="flex items-center gap-2 text-ink font-bold text-sm">
                <HelpCircle className="h-4 w-4 text-mocha" />
                <span>Technical Interview Defense Questions</span>
              </div>
              <p className="text-xs text-ink-soft">
                Questions an interviewer can ask the candidate to test if they truly understand the code:
              </p>
              <div className="space-y-2">
                {result.recommended_defense_topics.map((q, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-canvas-alt border border-line text-xs text-ink flex items-start gap-2">
                    <span className="font-bold text-mocha font-mono shrink-0">Q{idx + 1}.</span>
                    <span className="leading-relaxed">{q}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendations */}
            <div className="card p-4 space-y-3 border border-line">
              <div className="flex items-center gap-2 text-ink font-bold text-sm">
                <Lightbulb className="h-4 w-4 text-warm" />
                <span>Actionable Codebase Recommendations</span>
              </div>
              <p className="text-xs text-ink-soft">
                Specific improvements to raise this repository to production standards:
              </p>
              <div className="space-y-2">
                {result.suggested_improvements.map((tip, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-canvas-alt border border-line text-xs text-ink flex items-start gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-success mt-0.5 shrink-0" />
                    <span className="leading-relaxed">{tip}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
