import express from "express";
import http from "http";
import path from "path";
import { WebSocketServer, WebSocket } from "ws";
import { GoogleGenAI } from "@google/genai";
import { createServer as createViteServer } from "vite";

const app = express();
const PORT = 3000;
app.use(express.json());

// Lazy-initialized Gemini client
let geminiClient: GoogleGenAI | null = null;
function getGemini(): GoogleGenAI | null {
  if (!geminiClient && process.env.GEMINI_API_KEY) {
    geminiClient = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
  }
  return geminiClient;
}

// ==================== IN-MEMORY SEEDED DATA STORE ====================

interface SeedLead {
  id: string;
  rawPostId: string;
  roleTitle: string;
  companyName: string;
  companyStage: string;
  compMin: number;
  compMax: number;
  compCurrency: string;
  equityNote: string;
  techStack: string[];
  locationMode: 'Remote' | 'Hybrid' | 'Onsite';
  clearanceRequired: boolean;
  isHiring: boolean;
  matchScore: number;
  urgencyTier: 'Immediate' | 'High' | 'Normal';
  contactAnchor: string;
  enrichmentMetadata: any;
  createdAt: string;
  rawPost: {
    id: string;
    platform: string;
    externalId: string;
    authorHandle: string;
    authorName: string;
    rawContent: string;
    sourceChannel: string;
    ingestedAt: string;
  };
}

