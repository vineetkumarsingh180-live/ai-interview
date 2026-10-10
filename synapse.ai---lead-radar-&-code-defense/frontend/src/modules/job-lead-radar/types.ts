// Types mirror the backend OpenAPI contract (camelCase). `null` always means "not stated/measured".

export interface RawPost {
  id: string;
  platform: 'twitter' | 'linkedin' | 'reddit' | 'telegram';
  externalId: string;
  authorHandle: string;
  authorName: string;
  authorAvatarUrl?: string | null;
  rawContent: string;
  sourceChannel: string;
  ingestedAt: string;
  isProcessed: boolean;
}

export interface JobLead {
  id: string;
  rawPostId: string;
  roleTitle: string;
  companyName: string;
  companyStage: string | null;
  compMin: number | null;
  compMax: number | null;
  compCurrency: string | null;
  equityNote: string | null;
  techStack: string[];
  locationMode: string | null;
  clearanceRequired: boolean | null;
  isHiring: boolean;
  /** Always null until a matching model exists. */
  matchScore: number | null;
  urgencyTier: string | null;
  contactAnchor: string | null;
  enrichmentMetadata: {
    summary?: string;
  };
  /** True for clearly labelled development fixtures. */
  isDemo: boolean;
  createdAt: string;
  rawPost?: RawPost | null;
}

export type IngestStatus = 'created' | 'discarded' | 'awaiting_analysis' | 'needs_review';

export interface IngestOutcome {
  status: IngestStatus;
  rawPostId: string;
  reason?: string | null;
  lead?: JobLead | null;
}

export interface IngestionTelemetry {
  totalScanned24h: number;
  qualifiedLeadsCount: number;
  seekingDiscardedCount: number;
  awaitingAnalysisCount: number;
  channelsMonitored: string[];
  /** Null: latency is not measured. */
  avgLatencyMs: number | null;
}

export type OutreachTone = 'Direct Technical' | 'Executive' | 'Casual Founder';

export interface OutreachDraft {
  id: string;
  leadId: string;
  tone: OutreachTone;
  pitchSubject: string;
  generatedPitch: string;
  candidateProfileContext?: string | null;
  status: string;
  modelVersion: string;
  promptTokens?: number | null;
  completionTokens?: number | null;
  createdAt: string;
}
