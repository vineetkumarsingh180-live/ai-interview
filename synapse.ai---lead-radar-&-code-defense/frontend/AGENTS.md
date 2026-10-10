# AGENTS.md

Read the repo-root `CLAUDE.md` first; it is the source of truth.

- This package is the React/Vite UI only. The API is FastAPI (`../backend`); there is no Node server.
- `npm run dev` (http://localhost:5173) proxies `/api` to FastAPI (`VITE_API_PROXY_TARGET`, default `http://127.0.0.1:8000`).
- `npm run verify` = typecheck + architecture check + tests + build. Run it before finishing.
- Module boundaries: `src/modules/<name>` may import only itself and `@shared/*`; `src/app` composes modules through their `index.ts`.
- Never fabricate data when an API call fails; show the error or a "Not measured" state.