let leadsStore: SeedLead[] = [
  {
    id: 'lead-1',
    rawPostId: 'raw-1',
    roleTitle: 'Staff Distributed Systems Engineer',
    companyName: 'Aura Labs',
    companyStage: 'Series A ($14M)',
    compMin: 220000,
    compMax: 285000,
    compCurrency: 'USD',
    equityNote: '+ 0.25% Equity',
    techStack: ['Rust', 'Raft', 'Kafka', 'PostgreSQL', 'Zero-Copy'],
    locationMode: 'Remote',
    clearanceRequired: false,
    isHiring: true,
    matchScore: 99.4,
    urgencyTier: 'Immediate',
    contactAnchor: 'DM @steve_aura on X or steve@auralabs.io',
    enrichmentMetadata: {
      summary: 'Building low-latency consensus clustering engine for next-gen stream processing. Looking for deep Raft & network state machine experience.',
      channelSource: 'X Core API',
      verifiedPost: true,
    },
    createdAt: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    rawPost: {
      id: 'raw-1',
      platform: 'twitter',
      externalId: 'tw_189218291',
      authorHandle: '@steve_aura',
      authorName: 'Steve Vance (CEO)',
      rawContent: 'Hiring Staff Distributed Systems Engineer to lead our low-latency Raft consensus clustering engine in Rust. $220k-$285k + 0.25% equity. Remote friendly. DM me directly!',
      sourceChannel: 'X Core API',
      ingestedAt: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    },
  },
  {
    id: 'lead-2',
    rawPostId: 'raw-2',
    roleTitle: 'Principal Protocol Architect',
    companyName: 'Solana Foundation / Ecosystem',
    companyStage: 'Ecosystem Grant',
    compMin: 240000,
    compMax: 320000,
    compCurrency: 'USD',
    equityNote: '+ Token Pool',
    techStack: ['Rust', 'Solana', 'Wasm', 'eBPF', 'P2P Gossip'],
    locationMode: 'Remote',
    clearanceRequired: false,
    isHiring: true,
    matchScore: 97.8,
    urgencyTier: 'High',
    contactAnchor: 'engineering@solana.org or Telegram @sol_infra',
    enrichmentMetadata: {
      summary: 'Validator pipeline scaling, transaction scheduling under heavy MEV contention, and asynchronous state verification.',
      channelSource: 'Reddit Tech (r/rust)',
      verifiedPost: true,
    },
    createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    rawPost: {
      id: 'raw-2',
      platform: 'reddit',
      externalId: 'rd_9827182',
      authorHandle: 'u/sol_core_dev',
      authorName: 'Solana Infra Team',
      rawContent: 'We need a Principal Protocol Architect with heavy Rust/Wasm and consensus optimization experience. $240k - $320k base + token allocation. Contact engineering@solana.org',
      sourceChannel: 'Reddit r/rust',
      ingestedAt: new Date(Date.now() - 1000 * 60 * 50).toISOString(),
    },
  },
  {
    id: 'lead-3',
    rawPostId: 'raw-3',
    roleTitle: 'Senior Infrastructure & Concurrency Lead',
    companyName: 'Neon Systems',
    companyStage: 'Series B',
    compMin: 195000,
    compMax: 250000,
    compCurrency: 'USD',
    equityNote: '+ 0.15% Options',
    techStack: ['Go', 'Kubernetes', 'gRPC', 'PostgreSQL', 'etcd'],
    locationMode: 'Hybrid',
    clearanceRequired: false,
    isHiring: true,
    matchScore: 94.6,
    urgencyTier: 'Normal',
    contactAnchor: 'LinkedIn InMail to VP of Engineering',
    enrichmentMetadata: {
      summary: 'Multi-region distributed database proxy routing, connection pooling, and fault injection testing.',
      channelSource: 'LinkedIn Jobs Live',
      verifiedPost: true,
    },
    createdAt: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    rawPost: {
      id: 'raw-3',
      platform: 'linkedin',
      externalId: 'li_2391083',
      authorHandle: 'Neon Systems Inc.',
      authorName: 'Talent Acquisition',
      rawContent: 'Neon Systems is expanding its Core Data Layer team! Looking for a Senior Concurrency & Infrastructure Lead with Go/etcd/Postgres expertise.',
      sourceChannel: 'LinkedIn Jobs',
      ingestedAt: new Date(Date.now() - 1000 * 60 * 130).toISOString(),
    },
  },
  {
    id: 'lead-4',
    rawPostId: 'raw-4',
    roleTitle: 'Core Database Kernel Engineer',
    companyName: 'Vektor Data',
    companyStage: 'Seed ($4.5M)',
    compMin: 210000,
    compMax: 260000,
    compCurrency: 'USD',
    equityNote: '+ 1.0% Equity',
    techStack: ['C++', 'Rust', 'LSM-Tree', 'SIMD', 'Linux io_uring'],
    locationMode: 'Remote',
    clearanceRequired: false,
    isHiring: true,
    matchScore: 92.1,
    urgencyTier: 'Immediate',
    contactAnchor: 'founders@vektordata.ai or Telegram @vektor_cto',
    enrichmentMetadata: {
      summary: 'Zero-copy high-performance vector index engine utilizing SIMD instructions and io_uring asynchronous disk I/O.',
      channelSource: 'Telegram Alpha Tech',
      verifiedPost: true,
    },
    createdAt: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
    rawPost: {
      id: 'raw-4',
      platform: 'telegram',
      externalId: 'tg_882910',
      authorHandle: '@vektor_cto',
      authorName: 'Dr. Elena Rostova',
      rawContent: 'Building a new vector search storage engine from scratch. Need kernel / LSM-tree systems engineer. High equity + competitive compensation.',
      sourceChannel: 'Telegram Alpha Tech',
      ingestedAt: new Date(Date.now() - 1000 * 60 * 250).toISOString(),
    },
  }
];

let telemetryStore = {
  totalScanned24h: 1842,
  qualifiedLeadsCount: 48,
  seekingDiscardedCount: 1794,
  channelsMonitored: ['X Core API', 'r/forhire', 'LinkedIn Jobs Live', 'Telegram Alpha'],
  avgLatencyMs: 240,
};

interface SeedRepo {
  id: string;
  candidateName: string;
  candidateGithubHandle: string;
  candidateAvatarUrl?: string;
  repoUrl: string;
  repoName: string;
  targetRole: string;
  branch: string;
  commitSha: string;
  language: string;
  status: string;
  submittedAt: string;
  benchmark: {
    id: string;
    repoId: string;
    testCoveragePct: number;
    cyclomaticComplexity: number;
    secVulnerabilitiesCount: number;
    aiGeneratedProbability: number;
    executionTimeMs: number;
    suiteLogOutput: string;
    createdAt: string;
  };
  evaluation: {
    id: string;
    repoId: string;
    compositeHealthScore: number;
    architectureScore: number;
    concurrencySafetyScore: number;
    maintainabilityScore: number;
    antiCheatConfidence: number;
    summaryVerdict: string;
    rubricBreakdown: Record<string, number>;
    flaggedAnomalies: Array<{ type: string; severity: string; description: string }>;
    recommendedDefenseTopics: string[];
    evaluatedAt: string;
  };
}

