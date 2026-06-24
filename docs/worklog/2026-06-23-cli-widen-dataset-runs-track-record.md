# Worklog — 2026-06-23 · Widen the CLI (dataset · runs · track-record)

## Summary

Second slice of the dual-distribution model (ADR-0004 §8, "vertical slice first, then widen").
The headless CLI graduates from `up`/`dev`/`run` to a full workflow surface, and the B4 cross-run
rollup lands where every shell can reach it — as a **pure core function**, not a frontend module.

**New core primitive — `track_record()` (`proof/leaderboard.py`).**
`track_record(reports, *, dataset_id=None) -> list[TrackRecordGroup]` rolls many runs up into
per-candidate standings, **one group per `(dataset_id, rubric.kind)`** — the comparability rule
locked in the B4 brainstorm (ADR-0004 §5): only runs over the same dataset scored the same way
roll up together (a similarity pass-rate and a judge pass-rate measure different things and must
never be averaged). Quick-compare runs are excluded (`mode=="quick"` / rubric kind `"none"` is
unscored — nothing to aggregate, mirroring `list_runs`/the leaderboard). **Pass-rate is pooled over
examples** (Σpasses / Σexamples), not a mean of per-run rates, so a 100-example run outweighs a
5-example one; `avg_cost_usd` is the mean per-run cost; `times_recommended` counts crowns. The fn is
pure — it reads existing `LeaderboardEntry`/`ProofRun` fields, re-runs no scoring, opens no
connection — so it **cannot touch `config_hash`** by construction. New `TrackRecordGroup` /
`TrackRecordEntry` Pydantic models in `domain/models.py`. Exported via `proof/__init__.py` `__all__`
(it has its two consuming uses — CLI now, the web Track Record screen later — per the §7 graduation
rule); `build_leaderboard` formalized into `__all__` at the same time (already public-by-use).

**New CLI commands (`cli.py`) — thin shells over the existing core (ADR-0004 §3).**
A shared `_with_conn()` context manager (extracted from the `run` command's prior inline
connect/migrate/close boilerplate; `run` now uses it too) opens the local DB, ensures the schema,
and always closes. On top of it:
- `orionfold dataset import <file>` — `parse_dataset` (by extension) + `save_dataset`
  (`--name`/`--description`/`--check-hint`/`--source`); clean exit on duplicate / parse / unsupported.
- `orionfold dataset list` — `list_dataset_rows` → a compact table (id · examples · hint · source · name).
- `orionfold runs list` — `list_runs` → newest-first table (run id · dataset · rubric · winner · created).
- `orionfold runs show <id>` — `get_report` → a verdict summary (leaderboard standings + run cost);
  `--format md|json|html` dumps the full receipt via the **same `_FORMAT_RENDERERS` map `run` uses**,
  so `runs show --format json` is byte-identical to `run --format json`. Clean error on unknown id.
- `orionfold track-record` — the core `track_record()` over `list_runs`; per-candidate standings per
  group; optional `--dataset <id>` filter.

`dataset` and `runs` are Typer sub-groups (`add_typer`). `up`/`dev`/`run` behavior unchanged.

**Deferred this slice (operator decision):** the `DEFAULT_THRESHOLDS` single-source (ADR-0004 §6 —
Python canonical → FE reads generated JSON) is its own follow-up slice, so this one stays BE/CLI-only
and leaves the FE untouched. `track-record` rendering is the full per-candidate standings (not a
group-summary line) — operator chose the richer surface now.

## Verification

- **340 backend tests pass** (was 319 → **+21**: 8 `test_track_record.py` + 13 `test_cli_workflow.py`).
- **ruff clean** on all changed files; **pyright 0 errors** on changed files (one new error — a
  `Privacy` literal narrowing on the `_CandidateAcc` accumulator attribute — caught and fixed with an
  explicit annotation). The pre-existing 9 pyright errors in `receipts/export.py` /
  `recipes/resolution.py` were **not touched** (this slice changes neither file).
- **The 8 `config_hash 467ddd96c9a5` freeze-tests pass** — the mock matrix hash is intact (this slice
  touches no scoring/hash path).
- **Headless e2e** (isolated `ORIONFOLD_DB`, keyless mocks): `dataset import` (→ 3 examples, source
  "imported", hint "exact") → `dataset list` → two `run`s (keypoint, `config_hash 2b80ec4587c2` — a
  different matrix than the canonical bundled mock matrix, as expected) → `runs list` (both runs,
  winner "Mock · good") → `track-record` (one `(run_slice_dataset, keypoint)` group, `runs=2`,
  Mock·good 100%/won 2, Mock·bad 0%/won 0). All output **secret-free** (no `sk-`/`api_key`/`Bearer`).
- Fresh-context **diff-reviewer**: (pending at time of writing — see commit).

## Product impact

The engineer/researcher audience (ADR-0004's first-class second audience) can now drive Proof's whole
loop headlessly — import a dataset, run a proof, inspect history, and read a cross-run track record —
without the cockpit. The B4 "Track Record" computation now lives in the core, so when its web screen
is built it will *render what the core computes*, not re-derive it. "One core, two shells" is now real
across five verbs, and the receipt stays the single protected artifact (one renderer, byte-identical
across `run` and `runs show`).

## Risks

- `track_record` aggregates whatever runs sit in the DB; stale/experimental runs (e.g. the
  "Recommended on 0/5" pre-gate rows noted in backlog #2) will appear in a track record. Acceptable —
  it reflects history honestly; a backfill is a separate backlog item.
- The CLI `run` command still stores runs under the **file-stem** dataset id (ephemeral), not a
  stored dataset id — so a `dataset import`ed set and a `run` over the same file are two different
  dataset ids in `track-record`. Out of scope here; if the CLI later grows `run --dataset-id <id>`
  (run over a *stored* set), the two will reconcile.

## Next recommended step

Operator picks from the deferred backlog. Natural next is the **`DEFAULT_THRESHOLDS` single-source**
slice (ADR-0004 §6, deferred from this one) — Python canonical → FE-consumed generated JSON, keeping
both freeze-tests and keypoint@0.8. Then #7 packaging (Apache-2.0 flip + PyPI metadata) and B7
private-strategy symlink migration, both of which gate the LAST item, #8 git remote + push.
