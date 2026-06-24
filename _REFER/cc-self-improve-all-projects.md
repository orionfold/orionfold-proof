# Claude Code self-improvement — Orionfold cross-project handoff

> **Living doc.** A portable playbook for running a Claude Code self-improvement pass on
> any Orionfold project. First authored from the `orionfold-proof` pass on 2026-06-22.
> Update the **What worked / didn't** and **Changelog** sections after each project's pass.
> Copy this file into each repo's `_REFER/` (or symlink) so every project starts here.

---

## 1. Operator ↔ Claude Code workflow (read first)

This section is for the **operator** (the human). Everything below it is the agent-facing
playbook. Your mindset: you're the **captain / director**, not the diff-reviewer. Leverage
lives at the *ends* of a task — sharpening intent before, holding the quality bar after —
not babysitting the middle. Spend attention on the **spec** and the **verification**; let
Claude Code (CC) own the implementation.

### The loop: ideation → ship
1. **Ideate** — rough intent. Don't over-specify yet.
2. **Clarify / brainstorm** — for anything non-trivial, let CC interview you
   (`AskUserQuestion` / the brainstorming skill). Answer the hard questions; skip the
   obvious. This is where ambiguity dies cheaply.
3. **Spec** — depth = *blast radius × uncertainty*: one-liner → no plan; single-file/clear
   → plan mode (the plan *is* the spec); multi-file/cross-layer/unfamiliar → a ~1-page
   written spec. Approve it via plan mode → ExitPlanMode. A spec is enough when it names
   files/interfaces, fences out-of-scope, sequences a vertical slice, and ends with an
   end-to-end check — stop there.
   - **Ceremony gate:** the superpowers `brainstorming` / `writing-plans` /
     `executing-plans` skills auto-trigger and default to a heavy plan-file workflow. CC is
     instructed (in CLAUDE.md, which outranks skills) to **ask you via `AskUserQuestion`
     before engaging any of them** — full ceremony vs lightweight plan mode vs skip. You
     hold the gate; default is the lightest option that fits the tier. `test-driven-
     development`, `systematic-debugging`, and `verification-before-completion` are exempt
     (rigor, not ceremony). Replicate this note in each project's CLAUDE.md.
4. **Code** — let CC implement against the approved spec. Don't interrupt mid-flow for
   style nits; capture those for review.
5. **Verify** — demand **evidence** (test output, the command + result, a screenshot), not
   "done." UI changes → real-browser screenshot + diff against target.
6. **Review** — fresh-context review for genuine risk (`diff-reviewer` agent or
   `/code-review`); skip detailed review for low-risk diffs.
7. **Ship** — commit after checks pass; update README/notes; keep the worktree clean.

### When to `/clear`
- **Between unrelated tasks — always.** The #1 hygiene habit; a clean session + sharp
  prompt beats a long polluted one.
- When a unit of work (sub-project / feature) **completes**.
- After **two failed corrections** on the same issue → clear and re-prompt, sharper.
- **Before implementing a written spec** — fresh context lifts code quality on hard work.
- As a ceiling: hand off before **~40%** context fill (accuracy degrades past ~40–50%).
  Don't ride auto-compaction into the degraded zone; treat it as a safety net only.

### What `HANDOFF.md` is for
A curated, hand-maintained baton across cleared sessions — higher-signal than an
auto-summary. **Write/update it before you `/clear` mid-thread or end a session with work
in flight.** Keep it to: current goal · what's done · what's next · key file paths ·
decisions made · gotchas · how to verify/run. Drop stale content each update. **Read it at
session start** to rebuild context (or invoke the `context-refresh` skill).

### Effort & speed dials (operator)
- **Raise effort** (`high` → `xhigh` → `max`) for hard, multi-constraint, or long agentic
  work; **lower** it for simple, high-volume steps. If reasoning looks shallow, raise
  effort *before* re-prompting.
- **`/fast`** for iteration, drafting, low-risk loops; standard mode for final judgment.

