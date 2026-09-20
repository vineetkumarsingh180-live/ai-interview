import React from 'react';
import {
  Radar,
  ShieldCheck,
  Mic,
  Trophy,
  Cpu,
  Sparkles,
  Zap,
  Terminal,
  Activity,
  Layers,
  ChevronRight
} from 'lucide-react';

export type ActiveTab = 'leads' | 'assessment';
export type SubView = 'radar' | 'code-verifier' | 'voice-defense' | 'leaderboard';

interface LeftNavbarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  activeSubView: SubView;
  setActiveSubView: (view: SubView) => void;
}

export const LeftNavbar: React.FC<LeftNavbarProps> = ({
  activeTab,
  setActiveTab,
  activeSubView,
  setActiveSubView,
}) => {
  return (
    <aside
      id="left-navbar"
      className="w-64 shrink-0 bg-slate-900/80 backdrop-blur-md border-r border-slate-800 flex flex-col justify-between h-screen sticky top-0 p-4 select-none z-30 font-sans"
    >
      <div className="space-y-6">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-2.5 px-2 py-1">
          <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center text-slate-950 font-black text-base shadow-[0_0_20px_rgba(34,211,238,0.3)]">
            G
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-lg tracking-tight text-cyan-400">
                GEMINI<span className="text-white">.OS</span>
              </span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">
                v2.6
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-400 tracking-tight">
              Talent Assessment Core
            </p>
          </div>
        </div>

        {/* Navigation Categories */}
        <div className="space-y-4">
          {/* TAB 1: SOCIAL LEAD RADAR */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between text-[10px] font-bold text-slate-500 uppercase tracking-widest">
              <span>Domain Module 1</span>
              <span className="flex items-center gap-1 text-cyan-400 font-mono text-[9px]">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                Live
              </span>
            </div>

            <button
              id="nav-tab-leads"
              onClick={() => {
                setActiveTab('leads');
                setActiveSubView('radar');
              }}
              className={`w-full flex items-center justify-between p-3 rounded-xl transition-all border text-left cursor-pointer ${
                activeTab === 'leads'
                  ? 'bg-slate-800 text-cyan-400 shadow-lg border-cyan-400/30'
                  : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-5 h-5 rounded-md flex items-center justify-center border-2 ${
                    activeTab === 'leads'
                      ? 'border-cyan-400 bg-cyan-400/15 text-cyan-400'
                      : 'border-slate-600 text-slate-400'
                  }`}
                >
                  <Radar className="w-3 h-3" />
                </div>
                <div>
                  <span className="text-sm font-bold block leading-none">
                    Job Lead Radar
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Social Ingest &amp; Outreach
                  </span>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">
                48
              </span>
            </button>
          </div>

          {/* TAB 2: CODE VERIFICATION & VOICE DEFENSE */}
          <div>
            <div className="px-3 mb-2 flex items-center justify-between text-[10px] font-bold text-slate-500 uppercase tracking-widest">
              <span>Domain Module 2</span>
              <span className="text-violet-400 font-mono text-[9px]">Assessment</span>
            </div>

            <div className="space-y-1">
              <button
                id="nav-tab-assessment"
                onClick={() => {
                  setActiveTab('assessment');
                  setActiveSubView('code-verifier');
                }}
                className={`w-full flex items-center justify-between p-3 rounded-xl transition-all border text-left cursor-pointer ${
                  activeTab === 'assessment' && activeSubView === 'code-verifier'
                    ? 'bg-slate-800 text-cyan-400 shadow-lg border-cyan-400/30'
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-md flex items-center justify-center border-2 ${
                      activeTab === 'assessment' && activeSubView === 'code-verifier'
                        ? 'border-cyan-400 bg-cyan-400/15 text-cyan-400'
                        : 'border-slate-600 text-slate-400'
                    }`}
                  >
                    <ShieldCheck className="w-3 h-3" />
                  </div>
                  <div>
                    <span className="text-sm font-bold block leading-none">
                      Code Verifier
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      AST &amp; Rubrics
                    </span>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </button>

              <button
                id="nav-subview-voice"
                onClick={() => {
                  setActiveTab('assessment');
                  setActiveSubView('voice-defense');
                }}
                className={`w-full flex items-center justify-between p-3 rounded-xl transition-all border text-left cursor-pointer ${
                  activeTab === 'assessment' && activeSubView === 'voice-defense'
                    ? 'bg-slate-800 text-cyan-400 shadow-lg border-cyan-400/30'
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-md flex items-center justify-center border-2 ${
                      activeTab === 'assessment' && activeSubView === 'voice-defense'
                        ? 'border-cyan-400 bg-cyan-400/15 text-cyan-400'
                        : 'border-slate-600 text-slate-400'
                    }`}
                  >
                    <Mic className="w-3 h-3" />
                  </div>
                  <div>
                    <span className="text-sm font-bold block leading-none">
                      Voice Interview
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      Live AI Defense
                    </span>
                  </div>
                </div>
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              </button>

              <button
                id="nav-subview-leaderboard"
                onClick={() => {
                  setActiveTab('assessment');
                  setActiveSubView('leaderboard');
                }}
                className={`w-full flex items-center justify-between p-3 rounded-xl transition-all border text-left cursor-pointer ${
                  activeTab === 'assessment' && activeSubView === 'leaderboard'
                    ? 'bg-slate-800 text-cyan-400 shadow-lg border-cyan-400/30'
                    : 'bg-transparent border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-5 h-5 rounded-md flex items-center justify-center border-2 ${
                      activeTab === 'assessment' && activeSubView === 'leaderboard'
                        ? 'border-cyan-400 bg-cyan-400/15 text-cyan-400'
                        : 'border-slate-600 text-slate-400'
                    }`}
                  >
                    <Trophy className="w-3 h-3" />
                  </div>
                  <div>
                    <span className="text-sm font-bold block leading-none">
                      Leaderboard
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      Top 1% Percentiles
                    </span>
                  </div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Footer System Status Strip */}
      <div className="clay p-4 flex items-center gap-3 border border-slate-700/50">
        <div className="w-9 h-9 rounded-full bg-slate-700 border border-slate-600 flex items-center justify-center text-cyan-400 shrink-0">
          <Activity className="w-4 h-4" />
        </div>
        <div className="min-w-0">
          <div className="text-xs font-bold text-white truncate">Archie_Bot</div>
          <div className="text-[10px] text-cyan-400 font-mono tracking-wider flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            SYSTEM ACTIVE
          </div>
        </div>
      </div>
    </aside>
  );
};
