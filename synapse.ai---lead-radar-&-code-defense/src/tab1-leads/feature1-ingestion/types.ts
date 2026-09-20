export interface RawPost {
  id: string;
  platform: 'twitter' | 'linkedin' | 'reddit' | 'telegram';
  externalId: string;
  authorHandle: string;
  authorName: string;
  authorAvatarUrl?: string;
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
  companyStage?: string;
  compMin?: number;
  compMax?: number;
  compCurrency: string;
  equityNote?: string;
  techStack: string[];
  locationMode: 'Remote' | 'Hybrid' | 'Onsite';
  clearanceRequired: boolean;
  isHiring: boolean;
  matchScore: number;
  urgencyTier: 'Immediate' | 'High' | 'Normal';
  contactAnchor?: string;
  enrichmentMetadata?: {
    summary?: string;
    verifiedPost?: boolean;
    channelSource?: string;
    sentiment?: string;
  };
  createdAt: string;
  rawPost?: RawPost;
}

export interface IngestionTelemetry {
  totalScanned24h: number;
  qualifiedLeadsCount: number;
  seekingDiscardedCount: number;
  channelsMonitored: string[];
  avgLatencyMs: number;
}