### Delegation (operator)
- **Code in-session on Opus.** Delegate only reads / research / review to subagents.
- Say **"use subagents"** explicitly for parallel fan-out — Opus 4.8 under-spawns by
  default. Pin `model: opus` on any quality-sensitive delegated task.

### Safety actions (operator)
- Keep real keys in `.env.local` only; the secrets-guard hook backstops accidents.
- **Approve consciously** (don't auto-fly): `settings.json` / permission / hook changes,
  prod dependency adds, `git push` / releases, and migrations.

---

## 2. Origin instruction (the seed prompt)

Run this in a fresh session, in plan mode, at the repo root:

> Understand this project context. You are on a self-improvement (Claude Code) journey with
> the objective to make this project's development most aligned with current best practices
> so we generate the best code in the most token-optimal manner and ship at the fastest
> speed. First read `_REFER/claude-code-opus-4.8-best-practices-2026.md` (official best
> practices), then take aligning ideas from `_REFER/agentic-engineering-workflow.md`. Then
> do a thorough self-review of this project — its settings, skills, CLAUDE.md, memory,
> global settings, hooks, rules, agents, and anything else that impacts this project.
> Prepare a specification of improvements and summarize them for operator approval before
> implementing.

Prereqs in the repo's `_REFER/`: `claude-code-opus-4.8-best-practices-2026.md` and
`agentic-engineering-workflow.md` (copy from `orionfold-proof` if absent), plus this file.

## 3. The process that worked (repeat this)

1. **Read the two reference docs in full** (official first, practitioner second).
2. **Survey the whole steering surface** — delegate to a read-only Explore subagent to keep
   main context clean: root + subdir `CLAUDE.md`, `.claude/` (settings, rules, skills,
   agents, hooks, commands), memory store, `docs/` layout, and **global** `~/.claude/`
   (settings.json, plugins, personal skills, MCP servers).
3. **Diagnose against the doc's mechanisms** (§3–§9): is each rule in the *right* primitive?
   Deterministic guarantees in hooks/permissions, scoped knowledge in `rules/*.md`,
   sometimes-knowledge in skills, always-on facts in a lean CLAUDE.md.
4. **Write a spec, get approval** (plan mode → ExitPlanMode). Ask only the decisions that
   change the plan (use `AskUserQuestion` with concrete options).
5. **Implement smallest-first**, verify with evidence, log to the worklog.
6. Expect the **auto-mode classifier to gate `settings.json` writes** (granting
   permissions / registering hooks is self-modification) — that's correct; get explicit
   operator sign-off or turn auto-mode off for that step.

## 4. What was done for `orionfold-proof` (worked example)

The project was already strongly aligned; gaps were narrow (§4 enforcement + token tax).

**Project-scoped:**
- **Secrets-guard PreToolUse hook** (`.claude/hooks/secrets-guard.py`) — converts the
  advisory "never write/commit secrets" into a deterministic block on Write/Edit/Bash
  carrying real key material or staging `.env`. Conservative (matches secret *values*, not
  the words) so legitimate artifacts pass. *This is the highest-value, most product-specific
  change — adapt the patterns to each project's prime directive.*
- **Activated `.claude/settings.json`** — model pin, permission allow/ask/deny (hard-deny
  `.env` reads), hook wiring, and per-project disable of unused plugins.
- **CLAUDE.md edits** — point the secrets rule at the enforcing hook; fix a stale steering
  reference; add three workflow-policy bullets (below). Kept under the ~200-line budget.
- **Per-project inventory** (`docs/tech/global-skills-inventory.md`) of used vs unused
  global plugins/skills.

**Global (all projects):** disabled the `github` MCP plugin (prefer `gh` CLI); set
`alwaysThinkingEnabled: false` (let adaptive thinking route).

**Three workflow policies now encoded in CLAUDE.md** (operator-decided, portable):
- *Clearing > auto-compaction.* Operator-driven `/clear` + curated `HANDOFF.md` beats
  riding auto-compaction. Clear on task boundaries first; hard ceiling ≈40% of the window
  (accuracy degrades past ~40–50%).
- *Code in-session on Opus; delegate only reads/research/review to subagents.* If a
  delegated task is quality-sensitive, pin `model: opus` (or fork). Never author production
  code in a default (possibly Sonnet) subagent.
- *Spec depth = blast radius × uncertainty.* One-liner → no plan; single-file/clear → plan
  mode (the plan *is* the spec); multi-file/unfamiliar → a ~1-page self-contained spec, then
  `/clear` and implement fresh. A spec is "enough" when it names files/interfaces, fences
  out-of-scope, sequences a vertical slice, and ends with an end-to-end check.

## 5. Global skills & plugins — used vs disabled by `orionfold-proof`

Full per-project detail: `docs/tech/global-skills-inventory.md`. Cross-project summary:

**Plugins disabled globally (all projects):** `github` (prefer `gh` CLI — ~3× cheaper /
lower latency for PR/issue work).

**Plugins disabled for `orionfold-proof` only** (kept on globally for other projects):
`stripe`, `agent-sdk-dev`, `ralph-loop`, `session-report`. *Each project should disable the
plugins its stack/workflow never invokes.*

**Plugins this project keeps:** superpowers, code-review, feature-dev, frontend-design,
typescript-lsp, playwright, commit-commands, security-guidance, claude-md-management,
hookify, context7, skill-creator, code-simplifier, explanatory-output-style.

**Personal global skills (`~/.claude/skills/`, ~58):** there is **no per-project disable
toggle** — they tax every session's metadata (~80 tokens each). So per project we only
*inventory* used vs unused. Removal candidates seen from `orionfold-proof` (verify against
other projects before deleting): the `stagent-*` samples and end-user assistant agents
(`wealth-manager`, `travel-planner`, `marketing-strategist`, `shopping-assistant`,
`sales-researcher`, `customer-support-agent`, `data-analyst`, `financial-analyst`,
`health-fitness-coach`, `learning-coach`, `reading-list-manager`, `reddit-researcher`,
`researcher`, `content-creator`, `gmail-browser-ops`).

> **Multi-project removal rule:** a global skill is removable iff it appears in **no**
> project's "used" set. Aggregate every project's inventory before deleting. *Global skill
> removal is intentionally out of scope for a single project's pass.*

## 6. Generalized best practices (portable across projects)

Distilled from the two reference docs + this pass. Apply these to any Orionfold repo:

1. **Right primitive for each instruction.** Settings = law; hooks = guarantees; rules =
   scoped knowledge (`paths:` globs, lazy-loaded); skills = sometimes-knowledge; CLAUDE.md
   = always-on facts; subagents = context isolation; commands = daily inner-loop. Don't put
   a deterministic rule in CLAUDE.md prose.
2. **Turn the prime directive into a hook.** Whatever the product must *never* do (leak
   secrets, mutate prod, break a schema), enforce it with a PreToolUse hook — advisory prose
   is forgotten mid-session; hooks are not.
3. **Keep CLAUDE.md lean (≤~200 lines).** Test every line: "would removing this cause a
   mistake?" A bloated file drowns the rules that matter.
4. **Path-scope subtree conventions** with `.claude/rules/*.md` instead of subdir
   CLAUDE.md files — lazy-loaded, zero cost until a matching file is touched.
5. **Skill descriptions are triggers, not summaries** — third person, what + when, slightly
   pushy (models under-trigger). Body ≤ ~500 lines; add a Gotchas section over time.
6. **Right-tier subagent models** — cheap (Sonnet) for read-only investigation, Opus for
   review/security/anything quality-sensitive. Subagents isolate context; they don't write
   your production code.
7. **Cut always-on token tax** — disable plugins a project never uses; prefer CLI tools
   (`gh`, cloud CLIs) over MCP servers where benchmarked cheaper; inventory personal skills
   for a global cull.
8. **Let adaptive thinking + effort route** — don't force always-on thinking on Opus 4.8;
   raise *effort* (not prompt verbosity) when reasoning looks shallow; `/fast` for iteration.
9. **Verify with evidence, not assertion** — every task ends with a runnable check; show the
   output. Reserve fresh-context review (diff-reviewer agent / `/code-review`) for real risk.
10. **Manage the session** — `/clear` between unrelated tasks; explicit handoff over
    auto-compaction; after two failed corrections, clear and re-prompt.

## 7. What worked / what didn't (living — append per project)

### orionfold-proof — 2026-06-22
- **Worked:** project was already well-structured, so the pass was surgical (hook + settings
  + 3 doc edits). The conservative secrets-guard hit 5/5 test cases with no false positives.
  Delegating the config survey to an Explore subagent kept main context lean.
- **Friction:** the auto-mode classifier blocked the first `settings.json` write (expected —
  self-modification). Resolved by operator sign-off / auto-mode off.
- **Open:** personal global skills can't be per-project disabled — their token tax persists
  until a multi-project removal pass. Hook only registers on session restart.

### orionfold/website — 2026-06-24
- **Worked:** same surgical shape as proof — the repo was already well-aligned (43-line lean CLAUDE.md,
  46 memories, 6 solid skills, mirrored AGENTS.md/CODEX-CC.md parity, an inline HANDOFF-prune hook), so the
  pass was a single high-value enforcement add: a `publish-guard.py` PreToolUse hook adapting proof's
  secrets-guard. Adapted for this PUBLIC commerce repo by (a) adding Stripe/Supabase key signatures
  (`sk_`/`rk_`/`whsec_`/`sbp_`) and (b) extending `check_bash()` to block `git add`/`commit` of local-only
  paths — turning the CLAUDE.md "sweep before push" prose into enforcement (Codex had leaked local-only files
  before). Hit 17/17 unit cases (9 blocks, 8 allows) with **zero false positives**. Project `settings.json`
  gained a `.env` read-deny + disabled `agent-sdk-dev`/`ralph-loop`/`session-report` (kept `stripe` — core stack).
  Every touched path is git-ignored, so the pass wrote nothing public.
- **Friction:** orionfold-proof's `settings.json` uses a top-level `"//"` comment key — the website's settings
  schema **rejects** unrecognized top-level fields, so the first edit bounced. Fix: drop the `"//"` key; put the
  rationale in the hook's docstring instead. (Don't copy proof's commented settings header verbatim into repos
  with strict schema validation.)
