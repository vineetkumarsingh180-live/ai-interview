import React, { useState } from 'react';
import {
  Code2,
  Sparkles,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  HelpCircle,
  Cpu,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { analyzeCodeSnippet, CodeAnalysisResult } from '../api';

const SAMPLE_CODE = `def process_user_data(users, query):
    \"\"\"Filter and format user records safely.\"\"\"
    results = []
    for user in users:
        if query.lower() in user.get('name', '').lower():
            results.append({
                'id': user.get('id'),
                'name': user.get('name'),
                'email': user.get('email')
            })
    return results`;

export const CodePasteAnalyzer: React.FC = () => {
  const [code, setCode] = useState(SAMPLE_CODE);
  const [language, setLanguage] = useState('Python');
  const [context, setContext] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CodeAnalysisResult | null>(null);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await analyzeCodeSnippet({
        code: code.trim(),
        language: language.trim() || undefined,
        context: context.trim() || undefined,
      });
      setResult(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to analyze code.');
    } finally {
      setIsLoading(false);
    }
  };

  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const score = result?.overall_score ?? 0;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="space-y-6">
      {/* Input Card */}
      <section className="card p-5 space-y-4 shadow-clay">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-canvas-alt text-mocha">
              <Code2 className="h-5 w-5" />
            </span>
            <div>
              <h3 className="text-base font-bold text-ink">Code Visitor & AI Verifier</h3>
              <p className="text-xs text-ink-soft">
                Paste your code snippet or implementation to evaluate code quality, security, and performance.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="field text-xs py-1 px-2.5 rounded-lg border border-line bg-surface font-medium"
            >
              <option value="Python">Python</option>
              <option value="TypeScript">TypeScript / JS</option>
              <option value="Go">Go</option>
              <option value="Rust">Rust</option>
              <option value="Java">Java</option>
              <option value="C++">C++</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>

        <form onSubmit={handleAnalyze} className="space-y-4">
          <div>
            <label className="field-label flex justify-between items-center mb-1">
              <span>Source Code Snippet</span>
              <span className="text-xs text-ink-soft">{code.split('\n').length} lines</span>
            </label>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste your function, class, or module code here..."
              rows={9}
              required
              className="field font-mono text-xs sm:text-sm leading-relaxed p-3 w-full bg-canvas-alt border-line focus:border-mocha rounded-xl resize-y"
            />
          </div>

          <div>
            <label className="field-label mb-1">Target Context / Problem Intent (Optional)</label>
            <input
              type="text"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="e.g. High-throughput user search filtering API for backend service"
              className="field text-xs sm:text-sm"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-danger/30 bg-danger-tint p-3 text-xs sm:text-sm text-danger">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button
              type="submit"
              disabled={isLoading || !code.trim()}
              className="btn btn-primary px-5 py-2.5 text-sm font-semibold flex items-center gap-2 shadow-sm"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Evaluating with Gemini AI...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 text-warm" />
                  <span>Analyze & Compute AI Score</span>
                </>
              )}
            </button>
          </div>
        </form>
      </section>

      {/* Analysis Results */}
      {result && (
        <section className="space-y-6 animate-fadeIn">
          {/* Top Score Banner */}
          <div className="card p-6 shadow-clay">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
              {/* Radial Gauge */}
              <div className="well flex flex-col items-center justify-center p-5 md:col-span-4 rounded-2xl bg-canvas-alt">
                <div className="relative flex h-32 w-32 items-center justify-center">
                  <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120" aria-hidden="true">
                    <circle cx="60" cy="60" r={radius} className="text-sand/30" strokeWidth="10" stroke="currentColor" fill="transparent" />
                    <circle
                      cx="60"
                      cy="60"
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
                    <span className="text-[11px] font-bold tracking-wider text-ink-alt uppercase">Grade: {result.grade}</span>
                  </div>
                </div>
                <span className="mt-3 text-xs font-semibold text-mocha bg-mocha-tint px-2.5 py-0.5 rounded-full">
                  {result.language_detected || language}
                </span>
              </div>

              {/* Summary details */}
              <div className="space-y-3 md:col-span-8">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-mocha" />
                  <h4 className="text-base font-bold text-ink">AI Code Verification Verdict</h4>
                </div>
                <p className="text-sm leading-relaxed text-ink bg-surface p-3.5 rounded-xl border border-line">
                  {result.summary}
                </p>
                <div className="flex flex-wrap gap-2 text-xs text-ink-soft">
                  <span className="flex items-center gap-1 bg-canvas-alt px-2.5 py-1 rounded-md border border-line">
                    <Zap className="h-3.5 w-3.5 text-warm" />
                    Quality Score: <strong>{result.overall_score}/100</strong>
                  </span>
                  <span className="flex items-center gap-1 bg-canvas-alt px-2.5 py-1 rounded-md border border-line">
                    <Cpu className="h-3.5 w-3.5 text-mocha" />
                    Evaluated with Gemini 2.0 Flash
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Dimension Breakdown Tiles */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-ink uppercase tracking-wider flex items-center gap-2">
              <span>Rubric Dimensions</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {result.dimensions?.map((dim, idx) => (
                <div key={idx} className="card p-3.5 border border-line bg-surface shadow-clay space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-ink">{dim.label}</span>
                    <span
                      className={`font-mono font-bold px-1.5 py-0.5 rounded ${
                        dim.score >= 80
                          ? 'bg-success/15 text-success'
                          : dim.score >= 60
                          ? 'bg-warm/15 text-warm'
                          : 'bg-danger/15 text-danger'
                      }`}
                    >
                      {dim.score} / 100
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="h-1.5 w-full bg-sand/30 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-mocha rounded-full transition-all duration-500"
                      style={{ width: `${dim.score}%` }}
                    />
                  </div>
                  <p className="text-xs text-ink-soft leading-snug">{dim.feedback}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Issues and Suggestions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Issues */}
            <div className="card p-4 border border-line space-y-3">
              <div className="flex items-center gap-2 text-ink font-bold text-sm">
                <AlertTriangle className="h-4 w-4 text-warm" />
                <span>Flagged Issues & Bottlenecks</span>
              </div>
              {result.issues && result.issues.length > 0 ? (
                <ul className="space-y-2">
                  {result.issues.map((issue, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-xs text-ink-soft bg-canvas-alt p-2.5 rounded-lg border border-line">
                      <span className="h-1.5 w-1.5 rounded-full bg-warm mt-1.5 shrink-0" />
                      <span>{issue}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-ink-soft">No major issues identified.</p>
              )}
            </div>

            {/* Suggestions */}
            <div className="card p-4 border border-line space-y-3">
              <div className="flex items-center gap-2 text-ink font-bold text-sm">
                <Lightbulb className="h-4 w-4 text-warm" />
                <span>Actionable Recommendations</span>
              </div>
              {result.suggestions && result.suggestions.length > 0 ? (
                <ul className="space-y-2">
                  {result.suggestions.map((sug, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-xs text-ink-soft bg-canvas-alt p-2.5 rounded-lg border border-line">
                      <CheckCircle2 className="h-3.5 w-3.5 text-success mt-0.5 shrink-0" />
                      <span>{sug}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-ink-soft">No specific recommendations.</p>
              )}
            </div>
          </div>

          {/* Interview Topics */}
          {result.interview_topics && result.interview_topics.length > 0 && (
            <div className="card p-4 border border-line space-y-3">
              <div className="flex items-center gap-2 text-ink font-bold text-sm">
                <HelpCircle className="h-4 w-4 text-mocha" />
                <span>Interview Defense Questions (Derived from this Code)</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {result.interview_topics.map((topic, idx) => (
                  <div key={idx} className="p-3 bg-canvas-alt rounded-xl border border-line text-xs text-ink flex items-start gap-2">
                    <span className="font-bold text-mocha font-mono shrink-0">Q{idx + 1}.</span>
                    <span className="leading-relaxed">{topic}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
};
