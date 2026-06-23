# Spec — Real-world-inspired demo datasets (B3)

> **Status:** DRAFT — awaiting operator approval. No code until approved.
> **Source:** `_IDEAS/backlog.md` §B3. **Priority:** Someday / MED (stronger demo proof material).
> **Decision log (operator, 2026-06-23):** synthesize representative examples (never bundle
> real/sensitive Orionfold data) · add **3** new bundled datasets · trio = **classification +
> extraction + buyer-match** · rubric mix prioritizes **non-judge classes** to round out the story.

## Goal

Make a fresh install's demo material read like *a real builder's actual tasks* rather than one
toy summarization set — by bundling three more synthetic-but-realistic datasets, each chosen so
a proof run produces a **clear winner** (not "NO CLEAR WINNER") and each showcasing a **distinct
rubric class**. Together with the shipped keypoint sample, the bundled demos then span four
rubric classes: keypoint · exact · contains/numeric · LLM judge.

## Privacy invariant (non-negotiable)

Every example is **fully synthetic** — realistic in *shape* (drawn from task types seen across the
`~/orionfold/` portfolio) but containing **no real client, personal, or operator data**. Names,
numbers, companies, and quotes are invented. This honors the local-first / secrets-guard posture:
nothing shipped in the wheel is sensitive. (Real project data stays a user-import concern, out of
scope here.)

## The three datasets

The existing sample (`investment-memo-summarization`, keypoint) is unchanged. New:

| # | Catalog id | Task shape | `check_hint` → rubric | Why it's a clear-winner demo |
|---|---|---|---|---|
| 1 | `support-ticket-triage` | Ticket text → single category label | `exact` → **exact** | One correct label per ticket; weak models pick adjacent/verbose categories. Cheap, fast, unambiguous — the strongest "one model obviously wins" demo. |
| 2 | `contract-field-extraction` | Short doc → extract a key field (date / id / amount) | `numeric` or `substring` → **exact / contains** | Strong models return the exact field; weak ones garble or add prose. Shows the extraction rubric class. |
| 3 | `buyer-need-solution-match` | Enterprise pain statement → best-fit pitch + named proof | (no hint, **no keypoints**) → **similarity**, demo defaults to **LLM judge** | Paraphrase/judgment task — lexical scoring ~0 (the demo-scorer-default trap), so the LLM judge discriminates on hallucinated vs. real proofs and generic vs. specific pitch. |

### Rubric resolution — how each lands on the intended kind
(Per `default_rubric_for` in `scoring/rubric.py`: `check_hint` in `_HINT_KIND` wins → else keypoints → keypoint → else similarity.)

- **#1 `support-ticket-triage`:** examples carry **no `keypoints`**; seeded with `check_hint="exact"`
  → resolves to **exact**. Each `expected_text` is the bare category label (e.g. `"billing"`).
