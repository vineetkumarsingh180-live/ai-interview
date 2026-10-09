import React, { useState } from 'react';
import { X, Sparkles, Send, Twitter, Linkedin, MessageSquare } from 'lucide-react';

interface SimulateIngestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onIngest: (payload: {
    platform: string;
    authorHandle: string;
    authorName: string;
    rawContent: string;
    sourceChannel: string;
  }) => Promise<any>;
  isIngesting: boolean;
}

const PRESET_POSTS = [
  {
    platform: 'twitter',
    authorHandle: '@sabor_vc',
    authorName: 'Sabor Labs',
    sourceChannel: 'X Core API',
    rawContent:
      'Hiring Staff Distributed Systems Engineer to lead our low-latency Raft consensus clustering engine in Rust. $220k-$280k + 0.25% equity. Remote friendly. DM me directly!',
  },
  {
    platform: 'reddit',
    authorHandle: 'u/solana_core',
    authorName: 'Solana Ecosystem',
    sourceChannel: 'r/rust',
    rawContent:
      'We need a Principal Protocol Engineer with heavy Rust/Wasm experience. $240,000 - $310,000 + token allocation. Onsite in SF or Remote. Contact engineering@solanalabs.com',
  },
  {
    platform: 'twitter',
    authorHandle: '@junior_dev99',
    authorName: 'Alex Smith',
    sourceChannel: 'X Core API',
    rawContent:
      'Hey everyone! I just finished a bootcamp and am currently OPEN TO WORK looking for my first junior web developer position in React and Node. Please hire me! DMs open.',
  },
];

export const SimulateIngestModal: React.FC<SimulateIngestModalProps> = ({
  isOpen,
  onClose,
  onIngest,
  isIngesting,
}) => {
  const [platform, setPlatform] = useState('twitter');
  const [authorHandle, setAuthorHandle] = useState('@founder_steve');
  const [authorName, setAuthorName] = useState('Steve Chen');
  const [rawContent, setRawContent] = useState(PRESET_POSTS[0].rawContent);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawContent.trim()) return;
    await onIngest({
      platform,
      authorHandle,
      authorName,
      rawContent,
      sourceChannel: `${platform.toUpperCase()} Ingestion Pipeline`,
    });
    onClose();
  };

  const loadPreset = (preset: (typeof PRESET_POSTS)[0]) => {
    setPlatform(preset.platform);
    setAuthorHandle(preset.authorHandle);
    setAuthorName(preset.authorName);
    setRawContent(preset.rawContent);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        id="simulate-ingest-modal"
        className="w-full max-w-xl rounded-2xl clay border border-slate-800/80 p-6 shadow-2xl space-y-4 font-sans"
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-400/10 text-cyan-400 border border-cyan-400/30 cyan-glow">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Simulate Social Post Ingestion
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                Test Gemini binary classifier &amp; entity extractor
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl bg-slate-800/80 text-slate-400 hover:text-white border border-slate-700/50 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Quick presets */}
        <div>
          <span className="text-[11px] font-mono text-slate-400 block mb-1.5">
            Load Test Scenarios:
          </span>
          <div className="flex flex-wrap gap-2">
            {PRESET_POSTS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => loadPreset(p)}
                className="px-2.5 py-1.5 rounded-xl bg-slate-900/60 hover:bg-slate-800 text-[11px] font-mono text-slate-300 border border-slate-800/60 transition-colors cursor-pointer"
              >
                {idx === 0
                  ? '🎯 Staff Rust Hiring (Qualified)'
                  : idx === 1
                  ? '⚡ Solana Principal (Qualified)'
                  : '🚫 Job Seeker (Should Filter Out)'}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3 font-mono text-xs">
          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block text-slate-300 mb-1">Platform</label>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/50 text-slate-200 focus:outline-none focus:border-cyan-400"
              >
                <option value="twitter">X / Twitter</option>
                <option value="linkedin">LinkedIn</option>
                <option value="reddit">Reddit</option>
                <option value="telegram">Telegram</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-300 mb-1">Author Handle</label>
              <input
                type="text"
                value={authorHandle}
                onChange={(e) => setAuthorHandle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900/80 border border-slate-700/50 text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 mb-1">Raw Post Text</label>
            <textarea
              rows={4}
              value={rawContent}
              onChange={(e) => setRawContent(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/80 border border-slate-700/50 text-slate-200 resize-none focus:outline-none focus:border-cyan-400"
              required
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isIngesting}
              className="flex items-center gap-2 px-5 py-2 rounded-xl btn-primary-clay font-bold text-slate-950 cursor-pointer"
            >
              {isIngesting ? (
                <>
                  <Sparkles className="w-4 h-4 animate-spin text-slate-950" />
                  <span>Parsing with Gemini...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5 fill-current" />
                  <span>Ingest &amp; Classify</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
