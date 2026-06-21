# Worklog — 2026-06-21 · Prompt-aware mocks

## Summary

Made the keyless mock providers **prompt-aware** so the #6 prompt-compare demo produces a real,
intuitive winner with **no API key** — instead of every variant tying because the mocks ignored
the system prompt. The mocks now deterministically shape their output by *instruction cues* in the
candidate's `system_prompt`: a brevity instruction ("as few words as possible", "concise",
"terse", …) truncates the output, dropping trailing content (and so trailing keypoints), exactly
as a real model that obeyed the instruction would.

Crucially, the model-compare path is **provably untouched**: when `system_prompt is None` (the
model-compare default), the shaping helper returns the *same string object* unmodified. So the
"100% (5/5)" contract, the sample receipts, and sample `config_hash 467ddd96c9a5` are byte-identical
— no regeneration needed.

Built brainstorm → spec → plan → **subagent-driven execution** (2 tasks, fresh implementer +
spec/quality review per task) → Opus whole-branch review. Committed directly to `main` (solo
convention; no remote).

## What landed (2 commits, `9e41927`, `f346053`)

- **`_shape_for_prompt(base, system_prompt)`** (`9e41927`, `src/orionfold/providers/mock.py`) — a
  pure helper that returns `base` verbatim when there is no system prompt or no recognized cue, and
  otherwise truncates to the first `max(1, ceil(b · word_count))` words. Verbosity budget `b`:
  strong cues (`as few words as possible`, `fewest`, `terse`, `one sentence`, `tl;dr`) → `0.4`;
  mild cues (`concise`, `brief`, `short`, `minimal`) → `0.6`; strongest wins when both present.
  Both `MockGoodProvider` and `MockBadProvider` route their base output through it; `mock_bad`'s
  simulated failure still raises *before* shaping (failure path invariant to the prompt). 9 unit
  tests (identity via `is base`, tier ordering, determinism, keypoint drop, mock_bad still errors).
- **Integration lock** (`f346053`, `tests/integration/test_proof_api.py`) — a keyless prompt-compare
  run on `mock_good` with Baseline vs Concise asserts `avg_score` Baseline **strictly greater than**
  Concise at the API boundary.

No receipt schema change, no `RECEIPT_VERSION` bump, no frontend change, no other provider touched.

## Verification

Controller-verified at close on HEAD `f346053`:
- `uv run pytest -q` → **223 passed** (1 pre-existing third-party StarletteDeprecationWarning).
- `uv run ruff check src tests` → clean.
- `pnpm --dir web test` → **83 passed** (22 files); `pnpm --dir web build` → clean.
- `bash scripts/build.sh && pnpm --dir web e2e` → **6/6 Playwright specs** (incl. the keyless
  prompt-compare spec; embed rebuilt first).
- **`config_hash 467ddd96c9a5` still present** in the sample receipt — model-compare byte-identity
  confirmed; no sample regeneration needed.
- **Concrete keyless demo** (shipped starter prompts, `investment-memo-summarization`):
  **Baseline `avg_score=1.000` (recommended)** vs **Concise `avg_score=0.555`** — a genuine winner.
- TDD throughout (RED→GREEN per task). Both per-task reviews PASS (Spec ✅ / Quality Approved).
  **Final whole-branch review (Opus, `73ade79..f346053`): Ready to merge = YES, 0 Critical /
  0 Important** — every load-bearing invariant verified *empirically* (object-identity verbatim
  returns, determinism, mock_bad failure invariance, all 9 cue mappings, single-word/empty edges).

## Product impact

The keyless first-run now *demonstrates the decision*, not just the plumbing. A new user with no
API key can switch `Compare by: Prompts`, run the bundled demo, and see one wording win on the
leaderboard with the receipt recording exactly why — which is the product's whole thesis
("prove which AI is worth trusting") working before any provider is configured.

## Risks

- **The mock is a deliberately small *simulation*, not a model.** It is sensitive only to a finite
  brevity-cue vocabulary; a brevity instruction phrased outside that list falls through to "no
  change". Documented in the spec; the cue lists are the one obvious place to extend. Providers stay
  labeled "Mock ·…" so the simulation is never mistaken for a real result.
- **Real signal still requires a real model.** On a configured provider the variation comes from the
  model itself; the mock variation exists to make the *keyless demo* honest-but-illustrative.

## Next recommended step

Remaining non-blocking options from the #6 handoff are untouched: **catalog price/source accuracy
pass**, **cross-product (models × prompts)** only if a real need appears, and **set up a git remote
+ push** (all `main` commits remain local). Workflows/RAG remain post-v0.
