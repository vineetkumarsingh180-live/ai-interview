// HTTP client for the Voice Defense module's endpoints (see the backend OpenAPI contract).
import { requestJson } from '@shared/api/client';
import type { VoiceSessionInfo, VoiceTurnResult } from './types';

export function startVoiceSession(input: { repoId?: string; candidateName?: string }): Promise<VoiceSessionInfo> {
  return requestJson<VoiceSessionInfo>('/api/v1/assessment/voice/init', {
    method: 'POST',
    errorMessage: 'The interview session could not be started',
    body: { repoId: input.repoId, candidateName: input.candidateName },
  });
}

export function submitVoiceTurn(input: { sessionId: string; speechText: string }): Promise<VoiceTurnResult> {
  return requestJson<VoiceTurnResult>('/api/v1/assessment/voice/turn', {
    method: 'POST',
    errorMessage: 'Your answer could not be saved',
    body: { sessionId: input.sessionId, candidateSpeechText: input.speechText },
  });
}
