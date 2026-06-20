# 2026-06-19 — Gate 4: runnable skeleton (CLI + FastAPI + Vite shell)

## Summary
- Built the Gate 4 skeleton end-to-end. **No proof logic, providers, datasets, scoring, or
  receipts** — deferred to Gates 5–6 per the charter.
- **Backend:** `pyproject.toml` (hatchling, py≥3.12, approved baseline deps only), Typer CLI
  `orionfold` with `up` (serve embedded build, no reload) and `dev` (uvicorn `--reload`),
  FastAPI `create_app()` factory with `GET /api/health` and a cockpit mount that serves the
  embedded SPA when built or a calm placeholder otherwise (so `up` is never dead).
- **Frontend:** Vite + React 19 + TS + Tailwind v4 (`@tailwindcss/vite`) cockpit shell with a
  "Local engine" health card (loading / connected / error states) via plain `fetch`
  (TanStack Query deferred to the vertical slice). One Vitest render test.
- **Embed path (ADR-0001 §3):** `scripts/build.sh` enforces the hard ordering — build
  `web/dist` → copy into `src/orionfold/server/static` → `uv build`. The static dir is
  git-ignored and force-included into the wheel via hatchling `artifacts`.
- Docs: README rewritten with a real Quickstart (dev + embedded-run + test); `.gitignore`
  ignores the generated `static/` dir.

## Verification
- `uv run pytest` → **3 passed** (health endpoint, placeholder root, CLI `--help` lists up/dev).
- `uv run ruff check` → clean; `uv run pyright src` → 0 errors.
- `pnpm --dir web test` (Vitest 3.2.6) → **2 passed**.
- `pnpm --dir web build` (`tsc --noEmit && vite build`) → dist emitted.
- `bash scripts/build.sh` → wheel `orionfold_proof-0.1.0-py3-none-any.whl` built; confirmed
  `orionfold/server/static/index.html` + assets are **inside the wheel** (`unzip -l`).
- Live browser check (`orionfold up`, port 8799 to avoid the parallel codex instance on 8787):
  served SPA renders the calm shell; health card shows green "Connected · orionfold-proof
  v0.1.0" — CLI→FastAPI→embedded SPA→`/api/health` all connect. Screenshot captured.
- No secrets: nothing networked yet; health body carries only status/service/version.

## Product impact
- The skeleton proves the install-time experience (one Python wheel, no Node at runtime) and
  the embedded-frontend packaging that every later gate depends on. The proof loop can now be
  built on a verified foundation.

## Risks
- **Two fixes during build:** (1) `vitest@2` pulled `vite@5` types clashing with `vite@6`
  plugins → bumped to `vitest@^3`; (2) project-reference `tsconfig.node.json` fought
  `noEmit`/`composite` → collapsed to a single tsconfig type-checked via `tsc --noEmit`.
  Both resolved; watch for recurrence on dep bumps.
- Starlette `TestClient` emits a deprecation warning (wants `httpx2`). Harmless now; revisit
  if it becomes an error on a future starlette/httpx bump.
- Embedded `static/` is gitignored + force-included — correct, but the force-include is the
  single point that keeps the wheel from shipping UI-less. `build.sh` asserts `index.html`
  exists before `uv build`; keep that assertion.
- Empty `.gitkeep` dirs remain for unbuilt modules (proof/providers/receipts/scoring/storage/
  domain + web features); they fill in during Gates 5–6.

## Next recommended step
- **Gate 5: the proof-receipt vertical slice** — sample dataset → proof run (mock_good /
  mock_bad) → leaderboard → receipt export (Markdown/HTML/JSON), thin and verified, plus a
  Playwright happy-path smoke. Use the `proof-receipt-vertical-slice` skill. This pulls in
  SQLite storage, the domain models, the matrix engine, scoring primitives, and the receipt
  exporter — start in plan mode.