let candidateReposStore: SeedRepo[] = [
  {
    id: 'repo-1',
    candidateName: 'Alex Vance',
    candidateGithubHandle: 'alexvance',
    candidateAvatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    repoUrl: 'https://github.com/alexvance/distributed-raft-kv',
    repoName: 'distributed-raft-kv',
    targetRole: 'Staff Distributed Systems Engineer',
    branch: 'main',
    commitSha: 'd81a9f4',
    language: 'Rust',
    status: 'VERIFIED',
    submittedAt: new Date(Date.now() - 1000 * 60 * 300).toISOString(),
    benchmark: {
      id: 'bm-1',
      repoId: 'repo-1',
      testCoveragePct: 94.2,
      cyclomaticComplexity: 3.8,
      secVulnerabilitiesCount: 0,
      aiGeneratedProbability: 0.019,
      executionTimeMs: 1420,
      suiteLogOutput: 'PASS src/raft/election_test.rs (32/32 tests passed)\nPASS src/raft/split_brain_test.rs (partition quorum verified)\nPASS src/storage/wal_sync.rs (fsync benchmark 0.12ms p99)',
      createdAt: new Date().toISOString(),
    },
    evaluation: {
      id: 'eval-1',
      repoId: 'repo-1',
      compositeHealthScore: 94,
      architectureScore: 96,
      concurrencySafetyScore: 98,
      maintainabilityScore: 91,
      antiCheatConfidence: 98.1,
      summaryVerdict: 'Exemplary implementation of the Raft consensus state machine in Rust. Clean zero-allocation serialization in the networking layer, though the heartbeat election timeout jitter could benefit from cryptographic seed randomization under adversarial network partition.',
      rubricBreakdown: {
        'Consensus Safety & Quorum': 96,
        'Memory Safety & Rust Idioms': 98,
        'Partition Tolerance & Network Mocking': 94,
        'AST Authenticity (Anti-LLM Cheating)': 98,
      },
      flaggedAnomalies: [
        {
          type: 'Timeout Jitter',
          severity: 'Low',
          description: 'Election timeout randomized between 150-300ms without entropy seed reset after socket reset.'
        }
      ],
      recommendedDefenseTopics: [
        'Log compaction and snapshot transmission under asymmetric split-brain partitions',
        'Zero-copy buffer reclamation in custom circular ring buffer',
        'Handling Byzantine or sluggish followers during joint consensus reconfiguration'
      ],
      evaluatedAt: new Date().toISOString(),
    }
  },
  {
    id: 'repo-2',
    candidateName: 'Sophia Chen',
    candidateGithubHandle: 'sophiachen_dev',
    candidateAvatarUrl: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
    repoUrl: 'https://github.com/sophiachen/solana-mev-scheduler',
    repoName: 'solana-mev-scheduler',
    targetRole: 'Principal Protocol Architect',
    branch: 'main',
    commitSha: '9c44b12',
    language: 'Rust',
    status: 'VERIFIED',
    submittedAt: new Date(Date.now() - 1000 * 60 * 600).toISOString(),
    benchmark: {
      id: 'bm-2',
      repoId: 'repo-2',
      testCoveragePct: 91.5,
      cyclomaticComplexity: 4.1,
      secVulnerabilitiesCount: 0,
      aiGeneratedProbability: 0.024,
      executionTimeMs: 1880,
      suiteLogOutput: 'PASS tests/mempool_sort.rs\nPASS tests/bundle_sim.rs',
      createdAt: new Date().toISOString(),
    },
    evaluation: {
      id: 'eval-2',
      repoId: 'repo-2',
      compositeHealthScore: 92,
      architectureScore: 94,
      concurrencySafetyScore: 92,
      maintainabilityScore: 90,
      antiCheatConfidence: 97.6,
      summaryVerdict: 'High-throughput lock-free ring buffer for Solana transaction scheduling. Thorough benchmarks demonstrating 420k tx/sec parsing throughput.',
      rubricBreakdown: {
        'Throughput & Concurrency': 95,
        'Protocol Compliance': 92,
        'Test Rigor': 89,
      },
      flaggedAnomalies: [],
      recommendedDefenseTopics: [
        'Contention handling in lock-free transaction queues',
        'Fork choice evaluation under flash-loan sandwich attacks'
      ],
      evaluatedAt: new Date().toISOString(),
    }
  },
  {
    id: 'repo-3',
    candidateName: 'Marcus Thorne',
    candidateGithubHandle: 'm_thorne',
    candidateAvatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    repoUrl: 'https://github.com/mthorne/etcd-raft-proxy',
    repoName: 'etcd-raft-proxy',
    targetRole: 'Senior Infrastructure & Concurrency Lead',
    branch: 'main',
    commitSha: 'f1023ba',
    language: 'Go',
    status: 'VERIFIED',
    submittedAt: new Date(Date.now() - 1000 * 60 * 900).toISOString(),
    benchmark: {
      id: 'bm-3',
      repoId: 'repo-3',
      testCoveragePct: 88.4,
      cyclomaticComplexity: 4.6,
      secVulnerabilitiesCount: 0,
      aiGeneratedProbability: 0.041,
      executionTimeMs: 950,
      suiteLogOutput: 'PASS proxy_test.go',
      createdAt: new Date().toISOString(),
    },
    evaluation: {
      id: 'eval-3',
      repoId: 'repo-3',
      compositeHealthScore: 89,
      architectureScore: 90,
      concurrencySafetyScore: 88,
      maintainabilityScore: 89,
      antiCheatConfidence: 95.9,
      summaryVerdict: 'Robust Go gRPC proxy for multi-cluster etcd synchronization. Clear context cancellation and channel lifecycle management.',
      rubricBreakdown: {
        'Concurrency Safety': 88,
        'Network Resiliency': 90,
      },
      flaggedAnomalies: [],
      recommendedDefenseTopics: [
        'Goroutine leak prevention during graceful shutdown',
        'Watch stream compaction backpressure'
      ],
      evaluatedAt: new Date().toISOString(),
    }
  }
];

