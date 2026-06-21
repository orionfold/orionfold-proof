# Worklog — 2026-06-21 · #6 Prompt-variant candidates

## Summary

Shipped **#6 prompt-variant candidates** — a new comparison axis that holds the model fixed and
varies the **system prompt**: "one model, N prompts" compared in a single run. It answers the
decision *"which wording of my instructions produces the most trustworthy output on my task?"*
Composes with the existing picker, recipes, and scoring methods; **no new provider machinery**.

The architectural seam: a system prompt is a field on `Candidate`, so a prompt variant is *just a
candidate*. The 2-D candidate-major matrix (`iter_matrix`), streaming progress, leaderboard,
scoring, and the failure browser all work unchanged. A `Compare by: Models | Prompts` toggle in
the cockpit selects the axis; in Prompts mode the run sends one model id + a list of named prompts,
which the server fans out into one candidate per prompt.

Built brainstorm → spec → plan → **subagent-driven execution** (12 tasks, fresh implementer +
two-stage review per task, then an Opus whole-branch review), followed by an operator-approved
cleanup pass. Committed directly to `main` (solo convention; no remote configured).

### What landed (14 commits, `41cc8e2..d411e71`)

- **`Candidate.system_prompt` + `PromptVariant`** (`c3d8d69`) — the seam; `system_prompt_for(candidate)`
  helper in `providers/http.py`; all four real providers (anthropic, openai_compatible, gemini,
  ollama) read it, falling back to the global `TASK_SYSTEM_PROMPT` when `None`. Mocks ignore it
  (stay deterministic).
- **`expand_prompt_variants`** (`e6275fa`) — fans one model-bearing candidate into one candidate per
  variant; id = `{model_id}#{slug}` (deduped `-2`/`-3`); `#` is distinct from the `:` model split so
  routing/parse are untouched.
- **`config_hash` conditional** (`405993c` + test-lock `31d55da`) — includes `system_prompt` only
  when non-None, so model-compare runs hash **byte-identical** (zero sample churn) while variants
  hash distinctly and reproduce. A same-id/different-prompt assertion locks the behavior (revert
  check proven).
- **`RunRequest.prompt_variants` + `_resolve_candidates`** (`cf19bf0`) — shared by both run endpoints;
  422 on not-exactly-one-model / fewer-than-two-variants / empty name or prompt; `UnknownCandidateError`
  still → 400; the global 422 input-stripping handler intact.
- **`LeaderboardEntry.system_prompt`** (`577842c`) — provenance carrier, populated from the candidate.
- **Receipt v6** (`69a6b8b`) — `RECEIPT_VERSION` 5→6; JSON `prompt_variants: [{name, system_prompt}]`
  (empty for model-compare); a "Prompt variants" section in Markdown + HTML, gated on non-empty and
  html-escaped; `_rerun_command` emits the honest prompt-variant POST shape (also fixed the old
  single-quote-JSON repro bug for the model-compare path); samples regenerated.
- **Frontend** — `api.ts` types (`cc4f333`); pure helpers (`bd8481d`, renamed to
  `promptVariantsHelpers.ts` in cleanup); `PromptVariants` editor (`a977079`); `Compare by` toggle
  wired into RunSetup + ProofCockpit (`e25f8d5`).
- **e2e** (`da64119`) — keyless prompt-compare flow: toggle → 2-variant editor on a mock → leaderboard
  rows "Baseline"/"Concise" → JSON receipt records 2 prompt_variants.
- **Docs** (`472b10e`) — CHANGELOG + a demo-script "compare prompts" tip.
- **Cleanup** (`d411e71`, operator-approved) — renamed the case-only filename pair
  `promptVariants.ts` → `promptVariantsHelpers.ts` (kills the case-insensitive-FS footgun; all 5
  importers updated, zero stale imports); added a drift-lock test pinning the Baseline starter prompt
  to the server `TASK_SYSTEM_PROMPT` verbatim.

## Verification

Controller-verified at close on HEAD `d411e71`:
- `uv run pytest -q` → **213 passed** (1 pre-existing third-party StarletteDeprecationWarning from
  `fastapi/testclient`, not introduced here).
- `uv run ruff check src tests` → clean.
- `pnpm --dir web test` (vitest) → **83 passed** across 22 files.
- `pnpm --dir web build` (tsc + vite) → clean.
- `bash scripts/build.sh && pnpm --dir web e2e` → **6/6 Playwright specs** (incl. the new keyless
  prompt-compare spec; embed rebuilt first).
- TDD throughout (RED→GREEN per task). Per-task reviews all Spec✅/Approved; one fix loop (Task 3:
  the distinguishes-variants test passed on differing ids, not on system_prompt → strengthened with a
  same-id assertion, revert-check proven). **Final whole-branch review (Opus, `41cc8e2..472b10e`):
  Ready to merge = YES, 0 Critical / 0 Important**; all rolled-up Minors triaged defer; both plan
  deviations (remove-disable `<=1`, e2e JSON-receipt fallback) endorsed.

## Product impact

The product thesis extends from "which model do I trust?" to "which *instructions* do I trust?" A
consultant can now hold the model fixed and prove which wording of their system prompt produces the
most trustworthy output on their own dataset — and the receipt records the exact prompt of each
variant, so the decision is provable and client-shareable. It composes with recipes (#5) and the
model picker (#4): same leaderboard, same receipt, a new axis.

## Risks

- **Keyless prompt-compare on a mock is a plumbing demo, not a score-differentiator** — mocks ignore
  the system prompt by design, so all variants tie. The real signal appears on a configured model.
  This is a property of the feature, documented; not a coverage gap.
- **Receipt `prompt_variants` (from leaderboard) and `_rerun_command` (from `run.candidates`) read
  from two sources** that agree 1:1 today; a future leaderboard filter/reorder could desync them
  (non-blocking, noted by the final review).
- **Model-compare HTML now emits a trailing-whitespace blank line** before `<h2>Repro>` when there
  are no variants (cosmetic; browsers/parsers ignore it).

## Next recommended step

The decision-recipes/candidate-axis thread is now: #1 catalog → #4 picker → #5 recipes →
meaning-aware scoring → **#6 prompt variants (this)**. Natural next options:
- **Catalog price/source accuracy pass** (roadmap; non-blocking — a measured receipt cost always
  outranks a list price).
- **Prompt-aware mocks** for a more compelling keyless prompt-compare demo (only if desired).
- **Cross-product (models × prompts)** if a real need appears (deliberately deferred in this slice).
- Non-blocking debt: still **no git remote** — all `main` commits are local.
