import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchLeads, fetchTelemetry, ingestPost } from '../api';
import type { JobLead, IngestionTelemetry } from '../types';

export function useLeadStream() {
  const queryClient = useQueryClient();
  const [selectedChannel, setSelectedChannel] = useState<string>('all');
  const [minScore, setMinScore] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const {
    data: leads = [],
    isLoading: isLoadingLeads,
    isError: isLeadsError,
    error: leadsError,
    refetch,
  } = useQuery<JobLead[]>({
    queryKey: ['leads', selectedChannel, minScore],
    queryFn: () => fetchLeads({ platform: selectedChannel, minScore }),
    refetchInterval: 12000,
  });

  const { data: telemetry } = useQuery<IngestionTelemetry>({
    queryKey: ['telemetry'],
    queryFn: fetchTelemetry,
    refetchInterval: 8000,
  });

  const ingestMutation = useMutation({
    mutationFn: ingestPost,
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
    leadsError: isLeadsError ? (leadsError as Error) : null,
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
