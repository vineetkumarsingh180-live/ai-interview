# DbIngestion

External sources → **DbIngestion** → PostgreSQL → FastAPI → React.

A Python ingestion package (not a backend). It validates operator-provided input, deduplicates it,
stamps provenance, and persists it **through each backend module's public ingestion interface**.
Schema is owned by `backend/alembic`; this package has no models.

## Run (from the project root, with the backend virtualenv)

```bash
export LC_ALL=en_US.UTF-8
PY=backend/.venv/bin/python

# Job posts you provide (never fetched from a website)
$PY DbIngestion/ingest.py posts --file posts.json              # .json / .jsonl
$PY DbIngestion/ingest.py posts --file post.txt --platform reddit
$PY DbIngestion/ingest.py posts --text "..." --platform twitter --source-url https://... --note "why"

# GitHub repository metadata via GitHub's REST API (no cloning, no code execution)
$PY DbIngestion/ingest.py github https://github.com/<owner>/<repo> [--candidate-name "..."] [--target-role "..."]
$PY DbIngestion/ingest.py github --file repos.txt              # one URL per line

# Labelled development fixtures (fixtures/demo/*.json -> is_demo = true)
$PY DbIngestion/ingest.py demo load | demo remove

# Audit and undo
$PY DbIngestion/ingest.py runs
$PY DbIngestion/ingest.py rollback --run <run-id>

# Any write command accepts --dry-run (real validation and dedup, nothing written) and --json
```
Exit codes: `0` ok, `1` finished but some records were rejected/failed, `2` could not run.

## Post file format
```json
{"records": [{
  "platform": "twitter|linkedin|reddit|telegram",
  "text": "the post, exactly as you have it",
  "external_id": "optional source id",
  "author_handle": "@x", "author_name": "X", "source_url": "https://...", "posted_at": "2026-01-01T00:00:00Z",
  "note": "optional provenance note",
  "structured": {"role_title": "...", "company_name": "...", "tech_stack": ["..."], "location_mode": "Remote"}
}]}
```
`structured` is optional and is only what *you* typed; without it the post is stored as
"awaiting analysis" (no lead is created, no AI is called here).

## Guarantees
- Original text stored unchanged; `verification_status = unverified` (never "verified").
- Deduplication: sha256 of (platform + normalised text); GitHub rows by GitHub's repository id / URL.
- One transaction per record; a failing record is reported and the rest continue.
- Every row carries `source_type`, `ingestion_run_id`, `is_demo`; every run is recorded in `ingestion_runs`.
- GitHub rows contain only what GitHub returned. Nothing is analysed or scored.

## Tests
`backend/.venv/bin/python -m pytest DbIngestion` (persistence tests use the real database inside a rolled-back transaction; GitHub is mocked).
