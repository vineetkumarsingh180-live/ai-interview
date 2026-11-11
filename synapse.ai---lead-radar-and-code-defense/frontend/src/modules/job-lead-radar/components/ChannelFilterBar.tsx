import React from 'react';
import { Radio, RefreshCw, Plus, Twitter, Linkedin, MessageSquare, Send, Sparkles } from 'lucide-react';
import { IngestionTelemetry } from '../types';

interface ChannelFilterBarProps {
  selectedChannel: string;
  onSelectChannel: (channel: string) => void;
  telemetry?: IngestionTelemetry;
  onOpenIngestModal: () => void;
  onRefresh: () => void;
  isLoading: boolean;
  activeView?: 'feed' | 'chatbot';
  onSelectView?: (view: 'feed' | 'chatbot') => void;
}

const CHANNELS = [
  { id: 'all', label: 'All channels', icon: Radio },
  { id: 'twitter', label: 'X / Twitter', icon: Twitter },
  { id: 'linkedin', label: 'LinkedIn', icon: Linkedin },
  { id: 'reddit', label: 'Reddit', icon: MessageSquare },
  { id: 'telegram', label: 'Telegram', icon: Send },
];

const NOT_AVAILABLE = '—';

export const ChannelFilterBar: React.FC<ChannelFilterBarProps> = ({
  selectedChannel,
  onSelectChannel,
  telemetry,
  onOpenIngestModal,
  onRefresh,
  isLoading,
  activeView = 'feed',
  onSelectView,
}) => {
  // Genuine counts plus labelled demo counts (reported separately by the API); the note says so.
  const total = (genuine?: number, demo?: number) => (telemetry ? ((genuine ?? 0) + (demo ?? 0)).toLocaleString() : NOT_AVAILABLE);
  const demoShown =
    (telemetry?.demoScanned24h ?? 0) + (telemetry?.demoQualifiedLeadsCount ?? 0) + (telemetry?.demoSeekingDiscardedCount ?? 0) +
    (telemetry?.demoAwaitingAnalysisCount ?? 0);
  const metrics = [
    { label: 'Scanned (24h)', value: total(telemetry?.totalScanned24h, telemetry?.demoScanned24h) },
    { label: 'Qualified leads', value: total(telemetry?.qualifiedLeadsCount, telemetry?.demoQualifiedLeadsCount) },
    { label: 'Seekers filtered', value: total(telemetry?.seekingDiscardedCount, telemetry?.demoSeekingDiscardedCount) },
    { label: 'Awaiting analysis', value: total(telemetry?.awaitingAnalysisCount, telemetry?.demoAwaitingAnalysisCount) },
  ];

  return (
    <div id="channel-filter-bar" className="space-y-4">
      <section className="card space-y-4 p-4 sm:p-5" aria-label="Lead ingestion summary">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-canvas-alt text-mocha">
              <Radio className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <h2 className="text-base font-bold leading-tight text-ink">Lead radar</h2>
              <p className="text-sm text-ink-soft">Posts are imported manually, then analysed into structured leads.</p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              id="refresh-feed-btn"
              type="button"
              onClick={onRefresh}
              disabled={isLoading}
              className="btn btn-secondary btn-icon"
              title="Refresh leads"
              aria-label="Refresh leads"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              id="chatbot-toggle-btn"
              type="button"
              onClick={() => onSelectView?.(activeView === 'chatbot' ? 'feed' : 'chatbot')}
              className={`btn ${activeView === 'chatbot' ? 'btn-primary' : 'btn-secondary'}`}
              title="AI Job Search Chatbot"
            >
              <Sparkles className="h-4 w-4 text-warm" />
              <span>{activeView === 'chatbot' ? 'Close Chatbot' : 'AI Chatbot'}</span>
            </button>
            <button id="ingest-post-trigger-btn" type="button" onClick={onOpenIngestModal} className="btn btn-primary">
              <Plus className="h-4 w-4" />
              <span>Add a post</span>
            </button>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
          {metrics.map((m) => (
            <div key={m.label} className="well min-w-0 px-2.5 py-2.5 sm:px-3">
              <dt className="text-[11px] leading-tight text-ink-alt sm:text-xs">{m.label}</dt>
              <dd className="mt-0.5 text-lg font-bold tabular-nums text-ink sm:text-xl">{m.value}</dd>
            </div>
          ))}
        </dl>
        <p className="text-xs text-ink-soft">
          Counts are computed from the posts stored in the database over the last 24 hours
          {telemetry && demoShown > 0
            ? `, including ${telemetry.demoScanned24h ?? 0} labelled demo post${telemetry.demoScanned24h === 1 ? '' : 's'} (fixtures, not real posts).`
            : telemetry && telemetry.demoPostsCount > 0
            ? `; ${telemetry.demoPostsCount} labelled demo post${telemetry.demoPostsCount === 1 ? ' is' : 's are'} older than that window.`
            : '.'}
        </p>
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2" role="tablist" aria-label="View mode">
          <button
            type="button"
            role="tab"
            aria-selected={activeView === 'feed'}
            onClick={() => onSelectView?.('feed')}
            className={`chip font-semibold ${activeView === 'feed' ? 'border-mocha bg-canvas-alt text-ink' : 'text-ink-soft'}`}
          >
            <Radio className="h-3.5 w-3.5" />
            <span>Lead Stream</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeView === 'chatbot'}
            onClick={() => onSelectView?.('chatbot')}
            className={`chip font-semibold ${activeView === 'chatbot' ? 'border-warm bg-warm-tint text-warm-strong' : 'text-ink-soft'}`}
          >
            <Sparkles className="h-3.5 w-3.5 text-warm" />
            <span>AI Job Chatbot</span>
          </button>
        </div>

        {activeView === 'feed' && (
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter by source">
            {CHANNELS.map((ch) => {
              const Icon = ch.icon;
              const isActive = selectedChannel === ch.id;
              return (
                <button
                  key={ch.id}
                  id={`channel-tab-${ch.id}`}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => onSelectChannel(ch.id)}
                  className="chip"
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{ch.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
};
