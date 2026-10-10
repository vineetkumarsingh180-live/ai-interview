import { useQuery } from '@tanstack/react-query';
import { fetchHealth, HealthStatus } from '../api/health';

export interface BackendStatusItem {
  label: string;
  value: string;
  tone: 'success' | 'warm' | 'danger';
}

/** Live backend status (polled). Unreachable backends are reported, never hidden. */
export function useBackendStatus(): { items: BackendStatusItem[]; summary: BackendStatusItem; isLoading: boolean } {
  const { data, isError, isLoading } = useQuery<HealthStatus>({
    queryKey: ['backend-health'],
    queryFn: fetchHealth,
    refetchInterval: 30000,
    retry: 0,
  });

  if (isError) {
    const down: BackendStatusItem = { label: 'Backend', value: 'Unreachable', tone: 'danger' };
    return { items: [down], summary: down, isLoading: false };
  }
  if (!data) {
    const wait: BackendStatusItem = { label: 'Backend', value: 'Checking…', tone: 'warm' };
    return { items: [wait], summary: wait, isLoading };
  }

  const items: BackendStatusItem[] = [
    { label: 'Backend', value: `v${data.version}`, tone: 'success' },
    {
      label: 'Database',
      value: data.database === 'connected' ? 'Connected' : 'Unreachable',
      tone: data.database === 'connected' ? 'success' : 'danger',
    },
    {
      label: 'AI provider',
      value: data.gemini === 'configured' ? 'Configured' : 'Not configured',
      tone: data.gemini === 'configured' ? 'success' : 'warm',
    },
  ];
  const worst = items.find((i) => i.tone === 'danger') ?? items.find((i) => i.tone === 'warm');
  const summary: BackendStatusItem = worst
    ? { label: worst.label, value: worst.value, tone: worst.tone }
    : { label: 'Backend', value: 'Connected', tone: 'success' };
  return { items, summary, isLoading: false };
}