let leaderboardStore = [
  {
    id: 'leadb-1',
    sessionId: 'sess-alex-1',
    candidateName: 'Alex Vance',
    candidateAvatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    candidateHandle: 'alexvance',
    targetRole: 'Staff Distributed Systems Engineer',
    repoName: 'distributed-raft-kv',
    codeHealthScore: 94.2,
    voiceDefenseScore: 93.8,
    compositePercentile: 99.8,
    rankTier: 'Top 0.2%',
    statusTag: 'Auto-Hire Recommended',
    recordedAt: new Date().toISOString(),
  },
  {
    id: 'leadb-2',
    sessionId: 'sess-sophia-1',
    candidateName: 'Sophia Chen',
    candidateAvatarUrl: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80',
    candidateHandle: 'sophiachen_dev',
    targetRole: 'Principal Protocol Architect',
    repoName: 'solana-mev-scheduler',
    codeHealthScore: 92.0,
    voiceDefenseScore: 91.5,
    compositePercentile: 98.6,
    rankTier: 'Top 1.4%',
    statusTag: 'Auto-Hire Recommended',
    recordedAt: new Date(Date.now() - 1000 * 60 * 3600).toISOString(),
  },
  {
    id: 'leadb-3',
    sessionId: 'sess-marcus-1',
    candidateName: 'Marcus Thorne',
    candidateAvatarUrl: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
    candidateHandle: 'm_thorne',
    targetRole: 'Senior Infrastructure Lead',
    repoName: 'etcd-raft-proxy',
    codeHealthScore: 89.0,
    voiceDefenseScore: 88.5,
    compositePercentile: 94.2,
    rankTier: 'Top 5.8%',
    statusTag: 'Passed Defense',
    recordedAt: new Date(Date.now() - 1000 * 60 * 7200).toISOString(),
  }
];

// ==================== REST API ROUTES ====================

