// Types mirror the backend OpenAPI contract (camelCase). `null` always means "not measured".

export interface BenchmarkSuite {
  id: string;
  repoId: string;
  testCoveragePct: number | null;
  cyclomaticComplexity: number | null;
  secVulnerabilitiesCount: number | null;
  executionTimeMs: number | null;
  suiteLogOutput: string | null;
  createdAt: string;
}

export interface CodeEvaluation {
  id: string;
  repoId: string;
  compositeHealthScore: number | null;
  architectureScore: number | null;
  concurrencySafetyScore: number | null;
  maintainabilityScore: number | null;
  summaryVerdict: string | null;
  rubricBreakdown: Record<string, unknown>;
  flaggedAnomalies: Array<Record<string, unknown>>;
  recommendedDefenseTopics: string[];
  evaluatedAt: string;
}

export interface GithubMetadata {
  full_name?: string;
  description?: string | null;
  topics?: string[];
  languages_bytes?: Record<string, number>;
  stars?: number;
  forks?: number;
  open_issues?: number;
  license?: string | null;
  visibility?: string | null;
  archived?: boolean;
  fork?: boolean;
  pushed_at?: string | null;
  created_at?: string | null;
}

export type RepoStatus = 'awaiting_analysis' | 'analyzing' | 'analyzed' | 'failed' | string;

export interface CandidateRepo {
  id: string;
  candidateName: string;
  candidateGithubHandle: string;
  candidateAvatarUrl?: string | null;
  repoUrl: string;
  repoName: string;
  targetRole: string | null;
  branch: string | null;
  commitSha: string | null;
  language: string | null;
  status: RepoStatus;
  /** True for clearly labelled development fixtures. */
  isDemo: boolean;
  submittedAt: string;
  /** api_manual | github_api | demo_fixture */
  sourceType: string;
  /** unverified | github_metadata (fetched from GitHub, not analysed) | demo_fixture */
  verificationStatus: string;
  /** Exactly what GitHub returned (null when nothing was fetched). */
  githubMetadata?: GithubMetadata | null;
  metadataFetchedAt?: string | null;
  benchmark?: BenchmarkSuite | null;
  evaluation?: CodeEvaluation | null;
}
