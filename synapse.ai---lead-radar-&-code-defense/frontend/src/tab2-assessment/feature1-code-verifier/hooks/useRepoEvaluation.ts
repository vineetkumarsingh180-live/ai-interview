import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export interface BenchmarkSuite {
  id: string;
  repoId: string;
  testCoveragePct: number;
  cyclomaticComplexity: number;
  secVulnerabilitiesCount: number;
  aiGeneratedProbability: number;
  executionTimeMs: number;
  suiteLogOutput: string;
  createdAt: string;
}

export interface CodeEvaluation {
  id: string;
  repoId: string;
  compositeHealthScore: number;
  architectureScore: number;
  concurrencySafetyScore: number;
  maintainabilityScore: number;
  antiCheatConfidence: number;
  summaryVerdict: string;
  rubricBreakdown: Record<string, number>;
  flaggedAnomalies: Array<{ type: string; severity: string; description: string }>;
  recommendedDefenseTopics: string[];
  evaluatedAt: string;
}

export interface CandidateRepo {
  id: string;
  candidateName: string;
  candidateGithubHandle: string;
  candidateAvatarUrl?: string;
  repoUrl: string;
  repoName: string;
  targetRole: string;
  branch: string;
  commitSha: string;
  language: string;
  status: string;
  submittedAt: string;
  benchmark?: BenchmarkSuite;
  evaluation?: CodeEvaluation;
}

export function useRepoEvaluation() {
  const queryClient = useQueryClient();
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);

  const { data: repos = [], isLoading: isLoadingRepos, refetch: refetchRepos } = useQuery<CandidateRepo[]>({
    queryKey: ['candidate-repos'],
    queryFn: async () => {
      const res = await fetch('/api/v1/assessment/repo/recent');
      if (!res.ok) throw new Error('Failed to load candidate repositories');
      return res.json();
    },
    refetchInterval: 15000,
  });

  const submitRepoMutation = useMutation<CandidateRepo, Error, {
    candidateName: string;
    candidateGithubHandle: string;
    repoUrl: string;
    targetRole?: string;
    branch?: string;
  }>({
    mutationFn: async (payload) => {
      const res = await fetch('/api/v1/assessment/repo/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_name: payload.candidateName,
          candidate_github_handle: payload.candidateGithubHandle,
          repo_url: payload.repoUrl,
          target_role: payload.targetRole || 'Staff Distributed Systems Engineer',
          branch: payload.branch || 'main',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Submission failed' }));
        throw new Error(err.detail || 'Failed to submit repository');
      }
      return res.json();
    },
    onSuccess: (newRepo) => {
      queryClient.invalidateQueries({ queryKey: ['candidate-repos'] });
      setSelectedRepoId(newRepo.id);
    },
  });

  // Currently selected or default active repo
  const activeRepo = repos.find((r) => r.id === selectedRepoId) || repos[0] || null;

  return {
    repos,
    isLoadingRepos,
    activeRepo,
    selectedRepoId,
    setSelectedRepoId,
    submitRepo: submitRepoMutation.mutateAsync,
    isSubmitting: submitRepoMutation.isPending,
    submissionError: submitRepoMutation.error,
    refetchRepos,
  };
}
