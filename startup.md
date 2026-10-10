# Startup

Stack: React + Vite (frontend) → FastAPI (only backend) → PostgreSQL + pgvector. See `CLAUDE.md` for the rules and `handoff.md` for status (both local, git-ignored).

All paths below are inside `synapse.ai---lead-radar-&-code-defense/` (quote it: it contains `&`).

```bash
# 1. PostgreSQL  (macOS Homebrew; the locale variable is required)
export LC_ALL=en_US.UTF-8
pg_ctl -D /opt/homebrew/var/postgresql@18 -l /opt/homebrew/var/log/postgresql@18.log start

# 2. One-time database setup (needs a superuser; creates only role synapse_app + database synapse_dev)
psql -h localhost -d postgres -f backend/db/setup_local_db.sql      # pgvector must be installed: brew install pgvector

# 3. Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                       # optional: add GEMINI_API_KEY
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --port 8000 # http://127.0.0.1:8000/api/v1/docs

# 4. Frontend (new terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173
```

Optional demo fixtures: `cd backend && .venv/bin/python scripts/seed_demo.py` (labelled, removable with `--remove`).
Checks: `cd frontend && npm run verify` and `cd backend && .venv/bin/python -m pytest`.
