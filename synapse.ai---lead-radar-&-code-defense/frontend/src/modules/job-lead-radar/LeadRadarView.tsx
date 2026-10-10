import React, { useState } from 'react';
import { Sparkles, ArrowUpDown, AlertCircle } from 'lucide-react';
import { useLeadStream } from './hooks/useLeadStream';
import { ChannelFilterBar } from './components/ChannelFilterBar';
import { LeadCard } from './components/LeadCard';
import { SimulateIngestModal } from './components/SimulateIngestModal';
import { LeadSearchInput } from './components/LeadSearchInput';
import { OutreachModal } from './components/OutreachModal';
import { JobLead } from './types';

export const LeadRadarView: React.FC = () => {
  const {
    leads,
    telemetry,
    isLoadingLeads,
    leadsError,
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
    <div className="space-y-5">
      <ChannelFilterBar
        selectedChannel={selectedChannel}
        onSelectChannel={setSelectedChannel}
        telemetry={telemetry}
        onOpenIngestModal={() => setIsSimulateModalOpen(true)}
        onRefresh={refetchLeads}
        isLoading={isLoadingLeads}
      />

      {/* Search & sort */}
      <div className="card flex flex-col gap-3 p-3 sm:flex-row sm:items-center sm:justify-between sm:p-4">
        <LeadSearchInput value={searchQuery} onChange={setSearchQuery} isLoading={isLoadingLeads} />

        <div className="flex shrink-0 items-center gap-2 text-sm">
          <ArrowUpDown className="h-4 w-4 text-ink-soft" aria-hidden="true" />
          <label htmlFor="lead-sort-select" className="text-ink-soft">
            Sort by
          </label>
          <select
            id="lead-sort-select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'match' | 'recent' | 'comp')}
            className="field w-auto min-w-0 flex-1 sm:flex-none"
          >
            <option value="match">Match score</option>
            <option value="comp">Compensation (max)</option>
            <option value="recent">Most recent</option>
          </select>
        </div>
      </div>

      {/* Leads */}
      {isLoadingLeads ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-busy="true" aria-label="Loading leads">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div key={n} className="card h-72 animate-pulse bg-canvas-alt" />
          ))}
        </div>
      ) : leadsError ? (
        <div className="card p-8 text-center" role="alert">
          <AlertCircle className="mx-auto mb-3 h-8 w-8 text-danger" />
          <h3 className="mb-1 text-base font-bold text-ink">Leads could not be loaded</h3>
          <p className="mx-auto mb-4 max-w-md text-sm text-ink-soft">{leadsError.message}</p>
          <button type="button" onClick={() => refetchLeads()} className="btn btn-secondary">
            Try again
          </button>
        </div>
      ) : sortedLeads.length === 0 ? (
        <div className="card p-10 text-center">
          <Sparkles className="mx-auto mb-3 h-8 w-8 text-warm" />
          <h3 className="mb-1 text-base font-bold text-ink">No leads found</h3>
          <p className="mx-auto mb-4 max-w-md text-sm text-ink-soft">
            Nothing has been analysed yet for this filter. Import a post to create one; analysis needs the AI
            provider to be configured on the server.
          </p>
          <button type="button" onClick={() => setIsSimulateModalOpen(true)} className="btn btn-primary">
            + Import raw post
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {sortedLeads.map((lead) => (
            <LeadCard key={lead.id} lead={lead} onDraftOutreach={(l) => setSelectedLeadForOutreach(l)} />
          ))}
        </div>
      )}

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
