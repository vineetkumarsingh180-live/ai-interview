import React, { useState } from 'react';
import { GitBranch, Github, Play, Sparkles, CheckCircle2, User, Layers } from 'lucide-react';
import { CandidateRepo } from '../hooks/useRepoEvaluation';

interface RepoSubmitCardProps {
  repos: CandidateRepo[];
  selectedRepoId: string | null;
  onSelectRepo: (id: string) => void;
  onSubmitRepo: (payload: {
    candidateName: string;
    candidateGithubHandle: string;
    repoUrl: string;
    targetRole?: string;
  }) => Promise<any>;
  isSubmitting: boolean;
}

export const RepoSubmitCard: React.FC<RepoSubmitCardProps> = ({
  repos,
  selectedRepoId,
  onSelectRepo,
  onSubmitRepo,
  isSubmitting,
}) => {
  const [candidateName, setCandidateName] = useState('Alex Vance');
  const [githubHandle, setGithubHandle] = useState('alexvance');
  const [repoUrl, setRepoUrl] = useState('https://github.com/alexvance/distributed-raft-kv');
  const [targetRole, setTargetRole] = useState('Staff Distributed Systems Engineer');
  const [showSubmitForm, setShowSubmitForm] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidateName || !repoUrl) return;
    await onSubmitRepo({
      candidateName,
      candidateGithubHandle: githubHandle || 'candidate',
      repoUrl,
      targetRole,
    });
    setShowSubmitForm(false);
  };

  return (
    <div id="repo-submit-card" className="clay p-6 border border-slate-800/60 space-y-5 font-sans">
      {/* Card Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-600/20 text-violet-300 border border-violet-500/40">
            <Github className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">
              Candidate Code Repositories
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              Hermetic AST execution &amp; AI architecture breakdown
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowSubmitForm(!showSubmitForm)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-300 hover:text-white transition-colors border border-slate-700/50 cursor-pointer"
        >
          <span>{showSubmitForm ? 'Hide Form' : '+ New Audit'}</span>
        </button>
      </div>

      {/* Submission Form (Collapsible) */}
      {showSubmitForm && (
        <form
          onSubmit={handleSubmit}
          className="p-4 rounded-xl inset-well border border-slate-800/60 space-y-4 animate-in fade-in duration-200"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
            <div>
              <label className="block text-slate-300 mb-1">Candidate Full Name</label>
              <input
                type="text"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/50 text-slate-200 focus:outline-none focus:border-cyan-400"
                required
              />
            </div>
            <div>
              <label className="block text-slate-300 mb-1">GitHub Username</label>
              <input
                type="text"
                value={githubHandle}
                onChange={(e) => setGithubHandle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/50 text-slate-200 focus:outline-none focus:border-cyan-400"
                required
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-slate-300 mb-1">Public GitHub Repository URL</label>
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/50 text-slate-200 focus:outline-none focus:border-cyan-400"
                placeholder="https://github.com/org/repo"
                required
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-slate-300 mb-1">Target Engineering Role</label>
              <input
                type="text"
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/50 text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 rounded-xl btn-primary-clay text-xs font-semibold flex items-center justify-center gap-2 transition-all active:scale-95 cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin text-cyan-400" />
                <span>Cloning &amp; Benchmarking Sandbox...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Execute Hermetic Sandbox Audit</span>
              </>
            )}
          </button>
        </form>
      )}

      {/* Candidate Repos List */}
      <div className="space-y-2">
        <label className="block text-xs font-mono uppercase text-slate-400">
          Analyzed Candidate Submissions ({repos.length})
        </label>
        <div className="grid grid-cols-1 gap-2.5">
          {repos.map((r) => {
            const isSelected = selectedRepoId === r.id || (!selectedRepoId && r === repos[0]);
            return (
              <button
                key={r.id}
                id={`candidate-repo-item-${r.id}`}
                onClick={() => onSelectRepo(r.id)}
                className={`w-full p-3.5 rounded-xl text-left transition-all border flex items-center justify-between cursor-pointer ${
                  isSelected
                    ? 'bg-slate-800/90 border-cyan-400/50 shadow-[0_0_15px_rgba(34,211,238,0.15)] text-white'
                    : 'bg-slate-900/60 border-slate-800/60 hover:bg-slate-800/50 text-slate-400'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700/50 flex items-center justify-center overflow-hidden shrink-0">
                    {r.candidateAvatarUrl ? (
                      <img src={r.candidateAvatarUrl} alt={r.candidateName} className="w-full h-full object-cover" />
                    ) : (
                      <User className="w-4 h-4 text-violet-400" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white">
                        {r.candidateName}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">
                        @{r.candidateGithubHandle}
                      </span>
                    </div>
                    <p className="text-xs font-mono text-violet-400 flex items-center gap-1.5 mt-0.5">
                      <GitBranch className="w-3 h-3" />
                      <span>{r.repoName}</span>
                      <span className="text-slate-600">•</span>
                      <span className="text-slate-400">{r.language}</span>
                    </p>
                  </div>
                </div>

                <div className="text-right font-mono">
                  <div className="text-xs font-bold text-cyan-400 flex items-center justify-end gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{r.evaluation?.compositeHealthScore ?? 94} / 100</span>
                  </div>
                  <span className="text-[10px] text-slate-400 block mt-0.5">
                    {r.benchmark?.testCoveragePct ?? 94.2}% Coverage
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
