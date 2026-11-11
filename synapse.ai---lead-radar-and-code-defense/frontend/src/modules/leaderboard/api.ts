// HTTP client for the Leaderboard module's endpoints.
import { requestJson } from '@shared/api/client';
import type { LeaderboardItem } from './types';

export function fetchLeaderboard(): Promise<LeaderboardItem[]> {
  return requestJson<LeaderboardItem[]>('/api/v1/assessment/voice/leaderboard', {
    errorMessage: 'Failed to fetch leaderboard',
  });
}