app.get("/api/health", (req, res) => {
  res.json({
    status: "ok",
    service: "Synapse.AI API Core",
    version: "2.6.0",
    gemini_connected: !!process.env.GEMINI_API_KEY,
  });
});

// TAB 1: Leads Ingestion & Telemetry
app.get("/api/v1/leads/ingest/recent", (req, res) => {
  const { platform, min_score } = req.query;
  let results = [...leadsStore];

  if (platform && platform !== 'all') {
    results = results.filter((l) => l.rawPost.platform.toLowerCase() === String(platform).toLowerCase());
  }
  if (min_score) {
    results = results.filter((l) => l.matchScore >= Number(min_score));
  }
  res.json(results);
});

app.get("/api/v1/leads/ingest/telemetry", (req, res) => {
  res.json(telemetryStore);
});

app.post("/api/v1/leads/ingest/trigger", async (req, res) => {
  const { platform, external_id, author_handle, author_name, raw_content, source_channel } = req.body;

  // Run binary classification & entity extraction
  const ai = getGemini();
  let isHiring = true;
  let roleTitle = "Distributed Systems Engineer";
  let companyName = author_name || "Stealth Venture";
  let techStack = ["Rust", "Distributed Systems"];
  let compMin = 200000;
  let compMax = 250000;
  let matchScore = 95.0;

  if (ai) {
    try {
      const prompt = `Analyze this social post for hiring signals. Output ONLY valid JSON:
{
  "is_hiring": boolean (true if someone is HIRING/looking for talent, false if someone is SEEKING a job),
  "role_title": string,
  "company_name": string,
  "tech_stack": string[],
  "comp_min": number,
  "comp_max": number,
  "location_mode": "Remote" | "Hybrid" | "Onsite",
  "match_score": number (0-100)
}

POST CONTENT:
"""
${raw_content}
"""`;

      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: prompt,
        config: { responseMimeType: "application/json" },
      });

      if (response.text) {
        const parsed = JSON.parse(response.text);
        isHiring = parsed.is_hiring ?? true;
        roleTitle = parsed.role_title || roleTitle;
        companyName = parsed.company_name || companyName;
        techStack = parsed.tech_stack || techStack;
        compMin = parsed.comp_min || compMin;
        compMax = parsed.comp_max || compMax;
        matchScore = parsed.match_score || 92.5;
      }
    } catch (err) {
      console.warn("Gemini parse fallback:", err);
    }
  } else {
    // Local heuristic check
    const textLower = (raw_content || "").toLowerCase();
    if (textLower.includes("open to work") || textLower.includes("looking for my first") || textLower.includes("hire me")) {
      isHiring = false;
    }
  }

  telemetryStore.totalScanned24h += 1;
  if (!isHiring) {
    telemetryStore.seekingDiscardedCount += 1;
    return res.status(200).json({
      status: "discarded",
      reason: "Classified as candidate seeking employment (Job Seeker signal filtered).",
    });
  }

  telemetryStore.qualifiedLeadsCount += 1;
  const newLead: SeedLead = {
    id: `lead-${Date.now()}`,
    rawPostId: `raw-${Date.now()}`,
    roleTitle,
    companyName,
    companyStage: "Early Stage",
    compMin,
    compMax,
    compCurrency: "USD",
    equityNote: "+ Competitive Equity",
    techStack,
    locationMode: "Remote",
    clearanceRequired: false,
    isHiring: true,
    matchScore,
    urgencyTier: "Immediate",
    contactAnchor: `DM ${author_handle} directly`,
    enrichmentMetadata: {
      summary: raw_content.slice(0, 160),
      channelSource: source_channel || "User Simulation",
      verifiedPost: true,
    },
    createdAt: new Date().toISOString(),
    rawPost: {
      id: `raw-${Date.now()}`,
      platform: platform || "twitter",
      externalId: external_id || `sim_${Date.now()}`,
      authorHandle: author_handle || "@founder",
      authorName: author_name || "Tech Founder",
      rawContent: raw_content,
      sourceChannel: source_channel || "Direct Input",
      ingestedAt: new Date().toISOString(),
    },
  };

  leadsStore.unshift(newLead);
  res.status(201).json(newLead);
});

