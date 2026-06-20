# 2026-06-19 — Gate 5: proof-receipt vertical slice (mock-only)

## Summary
Built the thin end-to-end proof loop the whole product is organized around, **mock-only and
keyless** per the charter's scope-risk mitigation:

> bundled dataset → proof run (mock_good / mock_bad) → leaderboard → failure cases → Proof
> Receipt export (Markdown + HTML + JSON).

- **Domain (`domain/models.py`):** Pydantic single source of truth — `Example`, `Dataset`,
  `Rubric`, `Candidate`, `ProviderResult` (ADR-0001 §6 shape), `ResultRow`,
  `LeaderboardEntry`, `ProofBrief`, `ProofRun`, `ProofReport`.
- **Scoring (`scoring/rubric.py`):** deterministic stdlib primitives — exact / contains /
  normalized similarity (`difflib`). Default rubric similarity ≥ 0.8.
- **Providers (`providers/`):** `Provider` protocol + `safe_generate` boundary (errors
  returned, never raised; message-only and **redacted**). `mock_good` (returns expected) /
  `mock_bad` (generic answer, deterministically errors on ~1-in-5 inputs) — both keyless,
  `privacy="local"`, $0.00.
- **Engine (`proof/engine.py` + `leaderboard.py`):** candidates × examples matrix; provider
  errors become failing rows; `config_hash` = sha256[:12] over dataset/candidates/rubric/
  version (repeatable). Leaderboard ranks pass-rate ↓, latency ↑, cost ↑; marks one
  recommended.
- **Storage (`storage/`):** stdlib `sqlite3`, append-only `MIGRATIONS` tracked in
  `schema_migrations` (idempotent); reports stored as validated JSON; DB at
  `~/.orionfold/proof.db` (`ORIONFOLD_DB` override) with `0700`/`0600` perms.
- **Bundled dataset:** *Investment memo summarization* (5 examples) shipped **inside the
  package** (`src/orionfold/data/datasets/…json`, `importlib.resources`) so it survives a
  clean wheel install; seeded on startup.
- **Receipts (`receipts/export.py`):** Markdown/HTML/JSON, schema **v2** — each carries
  verdict (Ship / Ship-with-fallback / Keep-testing / Reject), summary, recommendation,
  leaderboard, failure cases, and a Repro block (run id + config hash + rerun command).
  Self-contained HTML, HTML-escaped; Markdown table/inline neutralized; no secrets, no full
  provider config.
- **API (`server/routes.py` + `app.py`):** `/api/datasets`, `/api/candidates`,
  `POST /api/runs`, `/api/runs/{id}`, `/api/runs/{id}/receipt.{md,html,json}` (download).
  DB migrate + seed in the FastAPI lifespan.
- **Cockpit (`web/`):** TanStack Query + Zod added. `lib/api.ts` (Zod-validated client),
  `features/proof/` (RunSetup · Leaderboard · FailureCases · ReceiptExport) orchestrated by
  `ProofCockpit`; `App.tsx` now the proof cockpit with a compact engine-status pill.

## Verification (evidence)
- `uv run pytest` → **30 passed** (scoring, providers incl. redaction + error invariant,
  engine determinism/leaderboard/config-hash, append-only migrations + round-trip, receipt
  provenance + secret-absence, full keyless API loop).
- `uv run ruff check` clean; `uv run pyright src` → 0 errors.
- `pnpm --dir web build` (tsc + vite) OK; Vitest → **3 passed**.
- **Playwright happy-path** (`e2e/playwright/proof.spec.ts`) → **1 passed**: open → run →
  leaderboard (recommended, 100% 5/5) → failure case (incl. surfaced provider error) →
  download all three receipts.
- **Browser visual check** (`orionfold up`, embedded build): setup / leaderboard / failure
  cases / receipt-export states all render calm and on-brand; engine pill "Connected".
- Wheel (`scripts/build.sh`) embeds the cockpit **and** the bundled dataset JSON
  (`unzip -l` confirmed).
- `receipt-quality-review`: added verdict/summary/repro, bumped schema v1→v2, re-exported;
  sample receipts in `samples/receipts/` are secret-free.
- `security-secrets-review` + `security-reviewer` subagent: no high-severity issues — no
  network capability, no secret in receipts/DB, HTML escaped, `raw_metadata` never
  persisted. `diff-reviewer`: no blocking; full plan adherence and rule compliance.

## Product impact
The core promise now works: a user runs a private, repeatable proof with no API keys and
exports a client-shareable receipt that names which candidate to trust and why. This is the
foundation every later gate extends.

## Risks / follow-ups
- **Packaging bug found & fixed:** `.gitignore` had an unanchored `data/` that excluded the
  bundled dataset from the wheel (build "succeeded" but shipped UI-less data). Fixed by
  anchoring to `/data/`; the `unzip -l` wheel check is the guard — keep it.
- **Redaction is defense-in-depth, not yet load-bearing:** `safe_generate` now scrubs
  key/token/Bearer patterns from error messages. The real test arrives in Gate 6 when
  httpx/SDK errors can echo credentials — verify redaction against real provider errors.
- Starlette `TestClient` httpx deprecation warning persists (harmless; revisit on bump).
- `created_at` normalized to trailing `Z` so live receipts match fixtures/samples.

## Next recommended step
- **Gate 6: provider integration** — add `ollama` (local) and `openai_compatible` (hosted;
  LM Studio rides this) behind the same `ProviderResult` boundary. Mock tests stay keyless;
  real-provider tests **skip without credentials**; confirm no keys are logged or written to
  receipts (exercise the redaction path against real errors). Then re-confirm all three
  export formats. Use `current-docs-check` before adding the httpx-based providers.
