import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { JobLead } from '../../feature1-ingestion/types';

export interface OutreachDraft {
  id: string;
  leadId: string;
  tone: 'Direct Technical' | 'Executive' | 'Casual Founder';
  pitchSubject: string;
  generatedPitch: string;
  candidateProfileContext?: string;
  status: string;
  modelVersion: string;
  createdAt: string;
}

export function useOutreachDraft() {
  const [selectedLead, setSelectedLead] = useState<JobLead | null>(null);
  const [tone, setTone] = useState<'Direct Technical' | 'Executive' | 'Casual Founder'>('Direct Technical');
  const [candidateProfile, setCandidateProfile] = useState<string>(
    'Principal Distributed Systems Engineer with 8+ years experience scaling consensus clusters, low-latency zero-copy networking, and Raft consensus engines in Rust and Go.'
  );
  const [copied, setCopied] = useState<boolean>(false);

  const generateMutation = useMutation<OutreachDraft, Error, { leadId: string; tone: string; candidateProfile: string }>({
    mutationFn: async ({ leadId, tone, candidateProfile }) => {
      const res = await fetch('/api/v1/leads/outreach/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lead_id: leadId,
          tone,
          candidate_profile_context: candidateProfile,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Generation failed' }));
        throw new Error(err.detail || 'Failed to generate outreach pitch');
      }
      return res.json();
    },
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return {
    selectedLead,
    setSelectedLead,
    tone,
    setTone,
    candidateProfile,
    setCandidateProfile,
    generateDraft: generateMutation.mutateAsync,
    isGenerating: generateMutation.isPending,
    currentDraft: generateMutation.data,
    generationError: generateMutation.error,
    copied,
    copyToClipboard,
  };
}
