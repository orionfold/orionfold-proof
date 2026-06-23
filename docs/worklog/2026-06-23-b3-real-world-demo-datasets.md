# Worklog — 2026-06-23 · B3 real-world demo datasets

## Summary

Implemented the approved spec `_SPECS/2026-06-23-real-world-demo-datasets.md` — three new bundled
**synthetic** datasets so a fresh install's demo material spans **four rubric classes** (keypoint ·
exact · contains · LLM judge), each a clear-winner demo on a distinct task shape. All additive; **no
migration**. The existing `investment-memo-summarization` (keypoint) sample is unchanged.

| Catalog id | Task shape | `check_hint` → rubric | Demo result (real models) |
|---|---|---|---|
| `support-ticket-triage` | ticket → one category label | `exact` → **exact** | clear winner, 100% |
| `contract-field-extraction` | clause → key field value | `substring` → **contains** | clear winner, 100% |
| `buyer-need-solution-match` | pain → pitch + named proof | none → **similarity**, UI auto-judge | clear winner via LLM judge |

5 examples each, fully synthetic (no real client/operator data — privacy invariant honored).

### What shipped

- **3 dataset JSON** in `src/orionfold/data/datasets/`: `support_ticket_triage.json`,
  `contract_field_extraction.json`, `buyer_need_solution_match.json`. Triage/extraction carry **no
  keypoints** (so the seeded `check_hint` resolves the kind); buyer-match carries no keypoints and
  no hint (falls through to similarity; the UI demo-judge-default `50155bb` auto-picks the LLM judge
  because the seeded copy is `is_sample`).
- **`data/__init__.py`** — 3 entries added to `_DATASET_FILES`; `bundled_datasets()` /
  catalog / import surface pick them up automatically. Docstring corrected ("one in v0" → all).
- **`sample_data.py` refactor** — the single hardwired seed became a frozen `SampleSpec` dataclass +
  a `_SAMPLES` list (investment-memo first, then the three new). `seed_sample_data` loops
  `_seed_one(conn, spec)` per spec → `insert_sample_dataset(...)` + `run_proof(...)` with the two
  mocks + `save_report(..., is_sample=True)`, and now returns **`(4, 4)`**. Each new sample gets its
  own `sample_id` (`sample-ticket-triage` / `sample-contract-extraction` / `sample-buyer-match`),
  `run_sample0N` receipt id (`02`/`03`/`04`), `ProofBrief`, `source="Bundled with Orionfold"`, and
  per-dataset `check_hint`. `remove_sample_data` is unchanged (still clears **all** `is_sample` rows →
  idempotency holds). Back-compat: the original `SAMPLE_DATASET_ID`/`SAMPLE_RUN_ID`/`SAMPLE_BRIEF`/
  `SAMPLE_CHECK_HINT` constants are preserved (tests + tooling reference them).
- **Seed-time scoring fidelity:** `_seed_one` passes `check_hint=spec.check_hint` into
  `default_rubric_for`, so each seeded receipt is scored by the **same** rubric a real run would
  resolve (triage→exact, extraction→contains). The investment-memo sample's `check_hint="eyeball"` is
  **not** in `_HINT_KIND`, so it still falls through to the keypoint heuristic → keypoint@0.8
  (original behavior preserved; mock `467ddd96c9a5` untouched).
- **SettingsView pluralization (FE).** The seed/remove copy hardcoded "1 dataset, 1 receipt" / "the
  seeded sample dataset"; now it seeds 4. Added a small `pluralize(count, noun)` helper and switched
  the static description to plural. Minimal, scoped to the count change.

### Tests

- **`tests/unit/test_data.py`** — parametrized load+5-example+rubric-resolution per dataset; a
  structural contract each (triage label ∈ fixed category set; extraction expected is a short ≤4-word
  field value; buyer-match expected is a ≥12-word pitch); `bundled_datasets()` lists all four.
- **`tests/unit/test_settings_and_samples.py`** — seed now `(len(_SAMPLES), len(_SAMPLES))` = `(4,4)`;
  all 4 sample datasets + receipts round-trip with `is_sample=1` and the right per-spec metadata
  (empty `check_hint` normalizes to `None` on read — asserted as `spec.check_hint or None`); idempotent
  re-seed = 4+4; remove keeps real rows; clear-all wipes `len(_SAMPLES)` runs.
