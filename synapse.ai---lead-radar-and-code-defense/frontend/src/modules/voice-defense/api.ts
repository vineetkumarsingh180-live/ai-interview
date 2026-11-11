// HTTP client for the Voice Defense module's endpoints (see the backend OpenAPI contract).
import { requestJson } from '@shared/api/client';
import type { VoiceCompleteResult, VoiceSessionInfo, VoiceTurnResult } from './types';

export function startVoiceSession(input: {
  repoId?: string;
  candidateName?: string;
  resumeText?: string;
  geminiApiKey1?: string;
}): Promise<VoiceSessionInfo> {
  return requestJson<VoiceSessionInfo>('/api/v1/assessment/voice/init', {
    method: 'POST',
    errorMessage: 'The interview session could not be started',
    body: {
      repoId: input.repoId,
      candidateName: input.candidateName,
      resumeText: input.resumeText?.trim() || undefined,
      geminiApiKey1: input.geminiApiKey1?.trim() || undefined,
    },
  });
}

export function submitVoiceTurn(input: { sessionId: string; speechText: string }): Promise<VoiceTurnResult> {
  return requestJson<VoiceTurnResult>('/api/v1/assessment/voice/turn', {
    method: 'POST',
    errorMessage: 'Your answer could not be saved',
    body: { sessionId: input.sessionId, candidateSpeechText: input.speechText },
  });
}

export function completeVoiceSession(sessionId: string): Promise<VoiceCompleteResult> {
  return requestJson<VoiceCompleteResult>(`/api/v1/assessment/voice/${sessionId}/complete`, {
    method: 'POST',
    errorMessage: 'Failed to complete and score the interview',
  });
}
