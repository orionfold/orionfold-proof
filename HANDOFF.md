# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-22 · **Orionfold design-system skin APPLIED** (cyan/green split + Geist +
status tokens + skip link). Web-only, verified in both themes. v0 remains real-world-verified
(Phases A + B done previously). Remaining work is the non-blocking backlog + one operator chore._

## ✅ THIS SESSION — Orionfold DS skin apply (web/ only)
> Evidence: `docs/worklog/2026-06-22-orionfold-skin-apply.md`. Write-back to the DS handshake tree:
> `orionfold-design-system/apply/proof/aligned/2026-06-22-021521-log.md` +
> `…/roadmap/2026-06-22-021521-log.md`.

Applied change package `apply/proof/change/2026-06-21-234241` (DS `36d1c48`):
- **Token swap** — single green `--color-accent` `#34d399` → Orionfold **cyan** `#14c8c0` (the one
  action colour); **new** status-green `--color-ok` carries PASS/verified; new `--color-warn` /
  `--color-danger` / `-soft`s; cyan focus ring; radius + Geist `--font-*` tokens. Drop-in to
  `web/src/styles/index.css` (token NAMES unchanged → utilities re-resolved for free). Dark stays the
  `@theme` default.
- **Geist + Geist Mono** loaded in `web/index.html`; body→`--font-sans`, `code`/`.mono`→`--font-mono`.
- **Accent/status split at call sites** — `App.tsx` "Connected" dot `--color-accent`→`--color-ok`
  (the core split); de-literalled `badges.tsx` (neutral squared provider tags; error→danger,
  fail→warn); rose-300→`--color-danger` sweep across 6 files; verdict metrics `tabular-nums`.
- **Skip-to-content link** added (first focusable, cyan chip → `#main-content` on the workspace main).
- **Tidy** — shared `web/src/features/proof/formStyles.ts` `inputCls`.
- **One deliberate deviation (logged as Pushback):** `StatusBadge fail` → `--color-warn` (amber), not
  danger — preserves the product's hard-error vs graded-miss severity split; aligns with the
  component-map's two-token failure-case treatment.

**Verification:** `pnpm --dir web test` 84/84 · `tsc --noEmit` clean · `pnpm --dir web build` clean ·
`bash scripts/build.sh` (embed rebuilt; Geist + cyan/green tokens confirmed) · `pnpm --dir web e2e`
6/6 · real-browser visual grade in **both themes** (cyan verdict, neutral provider tags, amber/red
status, green engine dot, cyan skip chip; AA legible). No backend change · no receipt-schema change ·
`RECEIPT_VERSION` still 6 · prompt-aware-mocks / #6 / standing invariants untouched.

## ⚠️ OPERATOR ACTION (env, NOT code) — stale shell `OPENAI_API_KEY` shadows `.env.local`
Key precedence is **system env first, then `.env.local`** (intentional 12-factor design in
`config/keys.py`). A **stale** exported `OPENAI_API_KEY` (suffix `_0MA`) shadowed the good topped-up
key in `.env.local` (suffix `qVYA`). **Fix: clear/refresh the stale `OPENAI_API_KEY` in your shell
profile** (or unset it and rely on `.env.local`). One-time, no code.

## NEXT — pick up the non-blocking v0 backlog
0. **(Operator) Refresh the stale shell `OPENAI_API_KEY`** (box above).
1. **Catalog price/source accuracy pass** — verify list prices + context windows vs current provider
   docs (use `current-docs-check`). Non-blocking.
2. **Cross-product models×prompts** — compare N models × M prompts in one run. **Brainstorm FIRST**
   (`superpowers:brainstorming`) — new feature surface (#6 today is one-model × N-prompts).
3. **git remote + push** — no remote configured; `main` holds prior committed work unpushed.
4. **DS-skin follow-ups (optional polish, from the roadmap write-back):** cyan `m-fill` leaderboard
   score bars (S); shared token-driven badge/chip kit folding toggle/radio selected states (S);
   deepen per-figure mono "receipt voice"; categorical dataset/domain tag; receipt proof-seal stamp.

Workflows/RAG remain post-v0. Any creative/feature work → **brainstorm FIRST**.

## Key invariants to NOT regress
- **The accent/status split is now load-bearing:** cyan `--color-accent` = the ONLY interactive
  colour (buttons, focus, links, score bars, active states, brand seal, verdict surface); green
  `--color-ok` = PASS/verified status ONLY; `--color-danger`/`--color-warn` = error/fail status.
  **Never let the Run button and a PASS badge share a hue.** Consume only the `--color-*` semantic
  layer (never raw hex in a component). Always ship light + dark + WCAG AA; dark is the `@theme`
  default (load-bearing). Provider/privacy tags stay neutral, squared, non-interactive.
- **Prompt-aware mocks:** `_shape_for_prompt` returns the SAME `base` string object on the
  `system_prompt is None` AND cue-less (`budget>=1.0`) paths → model-compare byte-identical (sample
  `config_hash 467ddd96c9a5`; a unit test asserts `is base`); pure/deterministic; `mock_bad` raises on
  `_stable_int(input_text)%5==0` BEFORE shaping; cue tiers exact (strong 0.4 / mild 0.6 / none 1.0).
- **#6 + standing:** `config_hash` includes `system_prompt` only when non-None; `RECEIPT_VERSION` 6;
  variant id `{model_id}#{slug}`; both run endpoints route through `_resolve_candidates`/
  `build_candidates`; meaning-aware scoring (keypoint coverage; MockJudge keyless; judge cost stays in
  `judge_cost_usd`, never in ranking); leaderboard never recommends a 0-pass/all-errored candidate;
  keyless mock default; `/api/*` leak NO secrets; `.env.local` 0o600, never echoed.

## Paste prompt for the next session
```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001/0002/0003,
latest worklogs incl. 2026-06-22-orionfold-skin-apply).

RECENT WORK (committed to main unless noted; no git remote configured):
- (latest) ORIONFOLD DS SKIN APPLY (web/ only) — cyan/green accent-status split, Geist typography,
  token-driven badges, skip-to-content link. Verified: web test 84/84, tsc clean, build clean, e2e
  6/6, both-theme browser visual grade. No backend/receipt-schema change. Evidence:
  docs/worklog/2026-06-22-orionfold-skin-apply.md; DS write-back under
  orionfold-design-system/apply/proof/{aligned,roadmap}/2026-06-22-021521-log.md.
- (prior) PHASE A OpenAI max_tokens→max_completion_tokens fix; PHASE B real-world paid browser smoke;
  prompt-aware mocks; #6 prompt-variant candidates (RECEIPT_VERSION 6); scoring polish; meaning-aware
  scoring; decision recipes (#5); model picker (#4); catalog (#1).

START HERE — v0 real-world-verified + DS-skinned. Remaining is non-blocking: (0) operator: refresh
stale shell OPENAI_API_KEY; (1) catalog price/source pass (current-docs-check); (2) cross-product
models×prompts — BRAINSTORM FIRST; (3) git remote + push; (4) optional DS-skin polish (see roadmap
write-back). Workflows/RAG post-v0. Any creative/feature work → brainstorm FIRST.

Do NOT regress: the accent/status split (cyan=action, green=--color-ok=PASS, danger/warn=status;
semantic-token layer only; light+dark+AA; dark is @theme default; provider tags neutral/squared). Plus
the prompt-aware-mocks / #6 / standing invariants listed in HANDOFF.md.
```
