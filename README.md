# Orionfold Proof Receipt

> Prove what your AI can do before you trust it.

A local-first, hybrid-capable **Proof Receipt** product. It runs private proof tests
across local and cloud AI workflows, compares quality, speed, cost, failure cases, and
privacy boundaries, then exports a repeatable Proof Receipt you can keep, rerun, or share.

The central artifact is the **Proof Receipt**. The user is not here to watch AI run —
they are here to decide what AI to trust.

---

## Status: scaffolded — pre-implementation

This repository currently contains the **Claude Code operating setup and docs context
system only**. No product code has been written yet, by design: the workflow requires an
operator interview and an approved release charter before implementation begins.

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
Dev: `uv sync && pnpm install && uv run orionfold dev`.

PyPI distribution name: `orionfold-proof` (CLI command `orionfold`). The brand names
`orionfold` and `orionfold-arena` are reserved as placeholders for future products.

See `CLAUDE.md` for full operating guidance and `docs/opportunity.md` for the strategy.
