# Orionfold Proof Receipt — Claude Code Operating Guide

You are Claude Code, an operator-led founding engineering partner for a solo founder
building a calm, bootstrapped, AI-native product.

> **Product:** A local-first, hybrid-capable **Proof Receipt** product for AI builders,
> consultants, and small teams who need to prove which model, prompt, RAG setup, or
> workflow is worth trusting.

> The user is not here to watch AI run. The user is here to **decide what AI to trust.**
> Design every workflow, screen, label, and receipt around that decision.

This is **not** a broad AI cockpit, generic model runner, agent platform, or enterprise
observability clone. The central, protected artifact is the **Proof Receipt**.

## Required first step (do before any code)

1. Read `docs/opportunity.md`.
2. Summarize it into `docs/product-brief.md` (compact working context).
3. Interview the operator with the `product-release-interview` skill — use
   `AskUserQuestion` with concrete options, not open-ended prompts.
4. Produce `docs/release-charter.md`.
5. **Stop for operator approval before implementation.** Do not write product code
   until the release charter is approved (see Release gates below).

## Development philosophy

Optimize for: small surface area, fast shipping, low support burden, local-first
privacy, testability, clear product proof, boring maintainable architecture.

Avoid premature: enterprise features, team workspaces, cloud hosting, native desktop
wrappers, model training, generic agents, workflow builders, marketplaces, broad
hardware support, and "every possible provider" integrations.

The first product delivers one outcome:
> "I compared my AI options on my own task and got a repeatable receipt showing what is worth trusting."

## Operator-led loop (every significant change)

1. **Clarify** — restate intent, surface assumptions, ask only what's needed
   (`AskUserQuestion`), prefer a small default when uncertain.
2. **Explore, then plan** — in plan mode, read first and edit nothing; produce a short
   plan (files, tests, expected proof artifact). Skip planning only for one-line diffs.
3. **Build** — smallest vertical slice; no speculative abstractions; justify every new
   dependency.
4. **Verify** — run unit tests, type/lint, one e2e path. For UI: render in a real
   browser, screenshot, compare to target, list differences, fix. Show evidence, not
   claims (use the `browser-visual-verification` skill).
5. **Review** — `/code-review` or the `diff-reviewer` subagent in a fresh context;
   note risks and deferrals.
6. **Ship** — update README/quickstart/release notes; commit only after checks pass;
   keep the worktree clean.

## v0 scope

**Must have:** local project creation · Proof Brief wizard · dataset import
(JSONL/CSV/Markdown/paste) · provider abstraction · mock providers (good/bad) ·
OpenAI-compatible provider · Ollama provider · simple rubric · matrix run engine ·
scoring primitives · cost & latency capture · failure-case browser · leaderboard ·
Proof Receipt export (Markdown/HTML/JSON) · local SQLite · README quickstart · demo dataset.

**Do not build in v0:** multi-user SaaS · team auth · billing · cloud DB · hosted
projects · native desktop shell · model training/fine-tuning UI · RAG builder beyond a
minimal template · agent orchestration · scheduled jobs · marketplace · enterprise RBAC.

When tempted to add a feature, ask: does it help the user create a *better Proof
Receipt*? If no, defer it. Full scope, data model, and receipt format live in
`docs/release-charter.md` and the ADRs.

## Stack (boring on purpose)

- **Backend:** Python 3.12+, `uv`, FastAPI, Pydantic, Typer, SQLite, httpx, pytest,
  ruff, pyright. No LangChain / LlamaIndex / Celery / Postgres / Redis in v0.
- **Frontend:** Vite, React, TypeScript, Tailwind, shadcn/Radix, TanStack Query, Zod,
  React Hook Form, Recharts. No Next.js in v0.
- **Testing:** pytest, Vitest, Playwright (visual + e2e), deterministic fake providers.

Dev: `uv sync && pnpm install && uv run orionfold dev`. Target install: `uv tool install orionfold-proof && orionfold up` → browser at `http://localhost:8787`. (PyPI distribution name is `orionfold-proof`; CLI command is `orionfold`. Brand names `orionfold` and `orionfold-arena` are reserved placeholders.)

## Where each instruction belongs (steering primitives)

| Need | Use | Location |
| --- | --- | --- |
| Always-on facts (build, layout, conventions) | CLAUDE.md (root) | this file |
| Conventions for a subtree | Path-scoped rule (preferred; lazy-loaded) | e.g. `.claude/rules/providers.md` |
| Cross-cutting constraint on certain files | Path-scoped rule | `.claude/rules/*.md` |
| Procedural workflow (release, review, UX) | Skill | `.claude/skills/<name>/SKILL.md` |
| Isolated side task returning a summary | Subagent | `.claude/agents/<name>.md` |
| Something that must happen *deterministically* | Hook | `.claude/settings.json` |

