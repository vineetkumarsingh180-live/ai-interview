import React, { ReactNode } from 'react';
import { LeftNavbar, ActiveTab, SubView } from './LeftNavbar';

interface LayoutProps {
  children: ReactNode;
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  activeSubView: SubView;
  setActiveSubView: (view: SubView) => void;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  activeTab,
  setActiveTab,
  activeSubView,
  setActiveSubView,
}) => {
  const getSubViewLabel = () => {
    if (activeTab === 'leads') return 'Social Radar Stream';
    if (activeSubView === 'code-verifier') return 'Code Verifier & AST';
    if (activeSubView === 'voice-defense') return 'Live Voice Defense';
    return 'Leaderboard Ranking';
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-200 font-sans overflow-hidden">
      {/* Persistent Left Navigation Bar */}
      <LeftNavbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeSubView={activeSubView}
        setActiveSubView={setActiveSubView}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-slate-950">
        {/* Frosted Glass Header */}
        <header className="h-16 flex items-center justify-between px-8 border-b border-slate-800/50 glass shrink-0 z-20">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 uppercase tracking-widest font-mono">
              {activeTab === 'leads' ? 'Job Lead Radar' : 'Assessment Hub'}
            </span>
            <span className="text-slate-700">/</span>
            <span className="text-xs text-slate-200 font-bold uppercase tracking-widest font-mono">
              {getSubViewLabel()}
            </span>
          </div>

          <div className="flex items-center gap-3 font-mono">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-400 font-bold uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span>Sandbox Clean</span>
            </div>
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-cyan-400 shadow-inner">
              SY
            </div>
          </div>
        </header>

        {/* Main Scrollable View Container */}
        <main className="flex-1 min-w-0 p-6 lg:p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
};
