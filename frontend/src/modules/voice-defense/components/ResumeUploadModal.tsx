import React, { useState, useRef } from 'react';
import { Upload, X, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';
import type { VoiceCandidate } from '../types';

interface ResumeUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: VoiceCandidate | null;
  initialResumeText?: string;
  onStartInterview: (params: { resumeText: string }) => void;
  isStarting: boolean;
  error?: string | null;
}

export const ResumeUploadModal: React.FC<ResumeUploadModalProps> = ({
  isOpen,
  onClose,
  candidate,
  initialResumeText = '',
  onStartInterview,
  isStarting,
  error,
}) => {
  const [resumeText, setResumeText] = useState(initialResumeText);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isReadingFile, setIsReadingFile] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setParseError(null);
    setIsReadingFile(true);

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === 'string') {
        // Strip null bytes and non-printable noise if any
        const clean = content.replace(/\0/g, '').trim();
        setResumeText(clean);
      }
      setIsReadingFile(false);
    };
    reader.onerror = () => {
      setParseError('Failed to read file. Please paste your resume text directly below.');
      setIsReadingFile(false);
    };

    // If text-like or pdf, read as text; for PDFs browsers can read raw text streams
    reader.readAsText(file);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStartInterview({
      resumeText: resumeText.trim(),
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <div
        className="card max-h-[90vh] w-full max-w-xl overflow-y-auto p-5 sm:p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="resume-modal-title"
      >
        <div className="flex items-center justify-between border-b border-line pb-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-mocha text-surface">
              <Sparkles className="h-5 w-5" />
            </span>
            <div>
              <h2 id="resume-modal-title" className="text-base font-bold text-ink">
                Start Voice Defense Interview
              </h2>
              <p className="text-xs text-ink-soft">
                Upload your resume to calibrate questions on your background, skills, and project.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-ink-alt hover:bg-canvas-alt hover:text-ink focus-visible:shadow-focus"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Candidate & Project info */}
          <div className="rounded-xl border border-line bg-canvas-alt p-3 text-xs">
            <span className="eyebrow block">Assessment candidate & project</span>
            <p className="mt-0.5 font-bold text-ink">
              {candidate?.name ?? 'Candidate'} {candidate?.targetRole ? `· ${candidate.targetRole}` : ''}
            </p>
            <p className="text-ink-alt">
              Target Repository: <span className="font-semibold text-mocha">{candidate?.repoName ?? 'Submitted project'}</span>
            </p>
          </div>

          {/* Resume Upload Box */}
          <div>
            <label className="field-label block">Upload Resume (.pdf, .txt, .docx, .md)</label>
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-line-strong bg-surface p-4 text-center transition-colors hover:border-mocha hover:bg-canvas-alt"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.docx,.md,.rtf"
                onChange={handleFileChange}
                className="hidden"
              />
              <Upload className="h-6 w-6 text-mocha" />
              <p className="mt-1 text-xs font-semibold text-ink">
                {fileName ? fileName : 'Click to select or drop resume file'}
              </p>
              <p className="text-[11px] text-ink-soft">Supports PDF, Markdown, Plain Text or Word documents</p>
            </div>
          </div>

          {parseError && (
            <p className="flex items-center gap-1.5 rounded-lg border border-danger/30 bg-danger-tint p-2 text-xs text-danger">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{parseError}</span>
            </p>
          )}

          {/* Resume Text Area */}
          <div>
            <div className="flex items-center justify-between">
              <label htmlFor="resume-text-input" className="field-label">
                Resume Content / Key Highlights
              </label>
              {resumeText && (
                <span className="text-[11px] text-success flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Ready
                </span>
              )}
            </div>
            <textarea
              id="resume-text-input"
              rows={5}
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Paste or review your resume here (experience, technical skills, achievements)..."
              className="field font-mono text-xs"
            />
          </div>

          {error && (
            <p className="flex items-center gap-1.5 rounded-lg border border-danger/30 bg-danger-tint p-2 text-xs text-danger">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </p>
          )}

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-line">
            <button type="button" onClick={onClose} className="btn btn-secondary text-xs">
              Cancel
            </button>
            <button
              type="submit"
              disabled={isStarting || isReadingFile}
              className="btn btn-primary text-xs font-bold"
            >
              {isStarting ? 'Starting Interview…' : 'Begin Defense Interview'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
