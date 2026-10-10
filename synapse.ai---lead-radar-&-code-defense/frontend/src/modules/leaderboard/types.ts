// Mirrors the backend OpenAPI contract (camelCase). `null` always means "not measured".
export interface LeaderboardItem {
  id: string;
  sessionId: string;
  candidateName: string;
  candidateAvatarUrl?: string | null;
  candidateHandle: string | null;
  targetRole: string | null;
  repoName: string | null;
  codeHealthScore: number | null;
  voiceDefenseScore: number | null;
  compositePercentile: number | null;
  rankTier: string | null;
  /** A review state such as "needs_human_review"; never a hiring recommendation. */
  statusTag: string;
  recordedAt: string;
}
