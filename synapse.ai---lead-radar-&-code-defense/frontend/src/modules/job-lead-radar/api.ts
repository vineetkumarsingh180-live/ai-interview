// HTTP client for the Job Lead Radar module's endpoints (see the backend OpenAPI contract).
import { requestJson } from '@shared/api/client';
import type { IngestionTelemetry, IngestOutcome, JobLead, OutreachDraft } from './types';

export function fetchLeads(params: { platform?: string; minScore?: number }): Promise<JobLead[]> {
  const query = new URLSearchParams();
  if (params.platform && params.platform !== 'all') query.append('platform', params.platform);
  if (params.minScore && params.minScore > 0) query.append('min_score', params.minScore.toString());
  const qs = query.toString();
  return requestJson<JobLead[]>(`/api/v1/leads/ingest/recent${qs ? `?${qs}` : ''}`, {
    errorMessage: 'Failed to load leads',
  });
}

export function fetchTelemetry(): Promise<IngestionTelemetry> {
  return requestJson<IngestionTelemetry>('/api/v1/leads/ingest/telemetry', {
    errorMessage: 'Failed to load ingestion counts',
  });
}

export interface IngestPayload {
  platform: string;
  authorHandle: string;
  authorName: string;
  rawContent: string;
  sourceChannel: string;
}

export function ingestPost(payload: IngestPayload): Promise<IngestOutcome> {
  return requestJson<IngestOutcome>('/api/v1/leads/ingest/trigger', {
    method: 'POST',
    errorMessage: 'Failed to submit the post',
    body: {
      platform: payload.platform,
      externalId: `ext_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      authorHandle: payload.authorHandle || undefined,
      authorName: payload.authorName || undefined,
      rawContent: payload.rawContent,
      sourceChannel: payload.sourceChannel,
    },
  });
}

export function generateOutreachDraft(input: {
  leadId: string;
  tone: string;
  candidateProfile: string;
}): Promise<OutreachDraft> {
  return requestJson<OutreachDraft>('/api/v1/leads/outreach/generate', {
    method: 'POST',
    errorMessage: 'Failed to generate the draft',
    body: {
      leadId: input.leadId,
      tone: input.tone,
      candidateProfileContext: input.candidateProfile.trim() || undefined,
    },
  });
}
