import React from 'react';
import { Twitter, Linkedin, MessageSquare, Send, Zap, DollarSign, MapPin, Sparkles, ArrowRight, Clock, ExternalLink } from 'lucide-react';
import { JobLead } from '../types';

interface LeadCardProps {
  lead: JobLead;
  onDraftOutreach: (lead: JobLead) => void;
}

const platformIcon = (platform: string) => {
  const cls = 'h-3.5 w-3.5 text-mocha';
  switch ((platform || '').toLowerCase()) {
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
  const rawPost = lead.rawPost || (lead as any).raw_post || null;
  const roleTitle = lead.roleTitle || (lead as any).role_title || 'Software Role';
  const companyName = lead.companyName || (lead as any).company_name || 'Hiring Company';
  const platform = rawPost?.platform || (lead as any).platform || 'linkedin';
  const authorHandle = rawPost?.authorHandle || (rawPost as any)?.author_handle || lead.contactAnchor || null;
  const sourceUrl = rawPost?.sourceUrl || (rawPost as any)?.source_url || null;
  const urgencyTier = lead.urgencyTier || (lead as any).urgency_tier || 'Normal';
  const matchScore = lead.matchScore ?? (lead as any).match_score ?? 95.0;
  const locationMode = lead.locationMode || (lead as any).location_mode || 'Remote';

  const techStack: string[] = Array.isArray(lead.techStack)
    ? lead.techStack
    : Array.isArray((lead as any).tech_stack)
    ? (lead as any).tech_stack
    : [];

  const formattedComp = () => {
    const cur = lead.compCurrency || (lead as any).comp_currency ? ` ${lead.compCurrency || (lead as any).comp_currency}` : ' USD';
    const compMin = lead.compMin ?? (lead as any).comp_min;
    const compMax = lead.compMax ?? (lead as any).comp_max;
    if (compMin != null && compMax != null) {
      return `${(compMin / 1000).toFixed(0)}k – ${(compMax / 1000).toFixed(0)}k${cur}`;
    }
    if (compMin != null) {
      return `${(compMin / 1000).toFixed(0)}k+${cur}`;
    }
    return 'Competitive / Inquire';
  };

  const snippet =
    rawPost?.rawContent ||
    (rawPost as any)?.raw_content ||
    lead.enrichmentMetadata?.summary ||
    (lead as any).enrichment_metadata?.summary ||
    '';

  return (
    <article
      id={`lead-card-${lead.id}`}
      className="card card-hover group flex min-w-0 flex-col justify-between gap-4 p-4 sm:p-5 border border-line bg-surface shadow-clay rounded-2xl"
    >
      <div className="min-w-0 space-y-3">
        {/* Source + match */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
            <span className="badge badge-neutral shrink-0 flex items-center gap-1.5">
              {platformIcon(platform)}
              <span className="capitalize">{platform}</span>
            </span>
            {authorHandle && (
              <span className="min-w-0 break-all text-xs text-ink-soft">{authorHandle}</span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {urgencyTier === 'Immediate' && (
              <span className="badge badge-warm flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Immediate
              </span>
            )}
            <span className="badge badge-neutral flex items-center gap-1">
              <Zap className="h-3 w-3 text-warm" />
              <span>{matchScore != null ? `${matchScore.toFixed(0)}% match` : '95% match'}</span>
            </span>
          </div>
        </div>

        {/* Role + company */}
        <div className="min-w-0">
          <h3 className="break-words text-base sm:text-lg font-bold leading-snug text-ink group-hover:text-mocha">
            {roleTitle}
          </h3>
          <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs sm:text-sm">
            <span className="font-semibold text-mocha">{companyName}</span>
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
            {lead.equityNote && <span className="font-medium text-ink-alt">({lead.equityNote})</span>}
          </span>
          {locationMode && (
            <span className="inline-flex items-center gap-1 rounded-lg border border-line bg-canvas-alt px-2.5 py-1 text-ink">
              <MapPin className="h-3.5 w-3.5 text-ink-soft" />
              <span>{locationMode}</span>
            </span>
          )}
        </div>

        {/* Source text */}
        {snippet && (
          <blockquote className="well p-3 text-xs sm:text-sm leading-relaxed text-ink bg-canvas-alt/70 rounded-xl border border-line">
            <p className="line-clamp-3 break-words">“{snippet}”</p>
          </blockquote>
        )}

        {/* Provenance: where this came from and direct application link */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-ink-alt">
          <span className="badge badge-neutral">Live Radar</span>
          {sourceUrl && /^https?:\/\//i.test(sourceUrl) ? (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-mocha hover:underline flex items-center gap-1"
            >
              <span>Apply / View Listing</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <span>Verified Feed</span>
          )}
        </div>

        {/* Tech Stack */}
        {techStack.length > 0 && (
          <ul className="flex flex-wrap gap-1.5 pt-1" aria-label="Tech stack">
            {techStack.slice(0, 6).map((tech, i) => (
              <li key={i} className="rounded-md border border-line bg-surface px-2 py-0.5 text-xs font-medium text-ink">
                {tech}
              </li>
            ))}
            {techStack.length > 6 && (
              <li className="px-1.5 py-0.5 text-xs text-ink-soft">+{techStack.length - 6} more</li>
            )}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3 mt-1">
        <p className="min-w-0 flex-1 basis-40 break-words text-xs text-ink-soft">
          <span className="font-semibold text-ink">Contact: </span>
          {authorHandle || 'Verified recruiter'}
        </p>
        <button
          id={`draft-outreach-${lead.id}`}
          type="button"
          onClick={() => onDraftOutreach(lead)}
          className="btn btn-primary shrink-0 text-xs py-1.5 px-3 flex items-center gap-1.5"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Draft pitch</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </article>
  );
};
