# Release Charter — Orionfold Proof Receipt v0

- **Status:** Accepted (operator-approved 2026-06-19 — Gate 2 passed)
- **Date:** 2026-06-19
- **Decisions locked (interview):** primary persona = AI consultant/studio · proof scope = text examples only · providers = mock pair + Ollama + OpenAI-compatible · receipt formats = Markdown + HTML + JSON.

## v0 scope (in)

**Core loop**
- Local project creation (SQLite, append-only migrations).
- Proof Brief wizard: task name, decision question, success criteria, privacy boundary, notes.
- Dataset import: JSONL, CSV, Markdown, and pasted examples → frozen input/expected text pairs.
- Candidate abstraction returning a uniform `ProviderResult` (incl. on error).
- Providers: `mock_good`, `mock_bad` (deterministic, keyless), `ollama` (local), `openai_compatible` (hosted; LM Studio rides this profile).
- Simple rubric definition + scoring primitives (e.g. exact/contains/similarity-style checks + optional LLM-as-judge later).
- Matrix run engine (candidates × examples) capturing output, scores, latency, estimated cost.
- Failure-case browser.
- Leaderboard: quality, latency, estimated cost, failure count, privacy mode, recommendation.
- Proof Receipt export: **Markdown + HTML + JSON**, each with config hash + timestamp.
- README quickstart + one end-to-end demo dataset.

**Explicitly text-only:** no document ingestion, no retrieval/RAG in v0 (deferred).

## v0 scope (out / defer list)

- Document ingestion + minimal RAG template (first thing after v0).
- LM Studio as a *distinct* SDK integration (covered by OpenAI-compatible profile for now).
- Bedrock (stub/profile only if operator later approves; no full support).
- Multi-user SaaS, team auth, billing, cloud DB, hosted projects, native desktop shell.
- Model training / fine-tuning UI, agent orchestration, scheduled jobs, marketplace, RBAC.
- Regression diffing between runs, human review queues, policy packs (P1, post-v0).

## User journey (happy path)

1. `orionfold up` → browser opens at `http://localhost:8787`.
2. Create Proof Run → choose the **Model Compare** template.
3. Import sample dataset (or use the bundled demo).
4. Select candidates: `mock_good`, `mock_bad`, and one of Ollama / OpenAI-compatible.
5. Run proof → watch progress.
6. View leaderboard → open at least one failure case.
7. Export Proof Receipt (Markdown, HTML, JSON) → view the files.

## Acceptance criteria (v0 is done only if all true)

- A new user can run the app locally from a fresh checkout via the documented quickstart.
- A sample proof run completes **without any external API keys** (mock providers).
- The user can compare **at least two candidates** and see the leaderboard in the UI.
- The user can inspect **at least one failure case**.
- The user can export a **Markdown, an HTML, and a JSON** receipt, each with a config hash + timestamp.
- Ollama and OpenAI-compatible providers work when configured; their tests **skip gracefully** without credentials.
- **No secrets** are logged, printed, committed, or written into any receipt/screenshot.
- Backend tests (`uv run pytest`), frontend units (`pnpm test`), `pnpm build`, and a Playwright happy-path e2e all pass.
- Each interactive view has empty/loading/error/populated states; core action is keyboard-accessible.
- v0 non-goals are documented; the worktree is clean.

## Tech stack

- **Backend:** Python 3.12+, `uv`, FastAPI, Pydantic, Typer, SQLite (stdlib `sqlite3`), httpx, pytest, pytest-asyncio, ruff, pyright.
- **Frontend:** Vite, React, TypeScript, Tailwind, shadcn/Radix, TanStack Query, Zod, React Hook Form, Recharts.
- **Testing:** pytest, Vitest, Playwright (e2e + visual), deterministic mock providers, fixtures under `tests/fixtures/`.
- No LangChain/LlamaIndex/Celery/Postgres/Redis; no Next.js. (See `docs/tech/dependency-policy.md`.)

**Packaging & naming**
- Single PyPI wheel; the **Vite/React cockpit is pre-built and embedded** in the wheel, served by FastAPI. No Node at runtime; `pnpm` is build-time only. Build order: compile `web/dist` → copy into package → `uv build`.
- **Distribution name:** `orionfold-proof` (CLI command: `orionfold`). Install: `uv tool install orionfold-proof`; launch: `orionfold up`.
- **Reserved placeholders on PyPI:** `orionfold` (umbrella/brand) and `orionfold-arena` (future product). All three names confirmed available 2026-06-19.
- Company: Orionfold LLC; product: Proof; trademark for "Orionfold" filed (pending).

## Risks & mitigations

- **Scope risk — both providers + 3 formats is wider than the absolute-thinnest slice.**
  Mitigate: build and verify the loop **mock-only first** (Gate 5), then add Ollama +
  OpenAI-compatible (Gate 6), then confirm all 3 export formats. Each is a checkpoint.
- **Provider flakiness / no creds.** Mitigate: deterministic mocks are the default path;
  real-provider tests skip without credentials; provider errors are actionable.
- **Receipt feature creep.** Mitigate: schema-versioned exports; `receipt-quality-review`
  skill gate on any change.
- **Secret leakage.** Mitigate: path-scoped rules on `providers/` + `receipts/`, `.env`
  denied in permissions, `security-secrets-review` before release.
- **Cost-estimate accuracy for hosted models.** Mitigate: label costs as *estimated*;
  capture token counts; never block the local-first path on cost precision.

## First demo script

1. `orionfold up` → app opens.
2. Create Proof Run → "Model Compare".
3. Select sample dataset: _Investment memo summarization sample_.
4. Candidates: `mock_good`, `mock_bad`.
5. Run proof → view leaderboard.
6. Open a failure case.
7. Export Proof Receipt → show the Markdown file.
8. Tagline: "Private, repeatable proof of which AI workflow is worth trusting."

## Next gate

On approval → **Gate 3: ADR-0001** (`docs/adr/0001-local-first-proof-receipt-architecture.md`):
local-first rationale, Python+FastAPI+Vite, SQLite, no LangChain/LlamaIndex, provider
abstraction, and test strategy. No product code until the ADR is approved.
