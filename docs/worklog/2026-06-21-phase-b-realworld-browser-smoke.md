# Worklog — 2026-06-21 · Phase B: comprehensive real-world browser smoke

> Operator chose "Run full Phase B now". Drove every built feature through a real server
> (`orionfold up` on free port 8811, fresh throwaway DB `/tmp/orionfold-phaseb.db`, freshly
> rebuilt embed) with **real provider keys** via Claude-in-Chrome + a few API runs for precise
> evidence. Result: **the OpenAI fix (Phase A) is confirmed end-to-end with real paid calls**, and
> **every Phase B checklist item passes**. One non-code environment gotcha surfaced (below).

## Headline: OpenAI `max_tokens` fix verified with real money

- First real cross-provider run errored on OpenAI with **`HTTP 401: Incorrect API key`** — NOT the
  old `max_tokens` 400. The request passed parameter validation (proving `max_completion_tokens` is
  accepted); it only failed on auth. **→ the code fix works.**
- Root cause of the 401 = an **environment gotcha** (see below). After resolving it, the real
  cross-provider run came back **0 errors**, OpenAI `gpt-5.4-nano` ran cleanly and was **Recommended**
  (2/5, avg 0.800), real cost `$0.00202`.
- The **OpenAI hosted judge** path (the other code path that sent `max_tokens`) also ran clean:
  0 errors, judge cost correctly separated (`candidate $0.00034 · judge $0.00017`).

## ⚠️ NEW FINDING (environment, NOT code) — stale shell key shadows `.env.local`

Key resolution precedence is **system env first, then `.env.local`** (intentional 12-factor design,
documented in `config/keys.py`). The shell exported a **stale** `OPENAI_API_KEY` (suffix `_0MA`) that
**shadowed** the topped-up key in `.env.local` (suffix `qVYA`) → a misleading "Incorrect API key" 401
on every OpenAI call until I relaunched with `env -u OPENAI_API_KEY` so `.env.local` resolved.

- **Not a bug** — precedence is by design. But it's a real operational trap: a stale exported key
  silently wins over the in-app/.env.local one with no UI signal (the provider just shows
  `available` because a key *is* present; only the call reveals it's the wrong one).
- **Action for operator:** clear/refresh the stale `OPENAI_API_KEY` in your shell profile (or unset
  it and rely on `.env.local`). Optional product consideration (defer): surface the *source* of a
  resolved key, or let `.env.local` override a shell key for the in-app credential flow. Low priority.

## Phase B feature checklist — all verified

- ✅ **Custom dataset import** — UI: selected **CSV**, pasted 3 rows, Preview parsed "3 examples", named
  & **froze** → "Phase B CSV smoke · 3 examples" listed. JSONL covered by e2e; Markdown toggle + hint render.
- ✅ **Model-compare, real cross-provider** — OpenAI + Gemini + OpenRouter in one run; **all succeed, 0
  errors**, real cost/latency. Leaderboard: Gemini 100% (REC) · OpenAI 60% · OpenRouter 0%.
- ✅ **Decision recipes (#5)** — "Cheapest model that still passes" pre-filled 3 low-cost candidates
  (Anthropic Haiku, OpenAI nano, Ollama local) **and** the question "What's the cheapest model that still passes my bar?".
- ✅ **Model picker / catalog (#1, #4)** — all providers, tiers/cost-classes (`$/$$/$$$`), `★ latest`,
  `+ custom` entries, and local providers (Ollama, LM Studio) shown. `/api/selection` = all 4 cloud keyed.
- ✅ **All 4 scoring methods** — cards present (Auto resolves to "Keypoint coverage" for this dataset);
  **LLM judge run live with a REAL Anthropic Haiku judge** (Run-on/Optimize/Judge stepper); Keypoint used
  in the cross-provider run. Similarity/heuristics covered by unit tests.
- ✅ **Prompt-variant compare (#6) on a REAL model** — Baseline vs a Vague prompt on `gpt-5.4-nano`:
  **real, differing results** (Vague 3/5 vs Baseline 2/5, not a tie), **receipt_version 6**,
  `prompt_variants` present in JSON, "Prompt variants" section in MD. 0 errors.
- ✅ **Streaming progress (ADR-0003)** — live `0/15 → 15/15` counter, "Now running … example N of 5",
  per-candidate progress bars filling candidate-major.
- ✅ **Leaderboard + recommendation + verdict** — ranking, Recommended badge, real cross-provider rows.
- ✅ **Failure-case browser** — per-candidate filter chips ("OpenAI · 2", "OpenRouter · 5"), Inspector
  shows Input / Expected / Output + score for the selected case.
- ✅ **Receipt export** — MD · HTML · JSON fetched; "Scored by LLM judge · claude-haiku-4-5", "Run cost"
  (candidate/judge/total), Config hash + reproducibility note, Rerun command. **Secret scan CLEAN**:
  6 real key values + key-shaped token patterns → **zero** matches in any format.
- ✅ **Candidates view + Receipts view** — Candidates lists all with Mock/Local/Cloud badges + pinned
  models; Receipts lists every past run (incl. the API runs) newest-first with winner, scored-by,
  config hash, timestamp, and per-format download.
- ✅ **Keyless regression guard** — model-compare mocks reproduce **`config_hash 467ddd96c9a5`** exactly
  (byte-identical); prompt-aware mocks **Baseline 1.000 (REC) vs Concise 0.483** (real keyless winner).

## Verification

- Real runs (paid): cross-provider model-compare; OpenAI hosted judge; live UI LLM-judge run (Anthropic
  Haiku); prompt-variant on a real model. Total real spend ≈ a few cents.
- Keyless: `config_hash 467ddd96c9a5` reproduced; Baseline>Concise; receipt secret scan clean.
- Phase A code unchanged this session (Phase B is verification-only). HEAD `9ffbb90`.
- Cleanup: server stopped, throwaway DB + temp receipts removed, browser tab closed, sibling checkout
  (port 4399/8787/8790 tabs & processes) left untouched.

## Product impact

v0 is real-world-proven end to end with live providers: the OpenAI arm (candidates **and** hosted
judge) works, the cross-provider "what to trust" decision produces honest verdicts with separated
judge cost, receipts export clean (no secrets), and the keyless demo path stays byte-identical.

## Risks / next

- **Operator action:** refresh the stale shell `OPENAI_API_KEY` (the `.env.local` key is good).
- Not exercised live (low risk, covered elsewhere): Markdown dataset paste (toggle renders; parser
  covered by tests), `+ custom` model entry (button renders), Similarity as a live real run (unit-tested),
  local Ollama/LM Studio generation (no backend running — catalog entries shown only).
- Backlog (unchanged, non-blocking): catalog price/source accuracy pass · cross-product models×prompts
  (brainstorm first) · git remote + push. Workflows/RAG remain post-v0.