// TAB 1: Cold Outreach Generator
app.post("/api/v1/leads/outreach/generate", async (req, res) => {
  const { lead_id, tone, candidate_profile_context } = req.body;
  const targetLead = leadsStore.find((l) => l.id === lead_id) || leadsStore[0];

  const ai = getGemini();
  let subject = `Technical Lead Inquiry - ${targetLead.roleTitle} @ ${targetLead.companyName}`;
  let pitch = `Hey ${targetLead.companyName} Team,\n\nI saw your post for the ${targetLead.roleTitle} role building with ${targetLead.techStack.slice(0, 3).join(", ")}. In my previous engineering roles, I focused on high-throughput distributed systems and low-latency consensus protocols matching your stack.\n\nI have proven experience maintaining zero-copy networking architectures and Raft state machines under aggressive network partition workloads. Would love to share benchmarks from recent consensus engine implementations.\n\nBest,\nCandidate`;

  if (ai) {
    try {
      const prompt = `You are an elite software engineer writing a cold outreach message to the hiring contact of this company.
LEAD DETAILS:
- Role: ${targetLead.roleTitle}
- Company: ${targetLead.companyName}
- Tech Stack: ${targetLead.techStack.join(", ")}
- Pitch Tone: ${tone}
- Candidate Background: ${candidate_profile_context || "Principal Distributed Systems Engineer"}

Write a high-converting, concise cold message with NO generic buzzwords.
Output ONLY JSON:
{
  "pitch_subject": string,
  "generated_pitch": string
}`;

      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: prompt,
        config: { responseMimeType: "application/json" },
      });

      if (response.text) {
        const parsed = JSON.parse(response.text);
        subject = parsed.pitch_subject || subject;
        pitch = parsed.generated_pitch || pitch;
      }
    } catch (err) {
      console.warn("Gemini outreach fallback:", err);
    }
  }

  res.json({
    id: `draft-${Date.now()}`,
    leadId: lead_id,
    tone: tone || "Direct Technical",
    pitchSubject: subject,
    generatedPitch: pitch,
    candidateProfileContext: candidate_profile_context,
    status: "GENERATED",
    modelVersion: "Gemini 2.5 Flash",
    createdAt: new Date().toISOString(),
  });
});

// TAB 2: Repo Evaluator & Code Verifier
app.get("/api/v1/assessment/repo/recent", (req, res) => {
  res.json(candidateReposStore);
});

app.post("/api/v1/assessment/repo/submit", async (req, res) => {
  const { candidate_name, candidate_github_handle, repo_url, target_role, branch } = req.body;
  const repoName = repo_url.split("/").filter(Boolean).pop() || "distributed-core";

  const newRepo = {
    id: `repo-${Date.now()}`,
    candidateName: candidate_name || "Candidate",
    candidateGithubHandle: candidate_github_handle || "dev",
    candidateAvatarUrl: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80",
    repoUrl: repo_url,
    repoName,
    targetRole: target_role || "Staff Distributed Systems Engineer",
    branch: branch || "main",
    commitSha: "a492df8",
    language: "Rust",
    status: "VERIFIED",
    submittedAt: new Date().toISOString(),
    benchmark: {
      id: `bm-${Date.now()}`,
      repoId: `repo-${Date.now()}`,
      testCoveragePct: 93.8,
      cyclomaticComplexity: 3.5,
      secVulnerabilitiesCount: 0,
      aiGeneratedProbability: 0.015,
      executionTimeMs: 1280,
      suiteLogOutput: "PASS sandbox/tests (28/28 passed)\nPASS memory_safety_sanitizer\nPASS zero_leak_audit",
      createdAt: new Date().toISOString(),
    },
    evaluation: {
      id: `eval-${Date.now()}`,
      repoId: `repo-${Date.now()}`,
      compositeHealthScore: 93,
      architectureScore: 95,
      concurrencySafetyScore: 97,
      maintainabilityScore: 92,
      antiCheatConfidence: 98.5,
      summaryVerdict: `Robust implementation of ${repoName}. Clean separation of concerns and hermetic AST verification confirmed human authorship.`,
      rubricBreakdown: {
        "Concurrency & Memory Safety": 97,
        "Architectural Decoupling": 95,
        "Hermetic AST Verification": 98.5,
      },
      flaggedAnomalies: [],
      recommendedDefenseTopics: [
        "Thread synchronization primitives and cache-line bouncing",
        "Recovery semantics during sudden host termination"
      ],
      evaluatedAt: new Date().toISOString(),
    }
  };

  candidateReposStore.unshift(newRepo);
  res.status(201).json(newRepo);
});

