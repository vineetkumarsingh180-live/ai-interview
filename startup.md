# Startup

Run everything from `synapse.ai---lead-radar-&-code-defense/` (quote the folder name in shells — it contains `&`).

## One-time machine setup (Node)

If Node.js is not installed: `winget install OpenJS.NodeJS.LTS`, then refresh the shell PATH:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
```

If npm scripts fail with `'-code-defense\node_modules\.bin\' is not recognized` or `.ps1 cannot be loaded ... running scripts is disabled`:

```powershell
npm config set script-shell powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
```

Both are already applied on this machine.

## Frontend + Node backend (the app you actually use)

```powershell
cd "C:\Users\ujjai\Downloads\ai-interview\synapse.ai---lead-radar-&-code-defense"
npm install      # first time only
npm run dev
```

- **URL: http://localhost:3000**
- One process (`tsx server.ts`) serves **both**:
  - frontend (React + Vite dev middleware) at `/`
  - backend API (Express) at `/api/v1/*`, WebSocket at `ws://localhost:3000/ws/voice`
- API data is in-memory seed data — no database; resets on restart.
- Optional: `$env:GEMINI_API_KEY="your-key"` before `npm run dev` for live Gemini calls.
  Without it, every AI endpoint falls back to hardcoded canned responses (app still works).
- Health check: http://localhost:3000/api/health
- Verify only: `npm run lint` (= `tsc --noEmit`). No tests exist.
- Stop: Ctrl+C the `npm run dev` process (or kill the `node`/`tsx` process on port 3000).

Production build (rarely needed):

```powershell
npm run build
$env:NODE_ENV="production"; npm start   # NODE_ENV must be set, or it boots Vite dev middleware instead of dist/
```

## Standalone Python backend (optional, NOT used by the frontend)

`backend/` is a parallel FastAPI implementation of the same `/api/v1` routes. The frontend
fetches relative URLs, so it always hits the Express server above — this backend only matters
if you explicitly want to develop it.

Prerequisites: Python 3.11+, and PostgreSQL running locally with a `synapse_db` database
(default URL: `postgresql+asyncpg://postgres:postgres@localhost:5432/synapse_db`,
override with `DATABASE_URL`).

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- URL: http://localhost:8000 (docs at http://localhost:8000/api/v1/docs)
- Startup tolerates a missing database (it logs a warning), but DB-backed routes will fail
  until Postgres is up and migrations are applied: `alembic upgrade head`.
