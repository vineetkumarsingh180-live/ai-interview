import React from 'react';
import { Twitter, Linkedin, MessageSquare, Send, Zap, DollarSign, MapPin, Sparkles, ArrowRight, ShieldCheck, Clock } from 'lucide-react';
import { JobLead } from '../types';

interface LeadCardProps {
  lead: JobLead;
  onDraftOutreach: (lead: JobLead) => void;
}

export const LeadCard: React.FC<LeadCardProps> = ({ lead, onDraftOutreach }) => {
  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'twitter':
      case 'x':
        return <Twitter className="w-3.5 h-3.5 text-[#60ffcf]" />;
      case 'linkedin':
        return <Linkedin className="w-3.5 h-3.5 text-[#0077b5]" />;
      case 'reddit':
        return <MessageSquare className="w-3.5 h-3.5 text-[#ff4500]" />;
      case 'telegram':
        return <Send className="w-3.5 h-3.5 text-[#229ed9]" />;
      default:
        return <Zap className="w-3.5 h-3.5 text-[#cbbeff]" />;
    }
  };

  const formattedComp = () => {
    if (lead.compMin && lead.compMax) {
      return `$${(lead.compMin / 1000).toFixed(0)}k - $${(lead.compMax / 1000).toFixed(0)}k ${lead.compCurrency}`;
    }
    if (lead.compMin) {
      return `$${(lead.compMin / 1000).toFixed(0)}k+ ${lead.compCurrency}`;
    }
    return 'Top-of-Market Comp';
  };

  return (
    <div
      id={`lead-card-${lead.id}`}
      className="clay p-5 clay-card-hover border border-slate-800/60 transition-all duration-300 flex flex-col justify-between group font-sans"
    >
      <div>
        {/* Header: Platform & Match Score */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-slate-950/70 text-slate-300 border border-slate-700/50">
              {getPlatformIcon(lead.rawPost?.platform || 'twitter')}
              <span className="capitalize">{lead.rawPost?.platform || 'Social'}</span>
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {lead.rawPost?.authorHandle || '@founder'}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {lead.urgencyTier === 'Immediate' && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-red-950/40 text-red-400 border border-red-500/30 animate-pulse">
                <Clock className="w-3 h-3" />
                Immediate
              </span>
            )}
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-cyan-400/10 text-cyan-400 border border-cyan-400/30 cyan-glow">
              <Zap className="w-3 h-3 fill-current" />
              {lead.matchScore.toFixed(1)}% Match
            </span>
          </div>
        </div>

        {/* Role & Company */}
        <div className="mb-3">
          <h3 className="text-lg font-bold text-white group-hover:text-cyan-400 transition-colors leading-snug">
            {lead.roleTitle}
          </h3>
          <p className="text-xs font-medium text-violet-400 flex items-center gap-1.5 mt-0.5">
            <span>{lead.companyName}</span>
            {lead.companyStage && (
              <>
                <span className="text-slate-500">•</span>
                <span className="text-slate-400">{lead.companyStage}</span>
              </>
            )}
          </p>
        </div>

        {/* Comp and Location badges */}
        <div className="flex flex-wrap items-center gap-2 mb-4 text-xs font-mono">
          <span className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-950/60 text-cyan-400 border border-slate-800/60 font-semibold">
            <DollarSign className="w-3.5 h-3.5" />
            {formattedComp()}
            {lead.equityNote && (
              <span className="text-violet-400 ml-1">{lead.equityNote}</span>
            )}
          </span>

          <span className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-950/60 text-slate-300 border border-slate-800/60">
            <MapPin className="w-3.5 h-3.5 text-amber-400" />
            {lead.locationMode}
          </span>

          {lead.clearanceRequired && (
            <span className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 text-amber-400 border border-amber-400/20 text-[10px]">
              <ShieldCheck className="w-3 h-3" />
              Clearance
            </span>
          )}
        </div>

        {/* Raw Post snippet / extraction summary */}
        <div className="p-3 rounded-xl inset-well border border-slate-800/50 mb-4 text-xs text-slate-300 leading-relaxed font-mono">
          <p className="line-clamp-3">
            "{lead.rawPost?.rawContent || lead.enrichmentMetadata?.summary || 'Targeting experienced systems engineers for core protocol development.'}"
          </p>
        </div>

        {/* Tech Stack Pills */}
        <div className="flex flex-wrap gap-1.5 mb-5">
          {lead.techStack.slice(0, 6).map((tech, i) => (
            <span
              key={i}
              className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800/70 text-slate-300 border border-slate-700/50"
            >
              {tech}
            </span>
          ))}
          {lead.techStack.length > 6 && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-400">
              +{lead.techStack.length - 6} more
            </span>
          )}
        </div>
      </div>

      {/* Footer Contact & Action */}
      <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between gap-3">
        <div className="text-[11px] text-slate-400 truncate">
          <span className="text-slate-400">Anchor: </span>
          <span className="font-mono text-cyan-400">{lead.contactAnchor || 'Direct Message'}</span>
        </div>

        <button
          id={`draft-outreach-${lead.id}`}
          onClick={() => onDraftOutreach(lead)}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl btn-primary-clay text-xs font-semibold whitespace-nowrap transition-transform active:scale-95 cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Draft Pitch</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
