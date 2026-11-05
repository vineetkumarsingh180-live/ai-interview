export interface TranscriptTurn {
  speaker: 'ai_interviewer' | 'candidate';
  text: string;
  timestamp: string;
  technicalAssessmentNote?: string | null;
}

/**
 * What this module needs to know about the candidate being interviewed. The host app builds it
 * from whatever source it has (for example a repository evaluation), keeping modules decoupled.
 */
export interface VoiceCandidate {
  id?: string;
  name: string;
  repoName?: string;
  targetRole?: string | null;
  commitSha?: string | null;
}

/** Response of POST /assessment/voice/init (subset the UI uses). */
export interface VoiceSessionInfo {
  id: string;
  repoId: string | null;
  candidateName: string;
  sessionStatus: string;
  defenseVerdict: string;
  transcriptTurns: TranscriptTurn[];
}

/** Response of POST /assessment/voice/turn. */
export interface VoiceTurnResult {
  sessionId: string;
  turnNumber: number;
  aiStatus: 'generated' | 'unavailable';
  interviewerReplyText: string | null;
  defenseScoreDelta: number | null;
  currentCompositeScore: number | null;
  currentVerdict: string;
  interviewStage?: string | null;
  isCompleted?: boolean;
  evaluationScore?: number | null;
  evaluationFeedback?: string | null;
}

export interface VoiceCompleteResult {
  sessionId: string;
  overallScore: number; // Scale: 1.0 to 10.0
  technicalDepthScore: number;
  clarityArticulationScore: number;
  projectDefenseScore: number;
  summary: string;
  keyStrengths: string[];
  areasForImprovement: string[];
  defenseVerdict: string;
}
