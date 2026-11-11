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

export interface RubricScores {
  vulgarity_score: number;
  vulgarity_verdict: string;
  vulgarity_detected: string[];
  bug_score: number;
  bug_verdict: string;
  detected_bugs: string[];
  advance_score: number;
  advance_verdict: string;
  advanced_features: string[];
}

export interface RepoAnalysisOutput {
  repo_url: string;
  owner: string;
  repo_name: string;
  primary_language: string;
  files_analyzed_count: number;
  overall_score: number;
  grade: string;
  summary_verdict: string;
  rubric: RubricScores;
  recommended_defense_topics: string[];
  suggested_improvements: string[];
}

export function analyzeRepoUrl(payload: { repo_url: string; candidate_name?: string }): Promise<RepoAnalysisOutput> {
  return requestJson<RepoAnalysisOutput>('/api/v1/assessment/repo/analyze-url', {
    method: 'POST',
    errorMessage: 'Failed to analyze GitHub repository with AI',
    body: {
      repo_url: payload.repo_url,
      candidate_name: payload.candidate_name || 'Candidate',
    },
  });
}

export interface DeleteRepoResponse {
  status: string;
  repo_id?: string;
  repoId?: string;
}

export function deleteRepo(repoId: string): Promise<DeleteRepoResponse> {
  return requestJson<DeleteRepoResponse>(`/api/v1/assessment/repo/${repoId}`, {
    method: 'DELETE',
    errorMessage: 'Failed to delete repository',
  });
}

export interface AnalyzeCodeSnippetInput {
  code: string;
  language?: string;
  context?: string;
}

export interface ScoreDimension {
  score: number;
  label: string;
  feedback: string;
}

export interface CodeAnalysisResult {
  overall_score: number;
  grade: string;
  summary: string;
  language_detected: string;
  dimensions: ScoreDimension[];
  issues: string[];
  suggestions: string[];
  interview_topics: string[];
}

export function analyzeCodeSnippet(payload: AnalyzeCodeSnippetInput): Promise<CodeAnalysisResult> {
  return requestJson<CodeAnalysisResult>('/api/v1/assessment/code/analyze', {
    method: 'POST',
    errorMessage: 'Failed to analyze code snippet with AI',
    body: payload,
  });
}
