# Scoring section redesign — design spec

_Date: 2026-06-21 · Status: Approved (operator) · Thread: cockpit usability_

## Problem

The **Scoring method** section of the Proof Run cockpit is a thin first cut. It reuses the
CandidatePicker chip pattern: four equal-weight buttons (Auto · Keypoint · Similarity · LLM
judge) with one dense helper paragraph, and when LLM judge is selected it expands into a flat
wall of chips — `mock_judge` plus every model of every provider. Three usability problems:

1. **It hides a real decision behind jargon.** "Keypoint" vs "Similarity" vs "LLM judge" means
   nothing to an operator deciding what to trust. The per-method guidance is collapsed into one
   skippable paragraph.
2. **The cost asymmetry is invisible.** Auto/Keypoint/Similarity are free, instant, deterministic.
   LLM judge **costs money, adds latency, and is non-deterministic** — a categorically different
   commitment with no visual signal. (Ironic, given the receipt now separates judge cost.)
3. **The judge picker gives no opinion and does not scale.** A flat chip wall of every model
   offers zero guidance and worsens as the catalog grows.

Plus a layout bug: `<ScoringMethod>` renders **after** the "Run proof" button
(`web/src/features/proof/ProofCockpit.tsx:185`, below `<RunSetup>`), so a run input sits below
the action that consumes it.

## Goal

Make the scoring choice legible and opinionated without new backend work:
- Methods become **cards with guidance + cost indicators**, grouped by free-vs-paid.
- The LLM-judge model choice becomes a **two-step filter** (Local/Hosted → Cheapest/Balanced/Best)
  feeding a **dropdown with an opinionated default pre-selected**.
- Scoring method becomes the last configure step, immediately above Run proof.

## Approach (architectural choice)

**Pure frontend. Zero backend change.** Everything required already ships:
- `/api/selection` model fields: `privacy` (`local`|`cloud`), `tier` (`economy`|`balanced`|`frontier`),
  `cost_class` (`free`|`$`|`$$`|`$$$`), `recommended` (bool), `latest` (bool), `available` per group.
- `rubric` schema already carries `judge_provider_id` / `judge_model`.

Rejected alternative: a new `/api/judges/filter` endpoint — buys nothing, adds a round-trip per
toggle. The filter is local state over data we already fetch with `getSelection`.

Consequences: **RECEIPT_VERSION stays 5** (input UI only; the receipt is unchanged). An equivalent
selection yields the same `config_hash`. No change to `routes.py`, `engine.py`, `models.py`,
`scoring/*`, or receipt export.

## Design

### Method cards — grouped (free vs paid)

Two labeled groups make the cost line structural:

```
Scoring method

FREE · INSTANT · REPEATABLE ──────────────────────────
 ┌──────────┐ ┌──────────┐ ┌──────────┐
 │ Auto  ✓  │ │ Keypoint │ │Similarity│
 │ picks the│ │ your key │ │ semantic │
 │ right    │ │ facts    │ │ close-   │
 │ check    │ │ appear   │ │ ness     │
 │ Free     │ │ Free     │ │ Free     │
 └──────────┘ └──────────┘ └──────────┘

COSTS MONEY · ADDS LATENCY ─────────────────────────
 ┌────────────────────────────────────────┐
 │ LLM judge          $ per run · slower    │
 │ A model grades each answer vs expected   │
 └──────────────────────────────────────────┘
```

- Each method is a `MethodCard`: title, one-line "pick when…" guidance, a cost chip
  (`Free` vs `$ per run · slower`), and a selected state mirroring the accent pattern.
- **Auto card is live**: it reads the selected dataset and shows what it resolves to —
  "Auto → **Keypoint coverage** (your dataset has keypoints)" or "→ Similarity (no keypoints)".
  Data source: `datasets.data` already in the cockpit; resolution mirrors backend
  `default_rubric_for` (keypoint if any example has keypoints, else similarity).

Guidance copy (draft, refine in implementation):
- **Auto** — "We pick the right free check for your dataset." cost: Free.
- **Keypoint** — "Checks your authored key facts appear in the answer." cost: Free.
- **Similarity** — "Scores by semantic closeness to the expected answer." cost: Free.
- **LLM judge** — "A model grades each answer against the expected one." cost: `$ per run · slower`.

### LLM judge — two-step filter

Selecting the judge card expands an inline `JudgeFilter`:

```
LLM judge · choose a judge model

 Run on    ( Local ✓ )  ( Hosted )
 Optimize  ( Cheapest ✓ ) ( Balanced ) ( Best )

 ┌─ Judge model ───────────────────────┐
 │ Mock judge — keyless, deterministic ▾│  ← default
 └─────────────────────────────────────┘
 Switch to Hosted for frontier judges (needs a key).
```

- **Run on** ← `privacy`: `Local` / `Hosted`.
- **Optimize** ← `tier`: `Cheapest` (economy) / `Balanced` (balanced) / `Best` (frontier).
- **Judge model** — dropdown of models matching both axes; an opinionated default is **pre-selected**
  (selection rule below).

**Judge-option set** = the synthetic **Mock judge** + every real provider group from
`/api/selection`, **excluding `mock_good` and `mock_bad`**. Those two are answer-generators, not
graders — the current `JudgePicker` lists them only because it iterates all groups; the redesign
drops them. (A provider's *availability* is verified against catalog data observed 2026-06-21:
cloud providers span economy/balanced/frontier; **local tiers come from Ollama**, which spans all
three when running and is availability-gated; **LM Studio is economy-only**. So "Local + Best" with
Ollama down legitimately hits the empty-state path.)

