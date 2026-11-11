# Synapse.AI frontend

React + TypeScript + Vite + Tailwind. Talks to the FastAPI backend in `../backend` (same-origin `/api`, proxied by Vite in development).

```bash
npm install
npm run dev      # http://localhost:5173  (FastAPI must run on :8000, or set VITE_API_PROXY_TARGET)
npm run verify   # tsc + architecture check + tests + build
npm run build && npm run preview
```

See the repository root `startup.md` for the complete stack (PostgreSQL, Alembic, FastAPI).
