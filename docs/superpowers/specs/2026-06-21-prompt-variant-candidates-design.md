# Design — #6 Prompt-variant candidates

- **Status:** Approved (operator-approved 2026-06-21)
- **Date:** 2026-06-21
- **Thread:** the candidate-axis thread (#1 catalog → #4 picker → #5 recipes → meaning-aware
  scoring → **#6 prompt variants**). Composes with the picker and recipes; still text-in/
  text-out; **no new provider machinery**.

## Problem

Today every candidate uses one global, hardcoded system prompt (`TASK_SYSTEM_PROMPT` in
`providers/http.py:81`). The only axis a user can vary is `provider:model`. But a huge part of
"which AI is worth trusting" is *how you instruct it* — the wording of the system prompt. A
consultant iterating on a summarization task wants to prove **which phrasing of their
instructions produces the most trustworthy output on their own dataset**, holding the model
fixed. There is no way to do that now.

## Decision (locked in brainstorm 2026-06-21)

A new comparison axis: **hold the model fixed, vary the system prompt.** Answers the decision
*"which wording of my instructions produces the most trustworthy output on my task?"*

Locked choices:

1. **Run shape:** one model, N prompts. Each prompt variant becomes a leaderboard row. (Not a
   cross-product of models × prompts — keeps the "which prompt wins?" signal clean and the
   matrix 2-D.)
2. **Authoring:** free-text, named variants, seeded with 2 editable starter presets. Minimum 2
   variants to run.
3. **Placement:** a `Compare by: Models | Prompts` toggle in `RunSetup`. *Models* = today's
   picker + recipes, untouched. *Prompts* = pick one model + author prompts. One axis at a time.

## Non-goals (YAGNI)

- Cross-product of multiple models × multiple prompts (deferred; muddies the decision).
- A bundled preset *library* of prompts (the whole point is testing **your** wording).
- Per-Proof-Brief prompt templating with variable interpolation (still deferred per ADR-0002).
- Varying the **user** message / few-shot examples (only the system prompt varies in v0).
- Making mock providers prompt-aware (they stay deterministic and prompt-agnostic — see Keyless).

## Architecture

The clean seam: **a system prompt is a field on `Candidate`.** A prompt variant is then *just a
candidate*, so the existing 2-D candidate-major matrix (`iter_matrix`), streaming progress,
leaderboard, scoring, and failure-case browser all work unchanged. No third dimension.

### Data model (`src/orionfold/domain/models.py`)

`Candidate` gains:

```python
system_prompt: str | None = None   # None → global TASK_SYSTEM_PROMPT (unchanged behavior)
```

`None` for every existing/model-compare candidate; non-None only for prompt variants.

### Identity

A prompt-variant candidate id is `{model_candidate_id}#{slug}`, e.g.
`anthropic:claude-haiku-4-5#terse`.

- `#` is a distinct separator from the `:` used for the model split, so existing parsing in
  `build_candidates` (split on first `:`) and `get_provider(candidate.provider_id)` routing are
  unaffected (`provider_id` stays bare, e.g. `anthropic`; `model` stays the bare model id).
- `slug` = normalized slug of the variant name (lowercase, non-alphanumeric → `-`, collapsed).
  Slugs are **deduped** within a run (`-2`, `-3`, …) so two variants named the same still get
  distinct ids.
- The id only needs to be unique per row and stable for `config_hash`; `#slug` keeps it
  human-readable in logs and SSE frames.

### API / run request (`src/orionfold/server/routes.py`)

`RunRequest` gains:

```python
prompt_variants: list[PromptVariant] | None = None
# PromptVariant = {name: str, system_prompt: str}
```

Server flow in **both** run endpoints (`/api/runs`, `/api/runs/stream`):

```text
base = build_candidates(body.candidate_ids)   # resolves the selected model(s)
if body.prompt_variants:
    validate: len(base) == 1                   # exactly one model  → else 422
    validate: len(prompt_variants) >= 2        # a comparison needs 2+ → else 422
    validate: each name & system_prompt non-empty (stripped) → else 422
    candidates = expand_prompt_variants(base[0], body.prompt_variants)
else:
    candidates = base                          # byte-for-byte today's behavior
```

`expand_prompt_variants(base, variants)` lives next to `build_candidates`
(`providers/registry.py`) and mints one `Candidate` per variant:

- `id = f"{base.id}#{slug}"` (deduped)
- `label = variant.name` (the model is shown once elsewhere; row label is the variant)
- `provider_id`, `privacy`, `model` copied from `base`
- `system_prompt = variant.system_prompt`

Validation errors raise a 422 (the global `RequestValidationError` handler already strips the
echoed body). A misconfigured judge still 422s as today.

### Provider threading

Add a tiny helper in `providers/http.py`:

```python
def system_prompt_for(candidate: Candidate) -> str:
    return candidate.system_prompt or TASK_SYSTEM_PROMPT
```

Replace the four hardcoded `TASK_SYSTEM_PROMPT` uses with `system_prompt_for(candidate)`:

- `anthropic.py` (`system=`)
- `openai_compatible.py` (system message)
- `gemini.py` (`systemInstruction`)
- `ollama.py` (system message)

`safe_generate` already passes the full `candidate` to `provider.generate`, so no signature
change. **Mocks** (`mock_good`/`mock_bad`) ignore `system_prompt` — documented; they stay
deterministic.

### config_hash (`src/orionfold/proof/engine.py`)

Include `system_prompt` in the per-candidate dict **only when non-None**:

```python
cand = {"id": c.id, "provider_id": c.provider_id, "privacy": c.privacy, "model": c.model}
if c.system_prompt is not None:
    cand["system_prompt"] = c.system_prompt
```

- Existing model-compare runs keep **byte-for-byte identical** hashes → zero sample-receipt
  churn for those, no re-pinning of existing config_hash assertions.
- Two variants of one model differ only by `system_prompt` → distinct hashes; a re-run with the
  same prompts reproduces the hash (repeatability preserved).

### Receipt (`src/orionfold/receipts/export.py`) — RECEIPT_VERSION 5 → 6

Provenance is the point: "which wording is trustworthy" is meaningless without showing the
wording. Prompt variants are author-written instructions, **never secrets** → safe to include
(the judge-key redaction path is untouched; `Rubric`/receipts still carry no key field).

**Data path:** `LeaderboardEntry` gains `system_prompt: str | None = None`, populated in
`build_leaderboard` from `cand.system_prompt` (the function already receives the candidate list
— `leaderboard.py:14`). The receipt builder reads the variant text from there; `ProofRun.candidates`
also persists it for free.

- **JSON:** each leaderboard entry serializes `system_prompt: str | null` (the actual text,
  `null` for default/model-compare entries).
- **Markdown + HTML:** when any entry has a non-null `system_prompt`, render a **"Prompt
  variants"** section listing each variant name + its prompt text, and note the fixed model
  once. Model-compare receipts render unchanged.
- Bump `RECEIPT_VERSION` to `6` (any receipt-schema change bumps it).
- `ProofReport` already reads back old persisted reports via zeroed defaults; the new field is
  additive/optional so old reports still deserialize.
- Regenerate sample receipts (`scripts/gen_samples.py`) and re-pin the receipt-version
  assertion.

### Leaderboard

No ranking change. Variants are ordinary candidates, so the existing rules hold: never recommend
a 0-pass/all-errored candidate; "No clear winner" neutral state when nobody passes; errored rows
say "errored, no output". Row labels are the variant names; the recommendation names the winning
variant.

### Frontend (`web/src/features/proof/`, `web/src/lib/api.ts`)

- **`Compare by` toggle** in `RunSetup` — `Models | Prompts`.
  - *Models*: today's `CandidatePicker` + recipes, unchanged.
  - *Prompts*: a single-select model `<select>` (flattened from the existing `SelectionPanel` —
    same models the picker offers, including the keyless mocks) + a **PromptVariants editor**.
- **PromptVariants editor:** a list of `{name, system_prompt}` rows, each a short name input + a
  textarea. Add/remove rows; seeded with 2 editable starters:
  - "Baseline" → the current `TASK_SYSTEM_PROMPT` text.
  - "Concise" → a terser variant.
  - **Min 2** non-empty rows to enable Run; soft cap ~6 (to keep receipts sane — `log`/note if
    exceeded rather than silently truncate).
- **`api.ts`:** `RunRequest.prompt_variants?: {name, system_prompt}[]`; `candidateSchema` gains
  optional `system_prompt`; run wiring builds the Prompts payload (single model id + variants)
  vs the Models payload (today's candidate_ids).
- Tailwind v4 CSS-var **parenthesis** shorthand only (`bg-(--color-x)`), per house rule.

## Testing

- **Backend (pytest):**
  - `expand_prompt_variants`: slug generation, dedup (`-2`), label/provider/model/privacy copy,
    `system_prompt` set.
  - Validation 422s: not exactly one model, `<2` variants, empty/whitespace name or prompt.
  - `config_hash`: model-compare hash unchanged vs baseline; two variants distinct; same prompts
    reproduce.
  - Provider threading: each provider's payload uses `candidate.system_prompt` when set, falls
    back to `TASK_SYSTEM_PROMPT` when `None` (assert on the built request payload).
- **Receipt (`receipt-quality-review`):** RECEIPT_VERSION 6; prompt text present in MD/HTML/JSON;
  model-compare receipt unchanged; **no secret** anywhere.
- **Frontend (Vitest):** toggle switches modes; editor add/remove; Run disabled with `<2`
  non-empty variants; payload shape per mode.
- **e2e (Playwright):** switch to Prompts mode, pick a mock model, author 2 variants, Run → 2
  leaderboard rows → export receipt shows the "Prompt variants" section. Runs **keyless**.

## Keyless invariant

The e2e and unit suites stay keyless. In Prompts mode the single model can be a **mock**; mocks
ignore the system prompt, so a keyless prompt-compare run exercises the full plumbing (distinct
candidates, distinct receipt entries, the new receipt section) even though the variants score
identically (a tie → first-wins or "No clear winner"). The real score-differentiating signal
appears on a configured model — that's a property of the feature, not a gap in coverage.

## Invariants preserved (do-not-regress)

- Keyless mock default; mocks pre-selected, bare-id, `model=None`, `system_prompt=None`.
- Leaderboard never recommends a 0-pass/all-errored candidate; calm "No clear winner" across the
  cockpit + 3 receipt formats; errored rows say "errored, no output".
- `default_rubric_for` / Auto scoring unchanged; judge cost stays in `ResultRow.judge_cost_usd` +
  `RunCostSummary` only, never in `estimated_cost_usd` or leaderboard ranking.
- The judge/API key never appears in a receipt/log/response; `Rubric` has no key field.
- Both run endpoints route through `build_candidates`; the global 422 input-stripping handler
  stays; `/api/selection` + `/api/catalog` + `/api/recipes` leak no secrets.
- Test-contract strings intact ("Orionfold Proof", "Connected", button `/Run proof/`, regions
  Leaderboard / Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON", etc.).
- Tailwind v4 parenthesis CSS-var shorthand.

## Files touched (anticipated)

- `src/orionfold/domain/models.py` — `Candidate.system_prompt`; `LeaderboardEntry.system_prompt`.
- `src/orionfold/proof/leaderboard.py` — populate `LeaderboardEntry.system_prompt` from the candidate.
- `src/orionfold/providers/registry.py` — `expand_prompt_variants`.
- `src/orionfold/providers/http.py` — `system_prompt_for`.
- `src/orionfold/providers/{anthropic,openai_compatible,gemini,ollama}.py` — use the helper.
- `src/orionfold/server/routes.py` — `RunRequest.prompt_variants`, fan-out + validation.
- `src/orionfold/proof/engine.py` — `config_hash` conditional `system_prompt`.
- `src/orionfold/receipts/export.py` — RECEIPT_VERSION 6, prompt-variants section + JSON field.
- `web/src/lib/api.ts` — request/schema additions.
- `web/src/features/proof/RunSetup.tsx` (+ new `PromptVariants.tsx`, `CompareByToggle` or inline)
  — toggle, single-model select, variants editor.
- Tests across pytest / Vitest / Playwright; `scripts/gen_samples.py` regen.

## Open follow-ups (non-blocking, out of this slice)

- Cross-product (models × prompts) if a real need appears.
- Prompt-aware mocks for a more compelling keyless demo (only if desired later).
- Catalog price/source accuracy pass (separate roadmap item).
