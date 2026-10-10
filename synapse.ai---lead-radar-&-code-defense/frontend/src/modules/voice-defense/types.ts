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

/** Response of POST /assessment/voice/turn. Scores are always null: answers are not auto-scored. */
export interface VoiceTurnResult {
  sessionId: string;
  turnNumber: number;
  aiStatus: 'generated' | 'unavailable';
  interviewerReplyText: string | null;
  defenseScoreDelta: number | null;
  currentCompositeScore: number | null;
  currentVerdict: string;
}
