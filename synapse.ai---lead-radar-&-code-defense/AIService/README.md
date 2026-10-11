# AIService

Internal Python package with Synapse.AI's AI/ML logic. It is a **library**: no HTTP server, no
database, no web framework. FastAPI (`backend/`) is the only API and the only caller.

```
React -> FastAPI -> AIService -> provider (Gemini)
                \-> PostgreSQL   (AIService never touches it)
DbIngestion -> PostgreSQL        (no AI analysis there)
```

| Package | Owns |
|---|---|
| `frontend/` | presentation only; never talks to Gemini, PostgreSQL or AIService |
| `backend/` | endpoints, validation, persistence, transactions, review states, orchestration |
| `DbIngestion/` | getting external data in (adapters, validation, dedup, provenance, run log) |
| `AIService/` | provider access, prompts, structured extraction, evidence checks, intelligence capabilities |
| PostgreSQL + pgvector | persistent data; schema only via `backend/alembic` |

## Layout

```
AIService/
  pyproject.toml
  aiservice/
    errors.py                      error taxonomy (stable `code` values)
    providers/base.py              LLMProvider Protocol, Generation, Usage, parse_model
    providers/gemini.py            GeminiProvider (the only vendor-specific file)
    prompts/__init__.py            versioned prompts (version is stored with results)
    shared/text.py                 deterministic evidence checks
    lead_intelligence/             analyze_post (classification + extraction), draft_outreach
    code_intelligence/             prepare_evidence, RepositoryEvidence.facts, CodeIntelligence.analyze
    interview_intelligence/        follow_up_question, repository_questions
  tests/                           mocked-provider tests
```

## Install and test

```bash
backend/.venv/bin/pip install -e AIService           # also pulled in by backend/requirements.txt (-e ../AIService)
cd AIService && ../backend/.venv/bin/python -m pytest   # no network, no key needed
```

## Configuration

`GEMINI_API_KEY` (and optional `GEMINI_MODEL`, default `gemini-2.5-flash`) are read by the **backend**
(`app/shared/config.py` from environment or `backend/.env`, never committed) and handed to
`GeminiProvider` by `app/shared/ai.py`. AIService itself reads no environment. The key is sent in the
`x-goog-api-key` header, never in a URL, and never logged or put in a repr. Without a key every
capability returns `status="unavailable", reason="not_configured"`; nothing is invented.

Provider behaviour: per-request timeout (default 20 s); transient failures (timeout, network, 5xx,
429) are retried up to `max_retries` (default 2) with exponential backoff and `Retry-After`;
401/403/404/other 4xx are not retried; unusable 200 answers raise `InvalidProviderResponse`. Token
usage is reported only when the provider returns it.

## How FastAPI calls AIService

Business modules never import `aiservice`. Each module declares a port (a Protocol plus small
dataclasses) in its `interfaces.py`; `backend/app/core/wiring.py` binds an adapter from
`backend/app/core/ai_adapters.py` that calls AIService:

| Module | Port | AIService call |
|---|---|---|
| job_lead_radar | `LeadAnalyzer.analyze_post` | `LeadIntelligence.analyze_post` |
| job_lead_radar | `OutreachDrafter.draft` | `LeadIntelligence.draft_outreach` |
| voice_defense | `Interviewer.follow_up` | `InterviewIntelligence.follow_up_question` |
| code_verifier | `RepositoryAnalyzer.analyze` | `prepare_evidence` + `CodeIntelligence.analyze` (seam only) |

Capability results are status objects (`analyzed` / `generated` / `unavailable` / `invalid_response`).
The module decides what that means (`awaiting_analysis`, `needs_review`, 503, ...) and persists it.

## Honesty guarantees (enforced in code and tests)

- **Lead extraction** asks for a verbatim quote per field and verifies it against the post. Values
  without support are dropped and listed in `dropped_fields`; numbers must occur in the post; tech
  stack items must occur in the text; urgency/location/clearance need a verified quote.
- **Code intelligence** only analyses files the caller supplies, excludes secret-like and binary files
  before prompting, bounds sizes, and discards findings whose quote is not in the cited file. It never
  claims coverage, confirmed vulnerabilities or authorship. It never fetches or executes anything.
- **Interview intelligence** never scores or decides; repository questions must cite supplied files and
  are otherwise discarded (no generic fallback).
- AI output is an interpretation, not a verified fact; human review stays required.

## Status of capabilities

| Capability | Status |
|---|---|
| Gemini provider transport, retry, error taxonomy | implemented, **mock-tested** (HTTP layer mocked); not live-verified |
| Lead extraction with evidence verification | implemented, mock-tested; wired into `/leads/ingest/trigger` and `/parse-text` |
| Outreach drafting | implemented, mock-tested; wired into `/leads/outreach/generate` |
| Follow-up interview question | implemented, mock-tested; wired into `/assessment/voice/turn` |
| Repository evidence preparation + analysis | implemented, mock-tested; **not wired to content**: no repository content is fetched, so the backend seam answers `unavailable: repository_content_not_available` |
| Repository-specific interview questions | implemented, mock-tested; not wired (needs repository content) |
| Embeddings, similarity, matching, ranking | **not implemented** (design below) |
| Live Gemini verification | **blocked**: `GEMINI_API_KEY` is not configured |

## Planned: embeddings, matching and evaluation (not implemented)

No code exists because no real vectors, labelled data or evaluation set exist. Nothing may produce a
match score, similarity or ranking until the following are in place:

- **Inputs:** job-post text/structured fields (from `job_leads`) and candidate evidence (approved,
  human-reviewed repository evidence and interview observations). Embeddings are produced by a
  provider embedding model and stored in `lead_embeddings` (pgvector, dimension fixed per model).
- **Outputs:** a ranked list with the *features that contributed*, model name and version, embedding
  model/version, and the data snapshot; an explicit "not measured" when inputs are missing.
- **Assumptions:** cosine similarity over embeddings is a retrieval signal, not a quality judgement;
  scores are only comparable within one model version.
- **Data requirements:** a labelled set of (job, candidate, human outcome) pairs gathered with consent,
  large enough per role family to evaluate; deduplicated and time-split.
- **Evaluation:** offline metrics (precision@k, NDCG, calibration) on a held-out split before release;
  per-group error analysis; regression suite pinned to the model version.
- **Fairness:** exclude protected attributes and obvious proxies from features; review group-wise
  outcomes; keep a human in the loop and a way to contest results.
- **Provenance and versioning:** persist model id, prompt/feature version, embedding model, run id and
  input hashes with every score so any value can be traced and recomputed.

## AIService vs DbIngestion

DbIngestion brings external data in (validation, dedup, provenance, run log) and performs no AI.
AIService interprets data it is handed and persists nothing. FastAPI connects them through the database
and owns every write.

## Working independently

Four developers can own the four product modules (frontend folder + backend package each) without
touching each other: cross-module needs are ports bound in `app/core/wiring.py`/`src/app/*`. The AI
engineer works inside `AIService/` against the stable result types above; the architecture checker
(`backend/scripts/check_architecture.py`) fails the build if a module imports `aiservice`, AIService
imports FastAPI/ORM/backend code, a provider SDK is used outside `providers/`, or a second server appears.
