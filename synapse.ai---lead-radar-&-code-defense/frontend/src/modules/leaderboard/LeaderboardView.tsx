import React from 'react';
import { LeaderboardTable } from './components/LeaderboardTable';
import { useLeaderboard } from './hooks/useLeaderboard';

/** Self-contained: owns its data fetching. */
export const LeaderboardView: React.FC = () => {
  const { leaderboard, isLoading, error, refetch } = useLeaderboard();
  return <LeaderboardTable leaderboard={leaderboard} isLoading={isLoading} error={error?.message ?? null} onRetry={() => refetch()} />;
};
