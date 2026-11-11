import { useQuery } from '@tanstack/react-query';
import { fetchLeaderboard } from '../api';
import type { LeaderboardItem } from '../types';

/** React Query key. Exported so a host can invalidate the leaderboard after another module publishes. */
export const LEADERBOARD_QUERY_KEY = ['leaderboard'] as const;

export function useLeaderboard() {
  const {
    data: leaderboard = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<LeaderboardItem[]>({
    queryKey: LEADERBOARD_QUERY_KEY,
    queryFn: fetchLeaderboard,
    refetchInterval: 10000,
  });

  return {
    leaderboard,
    isLoading,
    error: isError ? (error as Error) : null,
    refetch,
  };
}
