# AGENTS.md

## Layout
- The real project is `synapse.ai---lead-radar-&-code-defense/` (folder name contains `&` — always quote it in shell commands). Repo root has only this file and a stub README.
- Frontend: React 19 + Vite 6 + Tailwind 4 in `src/`, split into `tab1-leads/` and `tab2-assessment/`.
- Dev/prod server: `server.ts` (Express + `ws` + Vite middleware). It serves **both** the UI and the whole `/api/v1/*` API on port **3000** (hardcoded). API data lives in in-memory seeded arrays in `server.ts` — no DB, resets on every restart.
- `backend/` is a parallel FastAPI implementation of the same `/api/v1` routes (Postgres + pgvector + alembic). Nothing wires it up: no npm script, and the frontend's relative `fetch('/api/v1/...')` calls never reach it. Only run it if explicitly asked: `pip install -r requirements.txt`, needs Postgres (`postgresql+asyncpg://postgres:postgres@localhost:5432/synapse_db`), then `uvicorn app.main:app --reload` from `backend/`. Startup tolerates DB failure, but DB-backed routes will 500.

## Commands (run from `synapse.ai---lead-radar-&-code-defense/`; requires Node.js)
- `npm install`
- `npm run dev` → **http://localhost:3000** (UI + API together, one process)
- `npm run lint` → `tsc --noEmit` — this is the only verification step. No eslint/prettier config, no test suite, no CI, no pre-commit hooks anywhere in the repo.
- `npm run build`, then set `NODE_ENV=production` before `npm start`. The `start` script (`node dist/server.cjs`) does **not** set it, so plain `npm start` boots Vite dev middleware instead of serving `dist/`.

## Environment gotchas
- README says put `GEMINI_API_KEY` in `.env.local` — that file doesn't exist and nothing loads it (`dotenv` is a dependency but is never imported). Export it in the shell before `npm run dev` if you want live Gemini calls; otherwise every AI endpoint silently falls back to hardcoded canned responses and the app still works end to end.
- `DISABLE_HMR=true` turns off Vite HMR and file watching (`vite.config.ts`). Keep that block intact — it exists to stop flicker during agent edits.
- Never run `vite`/`vite dev` directly: there is no proxy config, so the UI loads but all `/api/v1/*` fetches 404.

## Windows gotchas (verified the hard way)
- The project folder name contains `&`, which breaks npm's default cmd.exe script shell: `npm run lint` dies with errors like `'-code-defense\node_modules\.bin\' is not recognized`. Fix once per machine: `npm config set script-shell powershell` (user-level `.npmrc`).
- With PowerShell as script-shell, npm runs the `.ps1` shims in `node_modules\.bin`, which the default execution policy blocks. Fix: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force`.
- A shell opened before Node was installed won't see it: refresh with `$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")`.
- Both fixes are already applied on this machine; `npm run lint` and `npm run dev` work.

## Conventions
- Feature dirs mirror across stacks: `src/tab1-leads/feature1-ingestion` ↔ `backend/app/tab1_leads/feature1_ingestion`. The routes that actually serve traffic are the ones in `server.ts` — add new endpoints there, not only in FastAPI.
- Path alias `@/` → project root (both `tsconfig.json` and `vite.config.ts`).
- Model IDs differ per stack: `server.ts` uses `gemini-2.5-flash`; Python services hardcode `gemini-3.8-flash` REST calls.
