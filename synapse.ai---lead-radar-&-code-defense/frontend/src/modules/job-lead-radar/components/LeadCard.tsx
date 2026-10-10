import React from 'react';
import { Twitter, Linkedin, MessageSquare, Send, Zap, DollarSign, MapPin, Sparkles, ArrowRight, ShieldCheck, Clock } from 'lucide-react';
import { JobLead } from '../types';

interface LeadCardProps {
  lead: JobLead;
  onDraftOutreach: (lead: JobLead) => void;
}

const platformIcon = (platform: string) => {
  const cls = 'h-3.5 w-3.5 text-mocha';
  switch (platform.toLowerCase()) {
    case 'twitter':
    case 'x':
      return <Twitter className={cls} />;
    case 'linkedin':
      return <Linkedin className={cls} />;
    case 'reddit':
      return <MessageSquare className={cls} />;
    case 'telegram':
      return <Send className={cls} />;
    default:
      return <Zap className={cls} />;
  }
};

export const LeadCard: React.FC<LeadCardProps> = ({ lead, onDraftOutreach }) => {
  const formattedComp = () => {
    const cur = lead.compCurrency ? ` ${lead.compCurrency}` : '';
    if (lead.compMin != null && lead.compMax != null) {
      return `${(lead.compMin / 1000).toFixed(0)}k – ${(lead.compMax / 1000).toFixed(0)}k${cur}`;
    }
    if (lead.compMin != null) {
      return `${(lead.compMin / 1000).toFixed(0)}k+${cur}`;
    }
    return 'Compensation not stated';
  };

  const snippet = lead.rawPost?.rawContent || lead.enrichmentMetadata?.summary;

  return (
    <article
      id={`lead-card-${lead.id}`}
      className="card card-hover group flex min-w-0 flex-col justify-between gap-4 p-4 sm:p-5"
    >
      <div className="min-w-0 space-y-3">
        {/* Source + match */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <span className="badge badge-neutral">
              {platformIcon(lead.rawPost?.platform || '')}
              <span className="capitalize">{lead.rawPost?.platform || 'Unknown source'}</span>
            </span>
            {lead.rawPost?.authorHandle && (
              <span className="truncate text-xs text-ink-soft">{lead.rawPost.authorHandle}</span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {lead.urgencyTier === 'Immediate' && (
              <span className="badge badge-warm">
                <Clock className="h-3 w-3" />
                Immediate
              </span>
            )}
            {lead.isDemo && (
              <span className="badge badge-warm" title="Development fixture, not a real lead.">
                Demo fixture
              </span>
            )}
            <span className="badge badge-neutral" title="No matching model exists yet.">
              <Zap className="h-3 w-3" />
              {lead.matchScore != null ? `${lead.matchScore.toFixed(1)}% match` : 'Match not measured'}
            </span>
          </div>
        </div>

        {/* Role + company */}
        <div className="min-w-0">
          <h3 className="break-words text-lg font-bold leading-snug text-ink group-hover:text-mocha">{lead.roleTitle}</h3>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-sm">
            <span className="font-medium text-mocha">{lead.companyName}</span>
            {lead.companyStage && (
              <>
                <span className="text-ink-soft" aria-hidden="true">•</span>
                <span className="text-ink-soft">{lead.companyStage}</span>
              </>
            )}
          </p>
        </div>

        {/* Comp + location */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 rounded-lg border border-line bg-canvas-alt px-2.5 py-1 font-semibold text-ink">
            <DollarSign className="h-3.5 w-3.5 text-warm" />
            {formattedComp()}
            {lead.equityNote && <span className="font-medium text-ink-alt">{lead.equityNote}</span>}
          </span>
          {lead.locationMode && (
            <span className="inline-flex items-center gap-1 rounded-lg border border-line bg-canvas-alt px-2.5 py-1 text-ink">
              <MapPin className="h-3.5 w-3.5 text-warm" />
              {lead.locationMode}
            </span>
          )}
          {lead.clearanceRequired && (
            <span className="badge badge-warm">
              <ShieldCheck className="h-3 w-3" />
              Clearance
            </span>
          )}
        </div>

        {/* Source text */}
        {snippet && (
          <blockquote className="well p-3 text-sm leading-relaxed text-ink">
            <p className="line-clamp-3 break-words">“{snippet}”</p>
          </blockquote>
        )}

        {/* Stack */}
        <ul className="flex flex-wrap gap-1.5" aria-label="Tech stack">
          {lead.techStack.slice(0, 6).map((tech, i) => (
            <li key={i} className="rounded-md border border-line-strong bg-surface px-2 py-0.5 text-xs text-ink">
              {tech}
            </li>
          ))}
          {lead.techStack.length > 6 && (
            <li className="px-1.5 py-0.5 text-xs text-ink-soft">+{lead.techStack.length - 6} more</li>
          )}
        </ul>
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
        <p className="min-w-0 flex-1 basis-40 break-words text-xs text-ink-soft">
          <span className="font-semibold text-ink-alt">Contact: </span>
          {lead.contactAnchor || 'Not stated'}
        </p>
        <button
          id={`draft-outreach-${lead.id}`}
          type="button"
          onClick={() => onDraftOutreach(lead)}
          className="btn btn-primary shrink-0"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Draft pitch</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </article>
  );
};