**Default landing = Local + Cheapest → Mock judge** (keyless, deterministic). Mock judge is not a
hardcoded special button — it is synthetically prepended as the single Local+Cheapest judge and is
the default selection, so the keyless invariant holds with no special case in the run path.

**In-filter default selection rule.** `recommended` is a *per-provider* flag (e.g. Anthropic's
recommended is Haiku 4.5, an *economy* model), so it does not survive every tier filter. Within the
filtered set, pick the default as the first of:
1. an **available** provider's model with `recommended: true`, else
2. an **available** provider's model with `latest: true`, else
3. the first **available** model, else
4. the first model overall (will be locked → surface `KeyEntry`).

**Key-gating reuses existing machinery.** If a Hosted selection resolves to a provider whose group
is `available: false`, the dropdown shows those models as locked and the existing inline `KeyEntry`
(from `selectionMeta.CLOUD_KEY_NAMES`) appears — exactly mirroring `CandidatePicker`'s unavailable
rows. The operator adds a key inline; on success the model becomes selectable.

**Empty combos degrade calmly**: if an axis pair yields no models (e.g. no local "Best" judge),
show "No local 'Best' judge — switch to Hosted" rather than an empty dropdown.

### Components (small, single-purpose, testable)

| File | Role |
| --- | --- |
| `MethodCard.tsx` *(new)* | Presentational card: title, guidance, cost chip, selected state. Used by all four methods. |
| `JudgeFilter.tsx` *(new)* | Replaces `JudgePicker`. Owns filter state (privacy, tier); emits `(judge_provider_id, judge_model)`; renders `KeyEntry` when gated. |
| `filterJudgeModels()` *(new pure helper)* | `(panel, privacy, tier) → { models, defaultProviderId, defaultModel }`. Excludes `mock_good`/`mock_bad`; prepends Mock judge to Local+Cheapest; applies the in-filter default rule. Unit-tested in isolation. |
| `ScoringMethod.tsx` | Slimmed: render the two grouped sections, own method state, emit `Rubric \| null`. Delegates cards to `MethodCard`, judge to `JudgeFilter`. |
| `selectionMeta.ts` | Add method guidance/cost copy + tier axis labels. Keep `CLOUD_KEY_NAMES`. |

### Placement fix

Make scoring method the **last configure step, immediately above "Run proof."** Today
`<ScoringMethod>` renders after `<RunSetup>` (which contains the run button). Restructure so the
run button follows the scoring method — either by moving `<ScoringMethod>` into the config card
just above the action, or relocating the run action below it. Exact wiring decided in the plan;
the design requirement is: scoring is configured before the button that consumes it.

## Data flow

1. `ProofCockpit` holds `rubric: Rubric | null` (unchanged) and passes `value`/`onChange` plus the
   selected dataset to `ScoringMethod`.
2. `ScoringMethod` derives the active method; card clicks emit the corresponding rubric (Auto → `null`).
3. Judge card → `JudgeFilter` reads `getSelection()` (cached query), runs `filterJudgeModels`, and on
   pick emits `{ kind: "judge", threshold: 0.8, case_sensitive: false, judge_provider_id, judge_model }`.
4. Run request unchanged: `rubric` omitted when `null` (Auto); otherwise sent verbatim.

## Error / edge handling

- Selection query loading/empty → cards render; judge filter shows a calm "loading judges" state.
- Hosted + missing key → locked option + inline `KeyEntry`; premature run still safely 422s server-side.
- Unknown/empty axis combo → guidance to switch axis (above).
- Auto on a keypoint-less dataset → Auto card shows "→ Similarity".

## Testing

- **Unit (Vitest):**
  - `filterJudgeModels`: Local+Cheapest default = Mock judge; `mock_good`/`mock_bad` excluded;
    tier/privacy filtering; in-filter default rule (recommended → latest → first available → first);
    empty-combo result.
  - `MethodCard`: renders guidance + cost chip; selecting emits the right rubric; Auto shows resolved kind.
  - `JudgeFilter`: defaults to keyless Mock judge; switching to Hosted pre-selects recommended;
    unavailable provider renders `KeyEntry`.
  - Rewrite `ScoringMethod.test.tsx` for the grouped structure.
- **e2e (Playwright):** keyless run still "Scored by Keypoint coverage" (unchanged); assert grouped
  cards + Mock-judge default render. Stays keyless.
- **Visual:** browser verification of both groups + the expanded filter (empty, Local default, Hosted
  with KeyEntry).

## Invariants preserved

- Keyless default (Mock judge = Local+Cheapest default; no key needed to run).
- Judge cost stays separate in `ResultRow.judge_cost_usd` + `RunCostSummary`; never enters a
  candidate's cost or the leaderboard.
- No secrets in UI/receipt/log; `KeyEntry` writes only whitelisted providers to `.env.local`.
- RECEIPT_VERSION 5 unchanged; `config_hash` unaffected for equivalent selections.
- Test-contract strings preserved; Tailwind v4 parenthesis CSS-var syntax (`bg-(--color-x)`).

## Out of scope

- Backend/scoring/receipt changes.
- New judge providers or models (catalog accuracy is a separate roadmap item).
- Prompt-variant candidates (#6) and RAG/workflows (post-v0).
