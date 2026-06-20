# Orionfold Proof Receipt

> Prove what your AI can do before you trust it.

A local-first, hybrid-capable **Proof Receipt** product. It runs private proof tests
across local and cloud AI workflows, compares quality, speed, cost, failure cases, and
privacy boundaries, then exports a repeatable Proof Receipt you can keep, rerun, or share.

The central artifact is the **Proof Receipt**. The user is not here to watch AI run —
they are here to decide what AI to trust.

---

## Status: Gate 5 — proof-receipt vertical slice

The core loop works end-to-end, **mock-only and keyless**: pick the bundled sample dataset,
run two deterministic mock candidates, see the leaderboard, inspect failure cases (including
a surfaced provider error), and export a Proof Receipt in Markdown, HTML, and JSON — each
stamped with a config hash, timestamp, and schema version. Real providers (Ollama +
OpenAI-compatible) land in Gate 6.

Run it: `bash scripts/build.sh && uv run orionfold up`, open the cockpit, click **Run proof**,
then export a receipt. See a sample under [`samples/receipts/`](samples/receipts/).

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

Target install (post-v0): `uv tool install orionfold-proof && orionfold up`.

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
src/ web/ samples/ tests/ e2e/ scripts/   Empty target dirs for the approved build
```

## Planned stack (boring on purpose)

- **Backend:** Python 3.12+, `uv`, FastAPI, Pydantic, Typer, SQLite, httpx, pytest, ruff, pyright.
- **Frontend:** Vite, React, TypeScript, Tailwind, shadcn/Radix, TanStack Query, Zod, React Hook Form, Recharts.
- **Testing:** pytest, Vitest, Playwright (visual + e2e), deterministic mock providers.

Target install (post-v0): `uv tool install orionfold-proof && orionfold up` → `http://localhost:8787`.
Dev: `uv sync && pnpm --dir web install && uv run orionfold dev` (see Quickstart above).

PyPI distribution name: `orionfold-proof` (CLI command `orionfold`). The brand names
`orionfold` and `orionfold-arena` are reserved as placeholders for future products.

See `CLAUDE.md` for full operating guidance and `docs/opportunity.md` for the strategy.