- **`tests/unit/test_storage.py`** — `seed_datasets` idempotency now asserts `len(bundled_datasets())`
  (4 bundled, INSERT OR IGNORE → no dupes).
- **`tests/integration/test_proof_api.py`** — seed/remove and clear-all endpoints assert
  `len(_SAMPLES)`.

## Verification

- **Backend:** `uv run pytest` → **309 passed** (was 298; +11 across new/updated data + seed tests).
- **Lint/types:** `ruff check src tests` clean; `pyright` on all changed files clean (0 new errors).
- **Frontend:** `pnpm vitest run` → **230 passed**; `tsc --noEmit` exit 0; `pnpm build` clean;
  re-embedded `web/dist` → `src/orionfold/server/static`. **Playwright 13/13.**
- **Seed introspection (mock seed):** all 4 receipts resolve their intended kind with a clear winner —
  `run_sample01` keypoint, `02` exact, `03` contains, `04` similarity; `mock_good` wins each.
- **Real-model browser pass** (Sandbox OFF, real keys, cost OK'd; Haiku 4.5 + GPT-5.4-nano):
  - **triage** → Auto/Exact card reads "here, Exact match"; **Scored by: Exact match**; Haiku 5/5
    (100%), recommended, total $0.0007.
  - **extraction** → Auto card reads "From your dataset hint: Contains text → Contains";
    **Scored by: Contains**; Haiku 5/5 (100%), recommended.
  - **buyer-match** → demo-judge-default auto-selected **LLM judge · claude-haiku-4-5**;
    **Scored by: LLM judge · claude-haiku-4-5**; clear winner (Haiku 20% recommended vs nano 0%);
    verdict explainer "claude-haiku-4-5 is the clear pick"; Run cost reconciles ($0.0098 total).
  - All 3 receipts **secret-free** (md/html/json scanned: 0 matches).
- **Operator decisions (AskUserQuestion):** (a) full browser pass on all 3; (b) loosen the
  buyer-match reference pitches for a stronger demo; (c) after the loosening moved the pass rate only
  marginally (20%/0%), **ship the loosened data as-is** — it's an honest, repeatable clear winner; the
  low absolute pass rate is the LLM-judge@0.8 threshold being strict on open-ended generation, a
  per-run Settings knob, **out of B3 dataset scope**.

## Product impact

A fresh install now demonstrates the proof loop across four rubric classes instead of one
summarization toy — the demo reads like a real builder's actual tasks (triage, extraction,
sales-pitch judgment). Each is a clear-winner receipt, reinforcing the "decide what to trust" north
star with concrete, distinct decision shapes.

## Risks / notes

- **Mock `config_hash 467ddd96c9a5` untouched** by construction (brand-new dataset ids, no shared
  hash path; no new `check_hint` maps to keypoint). **No migration** (all columns exist; index stays 6).
- **buyer-match pass rate is low (20%/0%)** — by design it's a judgment task; the LLM judge's 0.8
  default threshold rarely passes paraphrased generation even against a loosened reference. It's a
  valid clear winner (pass-rate-primary ranking picks Haiku), and avg-score can disagree (nano led
  avg-score once) — exactly the "disagreement is the insight" case the Decide layer handles. If a
  future polish pass wants higher demo pass rates, the lever is the judge threshold (A2 Settings),
  not the data.
- **Pre-existing pyright errors** (9) live in `src/orionfold/receipts/export.py` and
  `recipes/resolution.py` on the **clean pre-B3 tree** (confirmed via stash) — NOT introduced here.
  Flagging because prior handoffs claimed "pyright clean"; worth a separate cleanup, out of B3 scope.
- A stray `support-ticket-triage-v1` row sits in the dev `~/.orionfold/proof.db` from a prior ad-hoc
  import (not from this code) — harmless; clear via Settings → data management for a pristine demo.

## Next recommended step

B3 is the last queued spec item. Back to deferred BACKLOG (operator picks). Natural next =
**#7 packaging · licensing · distribution** (BRAINSTORM/scope FIRST). **#8 git remote + push stays
LAST** — do not surface until packaging is done (operator directive). `main` is local-only with all
work committed.
