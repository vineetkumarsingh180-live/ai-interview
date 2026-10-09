import { useQuery } from '@tanstack/react-query';

export interface LeaderboardItem {
  id: string;
  sessionId: string;
  candidateName: string;
  candidateAvatarUrl?: string;
  candidateHandle: string;
  targetRole: string;
  repoName: string;
  codeHealthScore: number;
  voiceDefenseScore: number;
  compositePercentile: number;
  rankTier: string;
  statusTag: string;
  recordedAt: string;
}

export function useLeaderboard() {
  const { data: leaderboard = [], isLoading, refetch } = useQuery<LeaderboardItem[]>({
    queryKey: ['leaderboard'],
    queryFn: async () => {
      const res = await fetch('/api/v1/assessment/voice/leaderboard');
      if (!res.ok) throw new Error('Failed to fetch leaderboard');
      return res.json();
    },
    refetchInterval: 10000,
  });

  return {
    leaderboard,
    isLoading,
    refetch,
  };
}
