import React from 'react';
import { Trophy, Medal, Award, CheckCircle2, GitBranch, ShieldCheck, User } from 'lucide-react';
import { LeaderboardItem } from '../hooks/useLeaderboard';

interface LeaderboardTableProps {
  leaderboard: LeaderboardItem[];
  isLoading: boolean;
}

export const LeaderboardTable: React.FC<LeaderboardTableProps> = ({
  leaderboard,
  isLoading,
}) => {
  const getRankBadge = (rank: number) => {
    switch (rank) {
      case 1:
        return (
          <div className="flex items-center justify-center w-7 h-7 rounded-full bg-amber-400/20 text-amber-400 border border-amber-400/40 font-bold text-xs shadow-[0_0_10px_rgba(251,191,36,0.3)]">
            <Trophy className="w-3.5 h-3.5" />
          </div>
        );
      case 2:
        return (
          <div className="flex items-center justify-center w-7 h-7 rounded-full bg-slate-700/40 text-slate-300 border border-slate-600/40 font-bold text-xs">
            <Medal className="w-3.5 h-3.5" />
          </div>
        );
      case 3:
        return (
          <div className="flex items-center justify-center w-7 h-7 rounded-full bg-amber-700/20 text-amber-500 border border-amber-600/30 font-bold text-xs">
            <Award className="w-3.5 h-3.5" />
          </div>
        );
      default:
        return (
          <span className="font-mono text-xs text-slate-400 font-bold pl-2">
            #{rank}
          </span>
        );
    }
  };

  return (
    <div
      id="live-assessment-leaderboard-card"
      className="clay p-6 border border-slate-800/60 space-y-4 font-sans"
    >
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/50">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-400/10 text-cyan-400 border border-cyan-400/30 cyan-glow">
            <Trophy className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">
              Verified Assessment Leaderboard
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              Composite ranking: Sandbox AST health (50%) + Live Voice Defense (50%)
            </p>
          </div>
        </div>

        <span className="text-xs font-mono text-cyan-400 bg-cyan-400/10 px-3 py-1 rounded-full border border-cyan-400/30">
          Auto-Hire Threshold: &ge;89.0%
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead>
            <tr className="border-b border-slate-800/60 text-slate-400 uppercase text-[10px]">
              <th className="py-3 px-2">Rank</th>
              <th className="py-3 px-3">Candidate &amp; Role</th>
              <th className="py-3 px-3">Verified Repo</th>
              <th className="py-3 px-3 text-right">Code Health</th>
              <th className="py-3 px-3 text-right">Voice Defense</th>
              <th className="py-3 px-3 text-right">Percentile</th>
              <th className="py-3 px-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {leaderboard.map((item, idx) => {
              const rank = idx + 1;
              const isTop = rank <= 3;
              return (
                <tr
                  key={item.id || idx}
                  className={`hover:bg-slate-800/40 transition-colors ${
                    isTop ? 'bg-violet-950/20' : ''
                  }`}
                >
                  {/* Rank */}
                  <td className="py-3.5 px-2 whitespace-nowrap">
                    {getRankBadge(rank)}
                  </td>

                  {/* Candidate */}
                  <td className="py-3.5 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700/50 flex items-center justify-center overflow-hidden shrink-0">
                        {item.candidateAvatarUrl ? (
                          <img
                            src={item.candidateAvatarUrl}
                            alt={item.candidateName}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <User className="w-3.5 h-3.5 text-violet-400" />
                        )}
                      </div>
                      <div>
                        <span className="font-bold text-sm text-white block">
                          {item.candidateName}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          @{item.candidateHandle} • {item.targetRole}
                        </span>
                      </div>
                    </div>
                  </td>

                  {/* Repo */}
                  <td className="py-3.5 px-3 whitespace-nowrap text-violet-400">
                    <div className="flex items-center gap-1.5">
                      <GitBranch className="w-3.5 h-3.5 text-slate-400" />
                      <span>{item.repoName}</span>
                    </div>
                  </td>

                  {/* Code Health */}
                  <td className="py-3.5 px-3 text-right whitespace-nowrap font-bold text-white">
                    {item.codeHealthScore.toFixed(1)} / 100
                  </td>

                  {/* Voice Defense */}
                  <td className="py-3.5 px-3 text-right whitespace-nowrap font-bold text-cyan-400">
                    {item.voiceDefenseScore.toFixed(1)}%
                  </td>

                  {/* Percentile */}
                  <td className="py-3.5 px-3 text-right whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/30 font-semibold">
                      {item.rankTier} ({item.compositePercentile.toFixed(1)}%)
                    </span>
                  </td>

                  {/* Status */}
                  <td className="py-3.5 px-3 text-center whitespace-nowrap">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-cyan-400/10 text-cyan-400 border border-cyan-400/30">
                      <CheckCircle2 className="w-3 h-3" />
                      {item.statusTag}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