- **Open:** the PreToolUse hook only registers on the next session start (same as proof). The unit test proves
  correctness now; the guard goes live next session. Per-project plugin disable is confirmed supported and works.

## 8. Changelog (living)

- **2026-06-24** — `orionfold/website` pass: added `publish-guard.py` (secrets + local-only-commit block),
  project `settings.json` (.env deny + 3 plugin disables, kept stripe), one CLAUDE.md guardrail line pointing at
  the hook (mirrored to AGENTS.md, parity green). Copied the 3 reference docs into a local-only `_REFER/` here.
  No global or public changes. Recorded the `"//"`-comment schema-rejection gotcha for strict-schema repos.
- **2026-06-22** — Doc created from the `orionfold-proof` pass. Global changes applied:
  `github` plugin off, `alwaysThinkingEnabled` off. Established the per-project inventory +
  multi-project-removal rule for personal global skills.
- **2026-06-22** — Added §1 *Operator ↔ Claude Code workflow* (operator-facing: the
  ideation→ship loop, when to `/clear`, what `HANDOFF.md` holds, effort/speed dials,
  delegation, safety actions); renumbered subsequent sections.
- **2026-06-22** — Superpowers kept active but **gated**: CLAUDE.md now instructs CC to ask
  the operator (`AskUserQuestion`) before engaging `brainstorming`/`writing-plans`/
  `executing-plans` ceremony; TDD/systematic-debugging/verification exempt. Resolves the
  conflict where the heavy plan-file workflow auto-triggered on every non-trivial task.
