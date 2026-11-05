import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { generateOutreachDraft } from '../api';
import type { JobLead, OutreachDraft, OutreachTone } from '../types';

export type { OutreachDraft };

export function useOutreachDraft() {
  const [selectedLead, setSelectedLead] = useState<JobLead | null>(null);
  const [tone, setTone] = useState<OutreachTone>('Direct Technical');
  const [candidateProfile, setCandidateProfile] = useState<string>('');
  const [copied, setCopied] = useState<boolean>(false);

  const generateMutation = useMutation<OutreachDraft, Error, { leadId: string; tone: string; candidateProfile: string }>({
    mutationFn: generateOutreachDraft,
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
