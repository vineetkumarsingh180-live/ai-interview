// HTTP client for the Code Verifier module's endpoints (see the backend OpenAPI contract).
import { requestJson } from '@shared/api/client';
import type { CandidateRepo } from './types';

export function fetchRepos(): Promise<CandidateRepo[]> {
  return requestJson<CandidateRepo[]>('/api/v1/assessment/repo/recent', {
    errorMessage: 'Failed to load submitted repositories',
  });
}

export interface SubmitRepoInput {
  candidateName: string;
  candidateGithubHandle: string;
  repoUrl: string;
  targetRole?: string;
  branch?: string;
}

export function submitRepo(payload: SubmitRepoInput): Promise<CandidateRepo> {
  return requestJson<CandidateRepo>('/api/v1/assessment/repo/submit', {
    method: 'POST',
    errorMessage: 'Failed to submit the repository',
    body: {
      candidateName: payload.candidateName,
      candidateGithubHandle: payload.candidateGithubHandle,
      repoUrl: payload.repoUrl,
      targetRole: payload.targetRole?.trim() || undefined,
      branch: payload.branch?.trim() || undefined,
    },
  });
}
