import React from 'react';
import { Radio, Filter, RefreshCw, Plus, Twitter, Linkedin, MessageSquare, Send, Sparkles } from 'lucide-react';
import { IngestionTelemetry } from '../types';

interface ChannelFilterBarProps {
  selectedChannel: string;
  onSelectChannel: (channel: string) => void;
  telemetry?: IngestionTelemetry;
  onOpenIngestModal: () => void;
  onRefresh: () => void;
  isLoading: boolean;
}

const CHANNELS = [
  { id: 'all', label: 'All Channels', icon: Radio },
  { id: 'twitter', label: 'X / Twitter', icon: Twitter },
  { id: 'linkedin', label: 'LinkedIn Jobs', icon: Linkedin },
  { id: 'reddit', label: 'Reddit Tech', icon: MessageSquare },
  { id: 'telegram', label: 'Telegram Alpha', icon: Send },
];

export const ChannelFilterBar: React.FC<ChannelFilterBarProps> = ({
  selectedChannel,
  onSelectChannel,
  telemetry,
  onOpenIngestModal,
  onRefresh,
  isLoading,
}) => {
  return (
    <div id="channel-filter-bar" className="space-y-4 mb-6">
      {/* Top Telemetry Strip */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl clay border border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-slate-800 border border-cyan-400/30 text-cyan-400 cyan-glow">
            <Radio className="w-4 h-4 animate-pulse text-cyan-400" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-medium tracking-wider text-cyan-400 uppercase">
                Radar Ingestion Online
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-slate-950/70 text-slate-300 border border-slate-700/50">
                4 Channels Active
              </span>
            </div>
            <p className="text-sm font-semibold text-white">
              Real-Time Social Scrape &amp; Gemini Parsing Stream
            </p>
          </div>
        </div>

        {/* Telemetry Metrics */}
        <div className="flex items-center gap-5 text-xs font-mono">
          <div className="hidden sm:block text-right">
            <span className="text-slate-400 block text-[11px]">Scanned (24h)</span>
            <span className="text-slate-200 font-bold text-sm">
              {telemetry ? telemetry.totalScanned24h.toLocaleString() : '1,842'} posts
            </span>
          </div>

          <div className="hidden md:block h-7 w-[1px] bg-slate-700/50" />

          <div className="hidden sm:block text-right">
            <span className="text-slate-400 block text-[11px]">Qualified Leads</span>
            <span className="text-cyan-400 font-bold text-sm">
              {telemetry ? telemetry.qualifiedLeadsCount : '48'} parsed
            </span>
          </div>

          <div className="hidden md:block h-7 w-[1px] bg-slate-700/50" />

          <div className="hidden lg:block text-right">
            <span className="text-slate-400 block text-[11px]">Seeking Discarded</span>
            <span className="text-amber-400 font-bold text-sm">
              {telemetry ? telemetry.seekingDiscardedCount : '1,794'} filtered
            </span>
          </div>

          <div className="flex items-center gap-2 pl-2">
            <button
              id="refresh-feed-btn"
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors border border-slate-700/50 cursor-pointer"
              title="Refresh radar stream"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>

            <button
              id="ingest-post-trigger-btn"
              onClick={onOpenIngestModal}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl btn-secondary-clay text-xs font-bold transition-all cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-slate-950" />
              <span>Simulate Raw Post</span>
            </button>
          </div>
        </div>
      </div>

      {/* Channel Selector Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-mono uppercase text-slate-400 mr-1 flex items-center gap-1.5">
          <Filter className="w-3 h-3 text-slate-500" />
          Filter Source:
        </span>
        {CHANNELS.map((ch) => {
          const Icon = ch.icon;
          const isActive = selectedChannel === ch.id;
          return (
            <button
              key={ch.id}
              id={`channel-tab-${ch.id}`}
              onClick={() => onSelectChannel(ch.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium transition-all border cursor-pointer ${
                isActive
                  ? 'bg-slate-800 text-cyan-400 border-cyan-400/40 shadow-[0_0_12px_rgba(34,211,238,0.25)] font-bold'
                  : 'bg-slate-900/60 backdrop-blur-md text-slate-400 border-slate-800/60 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
              <span>{ch.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
