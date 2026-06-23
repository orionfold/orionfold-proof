# 2026-06-22 — Claude Code self-improvement pass (Opus 4.8 best-practices alignment)

## Summary

A meta/config session (no product code) to align the project's agentic-engineering setup
with `_REFER/claude-code-opus-4.8-best-practices-2026.md` and the practitioner ideas in
`_REFER/agentic-engineering-workflow.md`. Finding: the project was already strongly aligned
(path-scoped `rules/*.md`, trigger-shaped skill descriptions, right-tiered agent models,
lean 138-line CLAUDE.md). The real gaps were in §4 (harness-enforced behavior) and
always-on token tax. Spec: `~/.claude/plans/understand-this-project-context-calm-globe.md`.

## What changed

**Project (`orionfold-proof`):**
- **`.claude/hooks/secrets-guard.py`** (new) — PreToolUse hook converting CLAUDE.md's
  advisory "never write/commit secrets" into a deterministic guarantee. Blocks Write/Edit
  carrying real key material (provider prefixes, bearer tokens, high-entropy assignments
  to `*_KEY`/`*_SECRET`/`*_TOKEN`) and Bash that stages a `.env` file. Conservative by
  design — matches secret *values*, not the words — so receipts (config hash, model name,
  api_base URL), env-var refs, and placeholders pass clean.
- **`.claude/settings.json`** (new, activated from the example) — pins
  `model: claude-opus-4-8`; allow/ask/deny permission lists (hard-denies `.env` reads);
  wires the secrets-guard hook; disables four unused plugins **for this project only**
  (`stripe`, `agent-sdk-dev` = change 1; `ralph-loop`, `session-report` = change 4).
- **`CLAUDE.md`** — secrets "Never" line now references the enforcing hook; steering-table
  row fixed to point at `.claude/rules/providers.md` (real mechanism) instead of a
  non-existent subdir CLAUDE.md; Context-discipline section gained three operator-policy
  bullets (clear-vs-auto-compact, subagents-vs-in-session, spec-depth). ~153 lines (within
  budget).
- **`docs/tech/global-skills-inventory.md`** (new) — inventory of which global
  plugins/skills this project uses, for a future multi-project reconciliation pass.

**Global (`~/.claude/settings.json`, all projects):**
- `github` plugin → **off** (change 3) — prefer the `gh` CLI (~3× cheaper / lower latency
  than the MCP for PR/issue work).
- `alwaysThinkingEnabled` → **false** (change 2) — let Opus 4.8 adaptive thinking + effort
  route per turn instead of forcing thinking on trivial turns.
- `stripe` / `agent-sdk-dev` left **on** globally (disabled only at project scope, per the
  operator's "change 1 = this project only").

## Operator decisions (2026-06-22)
- Scope = project fixes + full global review.
- Guardrails = secrets-guard PreToolUse hook, **no** turn-blocking Stop gate (4.8
  self-verifies; the diff-reviewer agent + skills cover review).
- Change 1 (disable stripe/agent-sdk-dev) = this project only. Change 2 (adaptive
  thinking) + change 3 (prefer gh) = all projects. Change 4 (disable unused skills) =
  this project only; **no global skills deleted** — global removal deferred to a later
  multi-project pass.
- Three workflow questions answered and encoded in CLAUDE.md: explicit `/clear` +
  HANDOFF.md over auto-compaction (clear on task boundary, ≤~40% ceiling); code in-session
  on Opus, delegate only reads/research/review to subagents; spec depth = blast radius ×
  uncertainty, stop once a colleague could execute it + a pass/fail check exists.

## Verification
- secrets-guard: 5/5 cases correct — blocks Anthropic key + `git add .env.local` (exit 2);
  allows receipt JSON (config hash + api_base), env-var/placeholder assignments, and normal
  code (exit 0). Evidence captured in session.
- Both `settings.json` files validated as parseable JSON; global toggles confirmed
  (`github:false`, `alwaysThinkingEnabled:false`, `stripe:true` globally).
- No product source touched → no app-test regression risk; backend/Playwright suites not
  re-run (out of this session's blast radius).

## Product impact
Indirect: the product's "no leaked secrets into receipts" promise is now machine-enforced;
per-session token tax is lower (fewer plugins, no forced thinking, no github MCP); the
workflow stays fast (no blocking gates). Authored rules/skills/agents left intact.

## Risks
- The hook only registers after a session restart (config is read at startup) — confirm it
  fires live next session.
- Disabling the `github` MCP globally removes its richer review tools; mitigated by `gh`.
- secrets-guard patterns are conservative; if a real provider key format isn't covered, the
  `security-reviewer` agent / `security-secrets-review` skill remain the deeper backstop.

## Next recommended step
Restart the session so `.claude/settings.json` + the hook take effect, then do a live
hook smoke test. After that, return to the product backlog — likely **packaging ·
licensing · distribution** (brainstorm first), which then unblocks the queued git remote +
push. Separately, when other projects are similarly inventoried, run the multi-project
global-skills removal pass using `docs/tech/global-skills-inventory.md`.
