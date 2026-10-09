import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { JobLead, IngestionTelemetry } from '../types';

export function useLeadStream() {
  const queryClient = useQueryClient();
  const [selectedChannel, setSelectedChannel] = useState<string>('all');
  const [minScore, setMinScore] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const { data: leads = [], isLoading: isLoadingLeads, refetch } = useQuery<JobLead[]>({
    queryKey: ['leads', selectedChannel, minScore],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedChannel !== 'all') params.append('platform', selectedChannel);
      if (minScore > 0) params.append('min_score', minScore.toString());
      const res = await fetch(`/api/v1/leads/ingest/recent?${params.toString()}`);
      if (!res.ok) throw new Error('Failed to fetch leads');
      return res.json();
    },
    refetchInterval: 12000,
  });

  const { data: telemetry } = useQuery<IngestionTelemetry>({
    queryKey: ['telemetry'],
    queryFn: async () => {
      const res = await fetch('/api/v1/leads/ingest/telemetry');
      if (!res.ok) throw new Error('Failed to fetch telemetry');
      return res.json();
    },
    refetchInterval: 8000,
  });

  const ingestMutation = useMutation({
    mutationFn: async (payload: {
      platform: string;
      authorHandle: string;
      authorName: string;
      rawContent: string;
      sourceChannel: string;
    }) => {
      const res = await fetch('/api/v1/leads/ingest/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: payload.platform,
          external_id: `ext_${Date.now()}`,
          author_handle: payload.authorHandle,
          author_name: payload.authorName,
          raw_content: payload.rawContent,
          source_channel: payload.sourceChannel,
        }),
      });
      if (!res.ok) throw new Error('Failed to trigger ingestion');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['telemetry'] });
    },
  });

  const filteredLeads = leads.filter((lead) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesTitle = lead.roleTitle.toLowerCase().includes(q);
      const matchesCompany = lead.companyName.toLowerCase().includes(q);
      const matchesTech = lead.techStack.some((t) => t.toLowerCase().includes(q));
      if (!matchesTitle && !matchesCompany && !matchesTech) return false;
    }
    return true;
  });

  return {
    leads: filteredLeads,
    telemetry,
    isLoadingLeads,
    selectedChannel,
    setSelectedChannel,
    minScore,
    setMinScore,
    searchQuery,
    setSearchQuery,
    triggerIngest: ingestMutation.mutateAsync,
    isIngesting: ingestMutation.isPending,
    refetchLeads: refetch,
  };
}
