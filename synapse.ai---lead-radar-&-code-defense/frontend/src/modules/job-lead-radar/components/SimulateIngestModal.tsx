import React, { useEffect, useState } from 'react';
import { X, Send, Loader2, AlertCircle, CheckCircle2, Info } from 'lucide-react';
import type { IngestOutcome } from '../types';

interface SimulateIngestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onIngest: (payload: {
    platform: string;
    authorHandle: string;
    authorName: string;
    rawContent: string;
    sourceChannel: string;
  }) => Promise<IngestOutcome>;
  isIngesting: boolean;
}

const PRESET_POSTS = [
  {
    label: 'Hiring post (sample)',
    platform: 'twitter',
    authorHandle: '@sample_founder',
    authorName: 'Sample Founder',
    sourceChannel: 'Manual import',
    rawContent:
      'Hiring a Staff Distributed Systems Engineer to lead our consensus engine in Rust. $220k-$280k + 0.25% equity. Remote friendly. DM me directly!',
  },
  {
    label: 'Job seeker (sample)',
    platform: 'twitter',
    authorHandle: '@sample_dev',
    authorName: 'Sample Developer',
    sourceChannel: 'Manual import',
    rawContent:
      'Hey everyone! I just finished a bootcamp and am currently OPEN TO WORK looking for my first junior web developer position in React and Node. Please hire me! DMs open.',
  },
];

const OUTCOME_COPY: Record<IngestOutcome['status'], { title: string; tone: 'success' | 'info' }> = {
  created: { title: 'Lead created', tone: 'success' },
  discarded: { title: 'Not a hiring post (no lead created)', tone: 'info' },
  awaiting_analysis: { title: 'Saved, awaiting analysis', tone: 'info' },
  needs_review: { title: 'Saved, needs human review', tone: 'info' },
};

export const SimulateIngestModal: React.FC<SimulateIngestModalProps> = ({
  isOpen,
  onClose,
  onIngest,
  isIngesting,
}) => {
  const [platform, setPlatform] = useState('twitter');
  const [authorHandle, setAuthorHandle] = useState('');
  const [authorName, setAuthorName] = useState('');
  const [rawContent, setRawContent] = useState('');
  const [outcome, setOutcome] = useState<IngestOutcome | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  // Start every opening with a clean result panel.
  useEffect(() => {
    if (isOpen) {
      setOutcome(null);
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawContent.trim()) return;
    setError(null);
    setOutcome(null);
    try {
      const result = await onIngest({
        platform,
        authorHandle,
        authorName,
        rawContent,
        sourceChannel: 'Manual import',
      });
      setOutcome(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The post could not be submitted.');
    }
  };

  const loadPreset = (preset: (typeof PRESET_POSTS)[0]) => {
    setPlatform(preset.platform);
    setAuthorHandle(preset.authorHandle);
    setAuthorName(preset.authorName);
    setRawContent(preset.rawContent);
    setOutcome(null);
    setError(null);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-scrim p-0 sm:items-center sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        id="simulate-ingest-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="simulate-ingest-title"
        className="modal-panel max-h-[92dvh] w-full max-w-xl space-y-4 overflow-y-auto rounded-t-2xl p-4 sm:rounded-2xl sm:p-6"
      >
        <div className="flex items-start justify-between gap-3 border-b border-line pb-3">
          <div className="min-w-0">
            <h3 id="simulate-ingest-title" className="text-base font-bold text-ink">
              Import a social post
            </h3>
            <p className="text-sm text-ink-soft">
              The post is stored, then analysed to decide whether it is a hiring lead.
            </p>
          </div>
          <button type="button" onClick={onClose} className="btn btn-secondary btn-icon shrink-0" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div>
          <span className="field-label">Fill with a sample</span>
          <div className="flex flex-wrap gap-2">
            {PRESET_POSTS.map((p) => (
              <button key={p.label} type="button" onClick={() => loadPreset(p)} className="chip">
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="ingest-platform" className="field-label">
                Platform
              </label>
              <select id="ingest-platform" value={platform} onChange={(e) => setPlatform(e.target.value)} className="field">
                <option value="twitter">X / Twitter</option>
                <option value="linkedin">LinkedIn</option>
                <option value="reddit">Reddit</option>
                <option value="telegram">Telegram</option>
              </select>
            </div>
            <div>
              <label htmlFor="ingest-handle" className="field-label">
                Author handle (optional)
              </label>
              <input
                id="ingest-handle"
                type="text"
                value={authorHandle}
                onChange={(e) => setAuthorHandle(e.target.value)}
                className="field"
              />
            </div>
          </div>

          <div>
            <label htmlFor="ingest-content" className="field-label">
              Post text
            </label>
            <textarea
              id="ingest-content"
              rows={5}
              value={rawContent}
              onChange={(e) => setRawContent(e.target.value)}
              className="field resize-y"
              required
              maxLength={20000}
            />
          </div>

          {error && (
            <p role="alert" className="flex items-start gap-2 rounded-lg border border-danger/30 bg-danger-tint p-2.5 text-sm text-danger">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          {outcome && (
            <div
              role="status"
              className={`flex items-start gap-2 rounded-lg border p-2.5 text-sm ${
                OUTCOME_COPY[outcome.status].tone === 'success'
                  ? 'border-success/30 bg-success-tint text-success'
                  : 'border-line-strong bg-canvas-alt text-ink'
              }`}
            >
              {OUTCOME_COPY[outcome.status].tone === 'success' ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              ) : (
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
              )}
              <span>
                <strong>{OUTCOME_COPY[outcome.status].title}.</strong>
                {outcome.reason ? ` ${outcome.reason}` : ''}
              </span>
            </div>
          )}

          <div className="flex flex-col-reverse gap-2 pt-1 sm:flex-row sm:justify-end">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              {outcome ? 'Done' : 'Cancel'}
            </button>
            <button type="submit" disabled={isIngesting} className="btn btn-primary">
              {isIngesting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analysing…</span>
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  <span>Submit post</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