- **#2 `contract-field-extraction`:** **no `keypoints`**; seeded with `check_hint="numeric"`
  (for amount/date fields) or `"substring"` (for id/string fields) → resolves to **exact**/**contains**.
  Pick **one** field type per dataset for a coherent rubric — recommend `substring` → **contains**
  so a correct value embedded in a slightly chatty answer still passes (more forgiving, still
  discriminating). *(Operator: confirm `numeric`/exact vs. `substring`/contains in review.)*
- **#3 `buyer-need-solution-match`:** **no `keypoints`**, **no `check_hint`** → falls through to
  **similarity** as the keyless/backend default; the existing **demo-judge-default** (`50155bb`)
  auto-selects the **LLM judge** for `is_sample` datasets in the UI. This reuses the flagship judge
  path in a second domain. (Backend `rubric:null` path still resolves similarity — consistent with
  the catalog sample's keypoint behavior; the judge is the *UI* default for samples.)

### Example counts
5 examples each (mirrors the shipped sample — enough to separate, small enough to author + run cheaply).

## Files to create / change (all additive; **no migration**)

The schema already has every needed column (`is_sample`, `created_at`, `source`, `check_hint`,
`tags` — migrations 2/3/5). Adding bundled datasets needs **no SQL migration** (next index stays 6,
untouched).

1. **New dataset JSON × 3** — `src/orionfold/data/datasets/`:
   `support_ticket_triage.json` · `contract_field_extraction.json` · `buyer_need_solution_match.json`.
   Each: `id`, `name`, `description`, `examples[]` (`input_text` + `expected_text`; keypoints **only**
   where the rubric is keypoint — i.e. **none** of these three).
2. **`src/orionfold/data/__init__.py`** — add three entries to `_DATASET_FILES`. (`bundled_datasets()`
   and the catalog/import surface pick them up automatically.)
3. **`src/orionfold/sample_data.py`** — **refactor** the single hardwired seed into a small list of
   sample specs and iterate:
   - Define a list like `_SAMPLES = [SampleSpec(catalog_id, sample_id, name, run_id, brief, source,
     check_hint), ...]` (the existing investment-memo entry **first**, then the three new ones).
   - `seed_sample_data` loops: for each spec → `insert_sample_dataset(...)` + `run_proof(...)` with the
     two mocks + `save_report(..., is_sample=True)`. Return `(n_datasets, n_receipts)` = `(4, 4)`.
   - Keep `remove_sample_data` as the idempotency front (it already clears **all** `is_sample` rows).
   - Each new sample gets its own `SAMPLE_*` constants (id `sample-<shape>`, run id `run_sample0N`,
     `created_at`, a `ProofBrief`, `source="Bundled with Orionfold"`, the per-dataset `check_hint`).

## Tests

- **`tests/unit/test_data.py`** — extend (or parametrize) so each new dataset: loads, validates,
  has the expected example count, and **resolves to its intended rubric kind** via `default_rubric_for`
  (exact / contains / similarity). Add a structural contract per dataset (e.g. triage `expected_text`
  is a label from a fixed category set; extraction `expected_text` appears in/῀matches the field).
- **`tests/unit/test_settings_and_samples.py`** — update the seed assertions: `seed_sample_data`
  now returns **`(4, 4)`**; all four sample datasets + receipts exist with `is_sample=1` and their
  display metadata round-trips; idempotent re-seed still yields exactly 4 + 4; `remove_sample_data`
  still returns the new counts and leaves real rows untouched.
- **No change** to `test_scoring.py` mock-hash guards — the mock matrix dataset is untouched.

## Invariants preserved (must not regress)

- **Mock `config_hash 467ddd96c9a5`:** safe **by construction** — these are brand-new datasets with
  no shared rows and no shared hash path; the mock matrix (keypoints, no hint → keypoint@0.8) is
  never read or modified. None of the new `check_hint` values touch the keypoint default.
- **No migration:** all columns exist; append-only migration **index stays 6** (nothing added).
- **Datasets metadata stays DB+API-only:** `created_at`/`source`/`check_hint`/`tags` written on the
  row via `insert_sample_dataset`, never on the domain `Dataset`/`Example` (unchanged contract).
- **Sample detection unchanged:** datasets by `is_sample`; receipts by `run_sample…` id prefix
  (each new sample uses a `run_sample0N` id).
- **Demo-judge-default (`50155bb`) unchanged:** `buyer-need-solution-match` is `is_sample` with no
  resolved keypoints, so the existing UI auto-judge applies; the other two resolve exact/contains and
  are **not** judge candidates (`prefersSampleJudge` only flips when a real judge cell resolves).

## Out of scope (explicitly fenced)

- Real/imported project data (user-import path) — privacy decision was *synthesize only*.
- The B4 cross-run leaderboard, B5 Quick-Compare depth, B2 promote seam — separate items.
- Any scoring-engine, threshold, or rubric-taxonomy change — datasets ride existing kinds only.
- Frontend changes beyond what the bundled-dataset list surfaces automatically (no new UI).

## Verification plan

1. `uv run pytest` — BE green incl. new/updated data + seed tests (expect `(4, 4)`).
2. `ruff` + `pyright` clean.
3. Re-seed a scratch DB (or Settings → reset) → confirm 4 sample datasets + 4 receipts appear.
4. **Real-model browser pass** (Sandbox OFF, operator-OK'd cost): run a proof on each new dataset →
   confirm each produces a **clear winner** on its intended rubric (triage→exact 100%/clear,
   extraction→contains, buyer-match→LLM judge); receipts record the right "Scored by:" line and are
   **secret-free**. If any dataset reads "NO CLEAR WINNER," tune its synthetic examples before ship.
5. Fresh-context `diff-reviewer` pass.
6. Worklog entry + re-handoff.

## Open question for review

- **#2 field type:** `substring`/**contains** (forgiving) vs `numeric`/**exact** (strict)? Recommend
  **contains** for a cleaner clear-winner without brittle exact-string matching. Confirm in approval.
