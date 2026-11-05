import React, { useEffect } from 'react';
import { X, Sparkles, Copy, Check, Terminal, Briefcase, UserCheck, Loader2, AlertCircle } from 'lucide-react';
import { JobLead } from '../types';
import { useOutreachDraft } from '../hooks/useOutreachDraft';

interface OutreachModalProps {
  lead: JobLead | null;
  isOpen: boolean;
  onClose: () => void;
}

const TONES = [
  {
    id: 'Direct Technical',
    label: 'Direct Technical',
    desc: 'Systems engineering focus, zero fluff, highlights consensus & architectural trade-offs.',
    icon: Terminal,
  },
  {
    id: 'Executive',
    label: 'Executive',
    desc: 'Strategic impact, business velocity, engineering team leadership & scale.',
    icon: Briefcase,
  },
  {
    id: 'Casual Founder',
    label: 'Casual Founder',
    desc: 'High agency, conversational startup speed, direct builder rapport.',
    icon: UserCheck,
  },
];

export const OutreachModal: React.FC<OutreachModalProps> = ({ lead, isOpen, onClose }) => {
  const {
    tone,
    setTone,
    candidateProfile,
    setCandidateProfile,
    generateDraft,
    isGenerating,
    currentDraft,
    generationError,
    copied,
    copyToClipboard,
  } = useOutreachDraft();

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen || !lead) return null;

  const handleRegenerate = () => {
    // The failure is shown from `generationError`; swallow the rejection so it is not "uncaught".
    generateDraft({
      leadId: lead.id,
      tone,
      candidateProfile,
    }).catch(() => {});
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-scrim p-0 sm:items-center sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        id="outreach-generator-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="outreach-title"
        className="modal-panel flex max-h-[92dvh] w-full max-w-3xl flex-col overflow-hidden rounded-t-2xl sm:rounded-2xl"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 border-b border-line p-4 sm:px-6">
          <div className="min-w-0">
            <h2 id="outreach-title" className="text-lg font-bold text-ink">
              Outreach draft
            </h2>
            <p className="text-sm text-ink-soft">Review and edit before using. Nothing is sent from this app.</p>
          </div>
          <button type="button" onClick={onClose} className="btn btn-secondary btn-icon shrink-0" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4 sm:px-6">
          <div className="well flex flex-col justify-between gap-3 p-4 sm:flex-row sm:items-center">
            <div className="min-w-0">
              <span className="eyebrow">Targeting role</span>
              <h4 className="mt-0.5 break-words text-sm font-bold text-ink">
                {lead.roleTitle} @ {lead.companyName}
              </h4>
              <p className="mt-0.5 break-words text-xs text-ink-alt">Required tech: {lead.techStack.join(', ')}</p>
            </div>
            <div className="min-w-0 text-xs sm:max-w-[16rem] sm:text-right">
              <span className="eyebrow block">Contact route</span>
              <span className="break-words font-semibold text-ink">{lead.contactAnchor || 'Not stated'}</span>
            </div>
          </div>

          {/* Tone */}
          <fieldset>
            <legend className="field-label">Pitch tone</legend>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {TONES.map((t) => {
                const Icon = t.icon;
                const isSelected = tone === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => setTone(t.id as any)}
                    className={`cursor-pointer rounded-xl border p-3 text-left transition-colors focus-visible:shadow-focus ${
                      isSelected
                        ? 'border-mocha bg-mocha-tint text-ink'
                        : 'border-line-strong bg-surface text-ink hover:bg-canvas-alt'
                    }`}
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <Icon className={`h-4 w-4 ${isSelected ? 'text-mocha' : 'text-ink-soft'}`} />
                      <span className="text-sm font-semibold">{t.label}</span>
                    </div>
                    <p className={`text-xs leading-relaxed ${isSelected ? 'text-ink-alt' : 'text-ink-soft'}`}>{t.desc}</p>
                  </button>
                );
              })}
            </div>
            <p className="mt-1.5 text-xs text-ink-soft">Choose the tone, add your background, then generate a draft.</p>
          </fieldset>

          {/* Profile */}
          <div>
            <label htmlFor="outreach-profile" className="field-label">
              Your background (sent with the request; the AI is told not to invent anything beyond it)
            </label>
            <textarea
              id="outreach-profile"
              rows={3}
              value={candidateProfile}
              onChange={(e) => setCandidateProfile(e.target.value)}
              className="field resize-y"
              placeholder="Facts about you the message may use: roles, projects, years of experience"
            />
          </div>

          {/* Output */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <span className="eyebrow">Generated pitch</span>
              <button
                type="button"
                onClick={handleRegenerate}
                disabled={isGenerating}
                className="btn btn-secondary min-h-9 px-3 py-1.5"
              >
                {isGenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                <span>{isGenerating ? 'Generating…' : currentDraft ? 'Regenerate' : 'Generate draft'}</span>
              </button>
            </div>

            {generationError && (
              <p role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2.5 text-sm text-danger">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{generationError.message}</span>
              </p>
            )}
            {currentDraft && !isGenerating && (
              <p className="text-xs text-ink-soft">Generated by {currentDraft.modelVersion}. Review before using.</p>
            )}

            <div className="flex items-center justify-between gap-3 rounded-xl border border-line-strong bg-surface p-3 text-sm">
              <div className="min-w-0 break-words">
                <span className="text-ink-soft">Subject: </span>
                <span className="font-semibold text-ink">{currentDraft?.pitchSubject || 'No draft yet'}</span>
              </div>
              <button
                type="button"
                onClick={() => copyToClipboard(currentDraft?.pitchSubject || '')}
                className="btn btn-secondary btn-icon h-9 w-9 min-h-0 shrink-0"
                title="Copy subject"
                aria-label="Copy subject"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>

            <div className="min-h-[140px] whitespace-pre-wrap break-words rounded-xl border border-line-strong bg-surface p-4 text-sm leading-relaxed text-ink">
              {isGenerating ? (
                <div className="flex h-32 flex-col items-center justify-center gap-2 text-ink-soft">
                  <Loader2 className="h-5 w-5 animate-spin text-mocha" />
                  <span>Generating draft…</span>
                </div>
              ) : (
                currentDraft?.generatedPitch || (
                  <span className="text-ink-soft">
                    No draft yet. Drafts are written by the AI provider; nothing is shown until one is generated.
                  </span>
                )
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex flex-col-reverse gap-2 border-t border-line bg-canvas-alt p-4 sm:flex-row sm:items-center sm:justify-end sm:px-6">
          <button type="button" onClick={onClose} className="btn btn-secondary">
            Close
          </button>
          <button
            type="button"
            onClick={() => {
              const fullText = `Subject: ${currentDraft?.pitchSubject || ''}\n\n${currentDraft?.generatedPitch || ''}`;
              copyToClipboard(fullText);
            }}
            disabled={!currentDraft}
            className="btn btn-primary"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                <span>Copy full pitch</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
