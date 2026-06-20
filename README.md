# Orionfold Proof Receipt

> Prove what your AI can do before you trust it.

A local-first, hybrid-capable **Proof Receipt** product. It runs private proof tests
across local and cloud AI workflows, compares quality, speed, cost, failure cases, and
privacy boundaries, then exports a repeatable Proof Receipt you can keep, rerun, or share.

The central artifact is the **Proof Receipt**. The user is not here to watch AI run —
they are here to decide what AI to trust.

---

## Status: Gate 7 — ship candidate

The full v0 loop works end-to-end. **Keyless out of the box:** pick the bundled sample
dataset, run two deterministic mock candidates, see the leaderboard, inspect failure cases
(including a surfaced provider error), and export a Proof Receipt in Markdown, HTML, and
JSON — each stamped with a config hash, timestamp, and schema version (currently v3).

**Real providers when you configure them:** the same loop runs against local and cloud
models — Ollama and LM Studio (local), plus OpenAI, OpenRouter, Google Gemini, and
Anthropic (cloud) — behind one uniform result boundary. Cloud candidates appear **only when
their API key resolves**; the keyless mock path stays the instant default. See
[Configure providers](#configure-providers) below.

Run it: `bash scripts/build.sh && uv run orionfold up`, open the cockpit, click **Run proof**,
then export a receipt. See a sample under [`samples/receipts/`](samples/receipts/), a
guided walkthrough in [`docs/demo-script.md`](docs/demo-script.md), and the release history
in [`CHANGELOG.md`](CHANGELOG.md).

## Quickstart

Prerequisites: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), and
[`pnpm`](https://pnpm.io/) (build-time only).

**Develop** (API with reload + Vite dev server with `/api` proxy):

```bash
uv sync                       # backend env
pnpm --dir web install        # cockpit deps
uv run orionfold dev          # API at http://127.0.0.1:8787 (reload)
pnpm --dir web dev            # cockpit at http://localhost:5173 (proxies /api)
```

**Run the embedded build** (cockpit served by FastAPI — the install-time experience):

```bash
bash scripts/build.sh         # build cockpit -> embed -> build wheel
uv run orionfold up           # open http://localhost:8787
```

**Test:**

```bash
uv run pytest                 # backend (unit + integration; keyless)
pnpm --dir web test           # cockpit (Vitest)
pnpm --dir web exec playwright install chromium  # one-time, for e2e
pnpm --dir web e2e            # Playwright happy-path (boots the embedded build)
```

Target install: `uv tool install orionfold-proof && orionfold up`.

## Configure providers

The mock candidates need no setup. To prove **real** models, make their credentials
resolvable. Orionfold reads keys from two places, in order:

1. The **system environment** (preferred for CI / 12-factor).
2. A repo-root **`.env.local`** file (git-ignored; convenient for local dev).

The system environment **wins** when both are set; empty or whitespace-only values are
treated as absent. A cloud candidate is offered **only when its key resolves**, so the
cockpit never lists a model that can't run. Keys are never logged, printed, or written into
any receipt or screenshot.

Create `.env.local` at the repo root (an example, never commit real keys):

```bash
# .env.local — git-ignored. Set only the providers you want to prove.
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
GEMINI_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
```

Local providers need no key — just a reachable server: **Ollama** (`ollama serve`, models
pulled) and **LM Studio** (`lms server start`, a model loaded). Both are always offered.

**Defaults and overrides** — each profile ships a sensible default model and every knob is
env-overridable (set in `.env.local` or the environment; no code change):

| Profile | Default model | Model override | Endpoint override |
| --- | --- | --- | --- |
| Ollama (local) | `llama3.2` | `ORIONFOLD_OLLAMA_MODEL` | `OLLAMA_HOST` |
| LM Studio (local) | `local-model` | `ORIONFOLD_LMSTUDIO_MODEL` | `LMSTUDIO_BASE_URL` |
| OpenAI | `gpt-4o-mini` | `ORIONFOLD_OPENAI_MODEL` | `OPENAI_BASE_URL` |
| OpenRouter | `openai/gpt-4o-mini` | `ORIONFOLD_OPENROUTER_MODEL` | `OPENROUTER_BASE_URL` |
| Gemini | `gemini-2.5-flash` | `ORIONFOLD_GEMINI_MODEL` | — |
| Anthropic | `claude-haiku-4-5` | `ORIONFOLD_ANTHROPIC_MODEL` | — |

The model is part of a candidate's identity and feeds the run's `config_hash`, so changing
it produces a distinct, traceable receipt.

Two cross-cutting knobs apply to every provider:

- `ORIONFOLD_MAX_TOKENS` (default `2048`) — per-completion output cap. Raise it for local
  **reasoning** models (qwen3, deepseek-r1, gpt-oss), which spend the budget *thinking* and
  return empty content at a low cap.
- `ORIONFOLD_TIMEOUT_S` (default `120`) — per-request timeout. Raise it for slow local
  models. _(This is a fixed wall-clock value; a progress-based streaming timeout is a
  planned follow-up — see the worklog.)_

Other knobs: `ORIONFOLD_ENV_FILE` (point at a non-default env file) and `ORIONFOLD_DB`
(override the SQLite path; default `~/.orionfold/proof.db`).

> Estimated costs use a small built-in price table for the default models. An unknown model
> (e.g. OpenRouter's namespaced ids) shows `$0.00` — costs are labeled **estimated**, never
> authoritative.

## How development is structured

Work proceeds through operator-approved gates (see `CLAUDE.md` → *Release gates*):

1. ⏸ Product brief → `docs/product-brief.md`
2. ⏸ Release charter → `docs/release-charter.md`
3. ⏸ Architecture → `docs/adr/0001-local-first-proof-receipt-architecture.md`
4. Skeleton → 5. Vertical slice → 6. Provider integration → 7. Ship candidate

The ⏸ gates stop for your approval.

## Start here (operator)

In Claude Code, kick off product discovery:

```text
Read docs/opportunity.md. Do not code yet.

Use the product-release-interview skill: interview me with AskUserQuestion to clarify the
first release, challenge assumptions, and produce docs/product-brief.md and
docs/release-charter.md for a v0 a solo founder can build quickly.

Bias toward a local-first Proof Receipt product, not a broad cockpit, SaaS platform, or
generic local model runner.
```

Then, before activating tighter permissions, review and rename
`.claude/settings.json.example` → `.claude/settings.json`.

## What's in this scaffold

```text
CLAUDE.md                         Lean always-on operating guide (< 200 lines)
.claude/
  settings.json.example           Reviewable permissions/model template (rename to activate)
  rules/                          Path-scoped constraints (providers, receipts, storage)
  skills/                         9 procedural skills (interview, vertical slice, reviews, gates)
  agents/                         diff-reviewer · codebase-investigator · security-reviewer
docs/
  opportunity.md                  Market/product source (read once, summarize into brief)
  claude-context-and-ux-addendum.md  Context engineering + UX quality bar
  tech/                           reference-index · docs-update-log · dependency-policy
  ux/                             design system · usability/a11y/visual checklists · copy-deck
  adr/                            architecture decision records (template seeded)
  worklog/                        per-session summaries (template seeded)
src/orionfold/                    Backend: CLI, FastAPI server, domain, providers, storage
web/                              Vite/React cockpit (built + embedded into the wheel)
samples/                          Bundled demo dataset + sample receipts (MD/HTML/JSON)
tests/  scripts/                  pytest (unit + integration), Playwright e2e, build script
```

## Stack (boring on purpose)

- **Backend:** Python 3.12+, `uv`, FastAPI, Pydantic, Typer, SQLite, httpx, pytest, ruff, pyright.
- **Frontend:** Vite, React, TypeScript, Tailwind, shadcn/Radix, TanStack Query, Zod, React Hook Form, Recharts.
- **Testing:** pytest, Vitest, Playwright (visual + e2e), deterministic mock providers.

Install: `uv tool install orionfold-proof && orionfold up` → `http://localhost:8787`.
Dev: `uv sync && pnpm --dir web install && uv run orionfold dev` (see Quickstart above).

PyPI distribution name: `orionfold-proof` (CLI command `orionfold`). The brand names
`orionfold` and `orionfold-arena` are reserved as placeholders for future products.

See `CLAUDE.md` for full operating guidance and `docs/opportunity.md` for the strategy.
