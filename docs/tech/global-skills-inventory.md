# Global skills & plugins inventory — orionfold-proof

Purpose: record which **global** Claude Code skills/plugins this project actually uses,
so you can reconcile across projects and run a later multi-project pass to remove globally
redundant skills (i.e., skills no project uses). Created during the 2026-06-22
self-improvement session.

**Method & caveats.** This is a *relevance assessment* against this project's stack
(Python/uv/FastAPI backend + Vite/React/TS frontend, local-first, security-sensitive) and
its operator-led workflow — not invocation telemetry. Two mechanism facts shape scope:
- **Plugins** can be toggled per-project via `enabledPlugins` in `.claude/settings.json`.
  This project disables the clearly-unused ones (see below).
- **Personal global skills** (`~/.claude/skills/`, ~58) have **no supported per-project
  disable**. They load metadata into every session regardless. So they can only be
  *inventoried* here; actual removal is the future global multi-project pass — out of
  scope for this session. **No global skills were deleted.**

---

## Plugins (global `~/.claude/settings.json`)

| Plugin | Status | Rationale |
| --- | --- | --- |
| superpowers | **Used** | brainstorming, writing-plans, TDD, systematic-debugging — core workflow |
| code-review | **Used** | `/code-review` in the operator loop |
| feature-dev | **Used** | code-architect / code-explorer agents for feature work |
| frontend-design | **Used** | UI design for `web/` |
| typescript-lsp | **Used** | `web/` is TypeScript |
| playwright | **Used** | e2e + visual verification |
| commit-commands | **Used** | commit / PR flow |
| security-guidance | **Used** | security-sensitive product (no leaked keys) |
| claude-md-management | **Used** | CLAUDE.md upkeep |
| hookify | **Used** | hook authoring (now in use: secrets-guard) |
| context7 | **Used** | current-docs-check / library docs |
| skill-creator | **Used** | skill authoring |
| code-simplifier | **Used (low-confidence)** | `/simplify`; overlaps with code-review |
| explanatory-output-style | **Used** | active output style this session |
| github | **Disabled globally (change 3)** | prefer `gh` CLI — ~3× cheaper / lower latency than the MCP for PR/issue work |
| stripe | **Disabled for this project only (change 1)** | payments — irrelevant to this product; kept ON globally for other projects |
| agent-sdk-dev | **Disabled for this project only (change 1)** | SDK-app builder — irrelevant here; kept ON globally |
| ralph-loop | **Disabled for this project only (change 4)** | long-running loop — unused here; kept ON globally |
| session-report | **Disabled for this project only (change 4)** | usage reporting — unused here; kept ON globally |
| supabase, vercel, rust-analyzer-lsp | Off globally (pre-existing) | not part of this stack |

---

## Personal global skills (`~/.claude/skills/`, ~58)

### Relevant to this project (keep available)
Engineering / planning / docs / UI skills this project plausibly invokes:

`autoplan` · `careful` · `investigate` · `plan-eng-review` · `plan-design-review` ·
`qa` · `qa-only` · `review` · `retro` · `ship` · `sweep` · `technical-writer` ·
`design-review` · `design-consultation` · `design-shotgun` · `devops-engineer` ·
`document-release` · `document-writer` · `project-manager` · `general` · `browse` ·
`connect-chrome` · `setup-browser-cookies` · `benchmark` · `guard` · `freeze` ·
`unfreeze` · `land-and-deploy` · `setup-deploy`

> Note: several overlap with this project's own `.claude/skills/` (which take precedence
> and are higher-signal here): `browser-visual-verification` (vs `browse`),
> `ux-polish-review` (vs `design-review`), `release-quality-gate` (vs `ship`/`qa`),
> `security-secrets-review`, `receipt-quality-review`. Prefer the project skills; the
> global ones are general fallbacks.

### Not used by this project (removal candidates for the multi-project pass)
These read as belonging to other products/personal use (a "stagent" suite, end-user
assistant agents). Confirm no other project uses them before removing globally:

`content-creator` · `customer-support-agent` · `data-analyst` · `financial-analyst` ·
`health-fitness-coach` · `learning-coach` · `marketing-strategist` ·
`operations-coordinator` · `reading-list-manager` · `reddit-researcher` · `researcher` ·
`sales-researcher` · `shopping-assistant` · `travel-planner` · `wealth-manager` ·
`gmail-browser-ops` · `stagent-sample-launch-copy-chief` · `stagent-sample-portfolio-coach` ·
`codex` · `cso` · `office-hours` · `learn` · `gstack-upgrade` · `upgrade-assistant`

(The last few — `codex`, `gstack-upgrade`, `upgrade-assistant`, `office-hours`, `learn`,
`cso` — are uncertain; verify intent before removing.)

---

## Reconciliation guidance (future multi-project pass)
1. Repeat this inventory per project (one "used" set each).
2. A global skill removable iff it appears in **no** project's "used" set.
3. Each removed personal skill reclaims ~80 tokens of always-on system-prompt metadata
   across every session in every project — the main token-tax lever, since personal
   skills cannot be scoped per-project.
4. Re-confirm before deleting: a skill's `description` is its trigger; losing it silently
   disables a capability rather than erroring.
