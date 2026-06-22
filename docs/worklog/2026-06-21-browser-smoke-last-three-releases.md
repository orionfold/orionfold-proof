# Worklog — 2026-06-21 · Browser smoke e2e (last three releases)

## Summary

Operator-requested **browser smoke e2e** of the three most recent feature releases, driven
through **Claude-in-Chrome** against a fresh keyless install. Rebuilt the embedded cockpit
(`bash scripts/build.sh`), started `orionfold up` on a provably-free port (**8799**, sibling
checkout holds 8787/8790/51xx) with a throwaway DB (`/tmp/orionfold-smoke.db`), and exercised
each feature live in a real browser. **No code change — verification only. No issues found.**

## What was smoke-tested (all PASS)

1. **Scoring-section design polish** (frontend) —
   - The four scoring methods (Auto / Keypoint / Similarity / LLM judge) render in **one
     responsive row** with cost chips pinned to the bottom and aligned (`Free / Free / Free /
     $ per run · slower`); the single helper line replaces the old split headers. ✓
   - Selecting **LLM judge** reveals the **single-row numbered stepper** ① Run on (Local/Hosted)
     → ② Optimize (Cheapest/Balanced/Best) → ③ Judge model (Mock judge — keyless, deterministic),
     with filled-accent ①②③ badges and **hairline connectors (not arrows)**, all inline. Zoomed
     screenshot confirmed the styling matches the top `StageStepper`. ✓

2. **#6 Prompt-variant candidates** —
   - `Compare by: Models | Prompts` toggle flips the panel; Prompts mode shows a **Prompt model**
     dropdown (Mock · good) + a **Prompt variants** editor pre-filled with **Baseline** (the
     starter prompt, drift-locked to server `TASK_SYSTEM_PROMPT`) and **Concise**, plus an
     **Add prompt** button. ✓
   - Leaderboard renders one row per variant (`mock_good#baseline`, `mock_good#concise`). ✓
   - JSON receipt is **v6** with a `prompt_variants: [{name, system_prompt}]` block; Markdown has
     a `## Prompt variants` section; HTML (200) renders it. Each leaderboard entry also carries its
     own `system_prompt`. `brief.decision_question` populated; `scored_by` = "Keypoint coverage". ✓

3. **Prompt-aware mocks** —
   - Keyless Prompts run produces a **real winner, not a tie**: **Baseline RECOMMENDED, 100%
     (5/5), avg 1.00** vs **Concise 0% (0/5), avg 0.48**. The brevity cue in "Concise" ("as few
     words as possible", strong tier) truncated output → dropped keypoints → score-based fails
     (0.50/0.50/0.50/0.25/0.67), not provider errors. ✓
   - **Byte-identity invariant intact:** a model-compare run (Mock · good vs Mock · bad) reproduces
     the bundled sample **`config_hash 467ddd96c9a5`** exactly, with `prompt_variants: []` and
     `system_prompt: None` on both rows. Mock · good 100% (5/5) RECOMMENDED; Mock · bad 0% (0/5),
     5 simulated provider failures. Prompt-aware mocks did **not** regress model-compare. ✓

## Verification

- Browser-driven via Claude-in-Chrome on `http://localhost:8799` (fresh DB). Console: **no errors
  or exceptions**.
- Receipts inspected via the export API (Markdown/HTML/JSON, the e2e-proven path): v6, prompt
  variants present, recommendation + verdict ("Ship") correct.
- **Secret scan** of the JSON receipt blob (sk-/api_key/Bearer/OPENAI/ANTHROPIC/password/secret):
  **none present**.
- Cleanup: server stopped, `/tmp/orionfold-smoke.{db,log}` removed, worktree clean.

## Product impact

Confirms the three releases stack into one coherent keyless decision path: the polished scoring
surface configures the run, the Compare-by toggle adds the prompt axis, and prompt-aware mocks make
that axis yield a provable winner — all before any API key, with the model-compare contract
untouched.

## Risks

None surfaced. Mocks remain a labeled brevity-cue **simulation**; real signal still needs a real
model (documented in the prompt-aware-mocks worklog).

## Follow-up — REAL-PAID route (operator-directed, same session)

After the keyless smoke, the operator authorized the **fully paid route** (real keys already in env:
OPENAI/GEMINI/OPENROUTER; ANTHROPIC unset) and asked for **real-world use cases, not mocks**. Ran two
live runs on the bundled dataset (~30 real calls, <$0.01 total) via Claude-in-Chrome, then the operator
said "stop test". No code changed.

**Run A — cross-provider, keypoint scoring** (GPT-5.4 nano vs Gemini Flash-Lite):
- Gemini RECOMMENDED 40% (2/5) avg 0.60, real latency 4576ms, real cost $0.00041; **verdict "Keep
  testing"** (honest caution on a weak winner). OpenAI **errored 5/5** → excluded from recommendation.

**Run B — cross-provider, REAL LLM judge** (Gemini Flash-Lite vs OpenRouter Llama 3.1 8B vs GPT-5.4
nano, graded by a real **Gemini** judge):
- Gemini RECOMMENDED **100% (5/5) avg 0.96**; OpenRouter Llama **ran** (real output) but judge-scored
  **0.26** (legit "weaker model" result); OpenAI errored. Cost line: candidate $0.00039 · **judge
  $0.00036** · total $0.00075 — judge cost captured separately, out of ranking. Verdict "Ship".

### Issues found (logged to HANDOFF for next session)

1. **🐞 BUG — `openai_compatible.py:56` sends `max_tokens`; GPT-5.x rejects it.** Real error:
   `HTTP 400 "Unsupported parameter: 'max_tokens' is not supported with this model. Use
   'max_completion_tokens' instead."` Blocks ALL OpenAI runs. OpenRouter/LM Studio (same class) accept
   `max_tokens` — verified OpenRouter Llama ran. Fix: per-profile `token_param` (TDD, no paid calls).
2. **UX gap — Hosted LLM-judge defaults to Claude Haiku · Anthropic**, errors when `ANTHROPIC_API_KEY`
   unset; judge dropdown doesn't signal missing keys (candidate picker does).
3. **Minor — raw provider error JSON shown verbatim** in failure cases + receipt. **No secret leak**
   (scanned receipts against actual env key values → none; boundary redaction holds). Consider truncating.

Environmental: OpenAI `429 insufficient_quota` in Run A — operator topped up billing (new key in
`.env.local`); independent of bug #1, which still blocks OpenAI until fixed.

### Product behavior confirmed under real providers (positive)

Real cost & latency capture · judge-cost separation · errored candidates excluded from recommendation ·
honest verdicts (Keep testing / Ship) · **no secret leakage** even with raw errors rendered.

## Next recommended step

**Fix Issue 1 (OpenAI `max_completion_tokens`) first** — confirmed bug blocking all OpenAI runs; TDD,
no paid calls to verify; then optionally re-run the real-paid smoke (billing topped up). Then triage
Issues 2–3. Prior backlog (non-blocking): catalog accuracy pass · cross-product models × prompts
(brainstorm first) · git remote + push.