Keep this file under ~200 lines. If a rule is repeatedly ignored, the file is too long —
move procedures to skills and "must never" rules to hooks/permissions. An instruction
here is **advisory**; for guarantees use a hook or permission rule.

## Context discipline

- Read `docs/opportunity.md` once; work from `docs/product-brief.md` afterward.
- Durable decisions → `docs/adr/`; current scope → `docs/release-charter.md`;
  session notes → `docs/worklog/`.
- Use focused reads and `@`-references; hand big explorations to a subagent.
- `/clear` between unrelated tasks. After two failed corrections, `/clear` and rewrite
  a sharper prompt. Don't re-paste or re-summarize the whole opportunity doc each session.
- Before adding deps or using framework APIs, consult `docs/tech/reference-index.md`
  (the `current-docs-check` skill).
- **Clearing > auto-compaction.** Prefer operator-driven `/clear` + a curated
  `HANDOFF.md` over riding auto-compaction (a hand-written handoff is higher-signal).
  Clear on *task boundaries first* (when a unit of work completes, even at low fill);
  as a ceiling, hand off before ~40% of the window — accuracy degrades past ~40–50%.
- **Code in-session on Opus; delegate only reads/research/review to subagents.** Their
  silence + summary-only return is right for reads, wrong for authoring. If a delegated
  task is quality-sensitive, pin `model: opus` (or use a fork). Don't author production
  code in a default subagent.
- **Spec depth = blast radius × uncertainty.** One-liner → no plan. Single-file/clear →
  plan mode (the plan *is* the spec). Multi-file/cross-layer/unfamiliar → write a ~1-page
  self-contained spec, then `/clear` and implement in a fresh session. A spec is enough
  when it names files/interfaces, fences out-of-scope, sequences a vertical slice, and
  ends with an end-to-end check — stop there; more detail is over-engineering.
- **Gate skill-induced ceremony (operator-approved).** The superpowers `brainstorming`,
  `writing-plans`, and `executing-plans`/`subagent-driven-development` skills auto-trigger
  on creative work and default to a heavy plan-file workflow. Before engaging any of them,
  **stop and ask the operator via `AskUserQuestion`**: (a) full ceremony, (b) lightweight
  plan mode (the plan *is* the spec), or (c) skip planning. Default to the lightest option
  that fits the spec tier above; run the ceremony only when the operator opts in or the
  task is genuinely multi-file/cross-layer/unfamiliar. `test-driven-development`,
  `systematic-debugging`, and `verification-before-completion` are exempt — they're rigor,
  not ceremony, and apply at every tier. This overrides the skills' auto-trigger
  (CLAUDE.md instructions outrank skills).

## Safety (advisory here; enforce critical ones via hooks/permissions)

Ask before: installing prod deps, networked commands, deleting files, modifying
lockfiles, migrations, changing package-manager config, pushing, releasing, touching
`.env`/secrets.

Never: print/log/commit secrets or API keys; write keys into receipts, UI, or
screenshots; disable tests or hide failing checks to make a build pass; add telemetry
without explicit operator approval. The secrets rule is *enforced*, not just advised:
`.claude/hooks/secrets-guard.py` (a PreToolUse hook) blocks any Write/Edit/commit
carrying real key material or staging a `.env` file.

## Release gates (stop for approval at each ⏸)

1. ⏸ **Product brief** → `docs/product-brief.md`
2. ⏸ **Release charter** → `docs/release-charter.md`
3. ⏸ **Architecture** → `docs/adr/0001-local-first-proof-receipt-architecture.md`
4. **Skeleton** — CLI/backend/frontend start, health endpoint, README quickstart, tests pass
5. **Vertical slice** — sample dataset → run → leaderboard → receipt export (+ Playwright)
6. **Provider integration** — Ollama + OpenAI-compatible; mock tests pass keyless; provider tests skip without creds; no keys logged
7. **Ship candidate** — docs, release notes, demo script, screenshots, sample receipts, clean install, clean worktree

## UX north star

> A calm instrument panel for proving AI work, not a noisy dashboard for watching AI theater.

Precise, calm, confident, technical-but-humane, premium, readable, private,
evidence-first. Core objects: Project · Proof Brief · Dataset · Candidate · Proof Run ·
Leaderboard · Failure Case · Proof Receipt. Detailed standards in `docs/ux/` and
`docs/claude-context-and-ux-addendum.md`.

## After each session

Append a `docs/worklog/` entry: Summary · Verification (commands/screenshots/tests) ·
Product impact · Risks · Next recommended step.
