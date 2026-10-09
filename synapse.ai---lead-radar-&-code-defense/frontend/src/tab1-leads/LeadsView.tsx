import React, { useState } from 'react';
import { Sparkles, SlidersHorizontal, ArrowUpDown, Filter } from 'lucide-react';
import { useLeadStream } from './feature1-ingestion/hooks/useLeadStream';
import { ChannelFilterBar } from './feature1-ingestion/components/ChannelFilterBar';
import { LeadCard } from './feature1-ingestion/components/LeadCard';
import { SimulateIngestModal } from './feature1-ingestion/components/SimulateIngestModal';
import { LeadSearchInput } from './feature2-outreach/components/LeadSearchInput';
import { OutreachModal } from './feature2-outreach/components/OutreachModal';
import { JobLead } from './feature1-ingestion/types';

export const LeadsView: React.FC = () => {
  const {
    leads,
    telemetry,
    isLoadingLeads,
    selectedChannel,
    setSelectedChannel,
    searchQuery,
    setSearchQuery,
    triggerIngest,
    isIngesting,
    refetchLeads,
  } = useLeadStream();

  const [selectedLeadForOutreach, setSelectedLeadForOutreach] = useState<JobLead | null>(null);
  const [isSimulateModalOpen, setIsSimulateModalOpen] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<'match' | 'recent' | 'comp'>('match');

  const sortedLeads = [...leads].sort((a, b) => {
    if (sortBy === 'match') return b.matchScore - a.matchScore;
    if (sortBy === 'comp') return (b.compMax || 0) - (a.compMax || 0);
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Telemetry & Ingestion Status Bar */}
      <ChannelFilterBar
        selectedChannel={selectedChannel}
        onSelectChannel={setSelectedChannel}
        telemetry={telemetry}
        onOpenIngestModal={() => setIsSimulateModalOpen(true)}
        onRefresh={refetchLeads}
        isLoading={isLoadingLeads}
      />

      {/* Search & Sort Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-4 rounded-2xl clay border border-slate-800/50">
        <LeadSearchInput
          value={searchQuery}
          onChange={setSearchQuery}
          isLoading={isLoadingLeads}
        />

        <div className="flex items-center gap-2 font-mono text-xs text-slate-300 shrink-0">
          <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">Sort By:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-3 py-1.5 rounded-xl bg-slate-950/60 border border-slate-700/60 text-slate-200 focus:outline-none focus:border-cyan-400 font-mono text-xs"
          >
            <option value="match">Match Score (High to Low)</option>
            <option value="comp">Compensation (Max)</option>
            <option value="recent">Most Recent Ingest</option>
          </select>
        </div>
      </div>

      {/* Grid of Leads */}
      {isLoadingLeads ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div
              key={n}
              className="h-72 rounded-2xl clay border border-slate-800/50 animate-pulse"
            />
          ))}
        </div>
      ) : sortedLeads.length === 0 ? (
        <div className="p-12 rounded-2xl clay border border-slate-800/50 text-center font-mono">
          <Sparkles className="w-8 h-8 text-cyan-400 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white mb-1">No Leads Found</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-4">
            Try broadening your channel filters or simulate a new raw job post from X, Reddit, or LinkedIn.
          </p>
          <button
            onClick={() => setIsSimulateModalOpen(true)}
            className="px-4 py-2 rounded-xl btn-secondary-clay text-xs font-semibold"
          >
            + Ingest Raw Post
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {sortedLeads.map((lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              onDraftOutreach={(l) => setSelectedLeadForOutreach(l)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      <OutreachModal
        lead={selectedLeadForOutreach}
        isOpen={!!selectedLeadForOutreach}
        onClose={() => setSelectedLeadForOutreach(null)}
      />

      <SimulateIngestModal
        isOpen={isSimulateModalOpen}
        onClose={() => setIsSimulateModalOpen(false)}
        onIngest={triggerIngest}
        isIngesting={isIngesting}
      />
    </div>
  );
};
