# 2026-06-20 — Leaderboard recommendation fix (Finding 1 + Finding 3)

## Summary

Fixed the highest-priority live-review finding: **the leaderboard recommended a candidate that
produced nothing.** An errored candidate returns a graceful `ProviderResult` reporting `0 ms /
$0.00`, so at a 0%-pass tie it won the lowest-latency-then-lowest-cost tiebreak and was crowned
`recommended` **unconditionally** — verified twice live (a `claude-fable-5` that wasn't available,
then an `ollama:llama3.2` that returned HTTP 404 on every example). This defeated the product's
"what to trust" thesis at the exact moment it matters.

The fix lands in three layers because the bug compounded across all three:

1. **Ranking** (`proof/leaderboard.py`) — added an `error_count` aggregate and a sort key
   `(all_errored, -pass_rate, -avg_score, avg_latency_ms, total_estimated_cost_usd)` where
   `all_errored = total > 0 and error_count == total`. A fully-errored candidate now sorts strictly
   **last**, and any candidate that produced output outranks it even at a 0.00 avg-score tie (the
   `-avg_score` term also breaks pass-rate ties on quality before latency/cost).
2. **Recommend gate** — `entries[0].recommended = True` **only when `pass_count > 0`**; otherwise no
   entry is crowned.
3. **Receipt + UI** — when nobody passes, the receipt verdict is **"No clear winner"** with a
   threshold-bearing reason, and the cockpit shows a calm **neutral** (non-accent) no-winner card
   instead of badging `leaderboard[0]`. Fully-errored rows are annotated **"errored, no output"** in
   Markdown, HTML, and the Leaderboard component. The receipt schema gains the additive `error_count`
   field → **`RECEIPT_VERSION` 3 → 4** (`config_hash` and run provenance byte-for-byte unchanged).

Bundled **Finding 3**: removed `claude-fable-5` from the catalog (not generally available; it was
what made the cost-vs-quality "Frontier" arm resolve to an unavailable model). `claude-opus-4-8` is
now the sole frontier claude model, flagged `latest: true`; the anthropic default
(`claude-haiku-4-5`) is unchanged, drift-guard green.

Built brainstorm → spec → plan → subagent-driven execution (5 TDD tasks; fresh implementer +
two-stage review per task; one Important fix loop on Task 2; an Opus whole-branch review). Commits
on `main` (all local — no remote): `5b899c6` (ranking + gate) · `bbb3d21` (receipt no-winner) ·
`4145b66` (test hardening) · `b56dc38` (catalog) · `45c7772` (frontend) · `67ee30c` (samples) ·
`0c0de7e` (pricing parity, from the final review).

## Verification

- `uv run pytest -q` → **157 passed**; `uv run ruff check src tests` → clean.
- `pnpm --dir web test` → **46 passed**; `pnpm --dir web build` (tsc + vite) → clean.
- Playwright e2e (rebuilt embed) → **4/4**.
- TDD throughout (RED→GREEN per task). Per-task reviews all Spec✅/Approved. **Task 2 fix loop:** the
  review caught a *vacuous* no-⭐ test (the fixture left `recommended=False` by default, so the
  assertion proved nothing); fixed (`4145b66`) by driving the test through real `build_leaderboard`
  and adding a positive control proving the star appears for a real winner — re-review Spec✅/0 issues.
- **Receipt quality review** (controller) — generated an ad-hoc all-fail receipt: verdict
  "No clear winner" + threshold "0.80"; a ran-but-failed Haiku (avg 0.08) ranked **above** a fully-
  errored Llama (3/3 errors); "errored, no output" annotation present; HTML self-contained (0
  external refs); **no secrets** in MD/HTML/JSON or the committed samples.
- **Live browser check** (port 8799, own PID, mock_bad-only run to force no-winner): the no-winner
  card renders **neutral** (panel colors, no accent, no badge), the leaderboard shows no Recommended
  row, and failure cases distinguish an **error** (red `RuntimeError`) from a **low score** (yellow
  "Fail · score …"). The catalog change is live — the Anthropic row shows "Claude Opus 4.8 ★" and no
  Fable 5. Server stopped; the sibling checkout's tab/processes were left untouched.
- **Final whole-branch review** (Opus, `a1ff6c7..67ee30c`): **Ready to merge with fixes** — all
  binding constraints verified (provenance untouched, `RECEIPT_VERSION 4`, ranking + recommend-gate
  exact, neutral no-winner across MD/HTML/component, Tailwind v4 shorthand, catalog drift-guard
  green, no secrets); consumer-impact analysis clean (no code still treats `leaderboard[0]` as the
  winner; the `error_count` default is deserialization-safe). One finding gated and fixed: a stale
  `claude-fable-5` entry left in `pricing.py` (a file documented as kept in step with the catalog) →
  removed (`0c0de7e`).

## Product impact

This restores the integrity of the central promise — the leaderboard is the verdict, so it must
never crown a model that produced nothing. The product now tells the honest truth in three voices
that agree (cockpit, and all three receipt formats): when an option errors it ranks last and is
labeled "errored, no output"; when nothing clears the rubric there is a calm "No clear winner"
state instead of a false badge. A consultant handing a client this receipt can trust that a ⭐ means
something passed.

## Risks

- **Similarity rubric (Finding 2) still open** — the v0 string-similarity rubric fails a correct-but-
  reformatted summary (a clean Markdown table scored 0.12). Deliberately out of scope here; needs its
  own brainstorm (LLM-as-judge / semantic rubric, charter "optional, later").
- **Minors deferred** (final review, non-blocking): a general `prices ⊆ catalog` drift-guard test was
  *not* added — `pricing.py` intentionally keeps legacy/test ids and OpenRouter uses a different id
  format, so a naive guard would false-fail; revisit if a non-fragile shape emerges. Also: `winnerOf`'s
  redundant `?? undefined`; no dedicated HTML test for the errored-row annotation (MD is tested; the
  `_failures_label` helper is shared); `_all_errored` defined per-call.
- **No git remote** — all `main` commits remain local only (longstanding; not pushed without an ask).

## Next recommended step

- **Finding 2 — similarity-rubric weakness.** Brainstorm an LLM-as-judge / semantic rubric (or an
  interim threshold/format-sensitivity documentation pass). This is the last of the three live-review
  findings.
- Then **#6 prompt-variant candidates** — same model, different system prompt; the next candidate
  axis, composes with the picker + recipes. Still text-in/text-out, no new provider machinery.
