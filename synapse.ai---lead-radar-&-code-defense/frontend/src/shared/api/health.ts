import { requestJson } from './client';

/** Backend status as reported by GET /api/health. */
export interface HealthStatus {
  status: 'ok' | 'degraded';
  service: string;
  version: string;
  database: 'connected' | 'unreachable';
  gemini: 'configured' | 'not_configured';
}

export function fetchHealth(): Promise<HealthStatus> {
  return requestJson<HealthStatus>('/api/health', { errorMessage: 'The backend did not answer' });
}