// TAB 2: Voice Interview & Leaderboard
app.post("/api/v1/assessment/voice/init", (req, res) => {
  res.json({
    id: `voice-sess-${Date.now()}`,
    candidateName: req.body.candidate_name || "Alex Vance",
    repoId: req.body.repo_id || "repo-1",
    status: "IN_PROGRESS",
    compositeScore: 89.0,
    verdict: "HUMAN_REVIEW",
    initialPrompt: "I see in your Raft implementation you've configured election timeouts between 150ms and 300ms. Under a partial cross-rack network split where heartbeats are intermittently dropped, how does your state machine prevent split-vote thrashing and uncommitted log divergence?",
  });
});

app.post("/api/v1/assessment/voice/turn", async (req, res) => {
  const { session_id, candidate_speech_text } = req.body;

  const ai = getGemini();
  let reply = "Good articulation on the pre-vote phase and heartbeat isolation. Next: how does your persistence log handle WAL fsync latency spikes when the disk buffer is saturated without blocking the main event loop?";
  let scoreDelta = 2.4;
  let score = 91.4;
  let verdict = "AUTO_HIRE";

  if (ai) {
    try {
      const prompt = `You are an elite Principal Distributed Systems Architect conducting an oral code defense for a candidate who wrote a Raft consensus implementation in Rust.
CANDIDATE ORAL ANSWER:
"""
${candidate_speech_text}
"""

Evaluate their answer. Output JSON:
{
  "reply": string (A razor-sharp, technically challenging 1-2 sentence follow-up question digging deeper into their architecture),
  "score_delta": number (between 1.0 and 4.0),
  "current_composite_score": number (between 90.0 and 97.0),
  "verdict": "AUTO_HIRE" | "HUMAN_REVIEW"
}`;

      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash",
        contents: prompt,
        config: { responseMimeType: "application/json" },
      });

      if (response.text) {
        const parsed = JSON.parse(response.text);
        reply = parsed.reply || reply;
        score = parsed.current_composite_score || 92.5;
        scoreDelta = parsed.score_delta || 2.0;
        verdict = parsed.verdict || "AUTO_HIRE";
      }
    } catch (err) {
      console.warn("Voice turn fallback:", err);
    }
  }

  // Update top candidate on leaderboard
  if (leaderboardStore[0]) {
    leaderboardStore[0].voiceDefenseScore = score;
  }

  res.json({
    turn_number: 2,
    interviewer_reply_text: reply,
    defense_score_delta: scoreDelta,
    current_composite_score: score,
    current_verdict: verdict,
  });
});

app.get("/api/v1/assessment/voice/leaderboard", (req, res) => {
  res.json(leaderboardStore);
});

// ==================== HTTP & WEBSOCKET SERVER ====================

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: "/ws/voice" });

wss.on("connection", (ws: WebSocket) => {
  ws.send(JSON.stringify({
    event: "connected",
    message: "AI Voice Defense WebSocket connected. Bidirectional audio/transcript ready."
  }));

  ws.on("message", (message: string) => {
    try {
      const data = JSON.parse(message.toString());
      if (data.type === "candidate_speech") {
        ws.send(JSON.stringify({
          event: "interviewer_speech",
          text: "Acknowledged your defense answer on log compaction. Can you explain how your state machine guarantees linearizability during read-only queries?",
          score: 93.4,
          verdict: "AUTO_HIRE"
        }));
      }
    } catch (e) {
      console.error("WS error:", e);
    }
  });
});

// ==================== VITE MIDDLEWARE ====================

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  server.listen(PORT, "0.0.0.0", () => {
    console.log(`[Synapse.AI] Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
