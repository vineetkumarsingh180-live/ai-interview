import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRepos, submitRepo, SubmitRepoInput } from '../api';
import type { CandidateRepo } from '../types';

export function useRepoEvaluation() {
  const queryClient = useQueryClient();
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);

  const {
    data: repos = [],
    isLoading: isLoadingRepos,
    isError: isReposError,
    error: reposError,
    refetch: refetchRepos,
  } = useQuery<CandidateRepo[]>({
    queryKey: ['candidate-repos'],
    queryFn: fetchRepos,
    refetchInterval: 15000,
  });

  const submitRepoMutation = useMutation<CandidateRepo, Error, SubmitRepoInput>({
    mutationFn: submitRepo,
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
    reposError: isReposError ? (reposError as Error) : null,
    activeRepo,
    selectedRepoId,
    setSelectedRepoId,
    submitRepo: submitRepoMutation.mutateAsync,
    isSubmitting: submitRepoMutation.isPending,
    submissionError: submitRepoMutation.error,
    refetchRepos,
  };
}

/** The hook's result. The host keeps it alive across tab switches and passes it to the view. */
export type RepoEvaluationState = ReturnType<typeof useRepoEvaluation>;
