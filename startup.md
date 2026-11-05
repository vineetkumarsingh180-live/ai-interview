# Startup

Stack: React + Vite (frontend) + FastAPI (only backend) + PostgreSQL + pgvector.

All paths below are run from the project root directory.

```bash
# 1. PostgreSQL (macOS Homebrew; the locale variable is required)
export LC_ALL=en_US.UTF-8
pg_ctl -D /opt/homebrew/var/postgresql@18 -l /opt/homebrew/var/log/postgresql@18.log start

# 2. One-time database setup (needs a superuser; creates only role synapse_app + database synapse_dev)
psql -h localhost -d postgres -f backend/db/setup_local_db.sql      # pgvector must be installed: brew install pgvector

# 3. Backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
# (requirements.txt also installs the internal AI package: -e ../AIService)
cp .env.example .env                       # optional: add GEMINI_API_KEY
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --port 8000 # http://127.0.0.1:8000/api/v1/docs

# 4. Frontend (new terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173
```

Optional demo fixtures: `backend/.venv/bin/python DbIngestion/ingest.py demo load` (labelled, removable with `demo remove`).
Checks: `cd frontend && npm run verify` and `cd backend && .venv/bin/python -m pytest`.
