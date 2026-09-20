import React, { useEffect } from 'react';
import { X, Sparkles, Copy, Check, Send, Bot, Terminal, Sliders, Briefcase, UserCheck } from 'lucide-react';
import { JobLead } from '../../feature1-ingestion/types';
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
    copied,
    copyToClipboard,
  } = useOutreachDraft();

  useEffect(() => {
    if (lead && isOpen) {
      // Auto-trigger initial generation for seamless speed
      generateDraft({
        leadId: lead.id,
        tone,
        candidateProfile,
      }).catch(() => {});
    }
  }, [lead, isOpen]);

  if (!isOpen || !lead) return null;

  const handleRegenerate = () => {
    generateDraft({
      leadId: lead.id,
      tone,
      candidateProfile,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        id="outreach-generator-modal"
        className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl clay border border-slate-800/80 p-6 shadow-2xl flex flex-col justify-between font-sans"
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800/60">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-violet-600/20 text-violet-300 border border-violet-500/40 shadow-[0_0_12px_rgba(124,58,237,0.3)]">
              <Sparkles className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                AI Cold Outreach Synthesizer
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Powered by Gemini 3.8 Flash • Contextual Entity Anchoring
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors border border-slate-700/50 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="space-y-5 my-5">
          {/* Target Lead Summary Box */}
          <div className="p-4 rounded-xl inset-well border border-slate-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider">
                Targeting Role
              </span>
              <h4 className="text-sm font-bold text-white mt-0.5">
                {lead.roleTitle} @ {lead.companyName}
              </h4>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Required Tech: {lead.techStack.join(', ')}
              </p>
            </div>
            <div className="text-left sm:text-right text-xs font-mono">
              <span className="text-slate-400 block text-[10px]">Contact Route</span>
              <span className="text-violet-400 font-semibold">
                {lead.contactAnchor || 'Direct Message'}
              </span>
            </div>
          </div>

          {/* Tone Selector */}
          <div>
            <label className="block text-xs font-mono uppercase text-slate-300 mb-2 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-violet-400" />
              Select Pitch Tone &amp; Posture
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {TONES.map((t) => {
                const Icon = t.icon;
                const isSelected = tone === t.id;
                return (
                  <button
                    key={t.id}
                    onClick={() => setTone(t.id as any)}
                    className={`p-3 rounded-xl text-left transition-all border cursor-pointer ${
                      isSelected
                        ? 'bg-slate-800 text-cyan-400 border-cyan-400/50 shadow-[0_0_15px_rgba(34,211,238,0.2)]'
                        : 'bg-slate-900/60 border-slate-800/60 text-slate-400 hover:bg-slate-800/50 hover:text-white'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`w-4 h-4 ${isSelected ? 'text-cyan-400' : 'text-slate-400'}`} />
                      <span className="text-xs font-bold text-white">{t.label}</span>
                    </div>
                    <p className="text-[10px] leading-relaxed line-clamp-2 text-slate-400">
                      {t.desc}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Candidate Profile Context */}
          <div>
            <label className="block text-xs font-mono uppercase text-slate-300 mb-1.5 flex items-center justify-between">
              <span>Your Technical Background / Proof of Work</span>
              <span className="text-[11px] text-slate-400 normal-case">Injected into LLM context</span>
            </label>
            <textarea
              rows={2}
              value={candidateProfile}
              onChange={(e) => setCandidateProfile(e.target.value)}
              className="w-full px-3.5 py-2.5 text-xs font-mono rounded-xl bg-slate-900/80 border border-slate-800/60 text-slate-200 focus:outline-none focus:border-cyan-400 transition-colors resize-none"
              placeholder="E.g., Principal engineer specializing in zero-copy networking and Raft consensus..."
            />
          </div>

          {/* Generated Output Area */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase text-cyan-400 flex items-center gap-1.5 font-bold">
                <Bot className="w-3.5 h-3.5" />
                Generated Cold Pitch
              </span>
              <button
                onClick={handleRegenerate}
                disabled={isGenerating}
                className="flex items-center gap-1 text-[11px] font-mono text-violet-400 hover:text-white transition-colors cursor-pointer"
              >
                <Sparkles className={`w-3 h-3 ${isGenerating ? 'animate-spin' : ''}`} />
                <span>{isGenerating ? 'Synthesizing...' : 'Regenerate Draft'}</span>
              </button>
            </div>

            {/* Subject Line */}
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800/60 flex items-center justify-between gap-3 text-xs font-mono">
              <div className="truncate">
                <span className="text-slate-400">Subject: </span>
                <span className="text-white font-semibold">
                  {currentDraft?.pitchSubject || `Technical Lead Inquiry - ${lead.roleTitle} @ ${lead.companyName}`}
                </span>
              </div>
              <button
                onClick={() => copyToClipboard(currentDraft?.pitchSubject || '')}
                className="text-slate-400 hover:text-cyan-400 transition-colors p-1 cursor-pointer"
                title="Copy Subject"
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Message Body */}
            <div className="relative p-4 rounded-xl bg-slate-900/80 border border-slate-800/60 text-xs text-slate-200 font-mono whitespace-pre-wrap leading-relaxed min-h-[140px]">
              {isGenerating ? (
                <div className="flex flex-col items-center justify-center h-32 text-slate-400 gap-2">
                  <Sparkles className="w-5 h-5 text-violet-400 animate-spin" />
                  <span>Aligning semantic hooks and engineering background...</span>
                </div>
              ) : (
                currentDraft?.generatedPitch ||
                `Hey ${lead.companyName} Team,\n\nSaw your post for the ${lead.roleTitle} role building with ${lead.techStack.slice(0, 3).join(', ')}. I have deep production experience architecting low-latency distributed systems and optimizing consensus throughput in similar production environments.\n\nWould love to connect and share some benchmarks from recent clustering and raft consensus work.\n\nBest,\nCandidate`
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="pt-4 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-3">
          <div className="text-[11px] font-mono text-slate-400">
            <span className="text-cyan-400 font-semibold">Status:</span> Ready to dispatch to hiring contact
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-xs font-medium text-slate-300 transition-colors border border-slate-700/50 cursor-pointer"
            >
              Close
            </button>

            <button
              onClick={() => {
                const fullText = `Subject: ${currentDraft?.pitchSubject || ''}\n\n${currentDraft?.generatedPitch || ''}`;
                copyToClipboard(fullText);
              }}
              className="flex items-center gap-2 px-5 py-2 rounded-xl btn-primary-clay text-xs font-semibold transition-all active:scale-95 cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-slate-950" />
                  <span>Copied to Clipboard!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-slate-950" />
                  <span>Copy Full Pitch</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
