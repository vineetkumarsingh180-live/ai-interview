// API types for the AI code paste analyzer endpoint
export interface CodeAnalysisRequest {
  code: string;
  language?: string;
  context?: string;
}

export interface ScoreDimension {
  score: number;    // 0-100
  label: string;
  feedback: string;
}

export interface CodeAnalysisResult {
  overall_score: number;   // 0-100
  grade: string;           // A+, A, B+, B, C+, C, D, F
  summary: string;
  language_detected: string;
  dimensions: ScoreDimension[];
  issues: string[];
  suggestions: string[];
  interview_topics: string[];
}
