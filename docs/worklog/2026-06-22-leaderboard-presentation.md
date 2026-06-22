# 2026-06-22 — Leaderboard presentation (sub-project 2 of 3)

## Summary

Shipped **sub-project 2 of the sequenced Datasets → Leaderboard → Quick-Compare effort**:
an additive presentation upgrade to the leaderboard, plus a `$/quality` efficiency metric that
crosses into the Proof Receipt. The leaderboard now ranks visually — a `#`/medal column, a
traffic-light pass-rate bar, a `$ / quality` column, and a strengthened local privacy tag — and the
receipt gains a `$ / quality` column (`RECEIPT_VERSION` 6 → 7). The ranking sort key, the proof
engine, and `config_hash 467ddd96c9a5` are untouched.

Spec: `docs/superpowers/specs/2026-06-22-leaderboard-presentation-design.md`.
Plan: `docs/superpowers/plans/2026-06-22-leaderboard-presentation.md`.

### Operator decisions (2026-06-22)
- `$/quality` is **stored on `LeaderboardEntry` and serialized into the receipt** (bumps the version);
  it is **presentation only and never affects ranking**.
- Score bar visualizes **pass rate** (length + traffic-light color).
- Medals (🥇🥈🥉) appear **only when a real winner exists**; no-winner → plain rank numbers.
- Local badge **strengthened per-row** (lock glyph + stronger neutral ink), no header banner.

## What changed (5 TDD commits on main)

1. `feat(leaderboard): cost_per_quality efficiency field (ranking unchanged)` — `LeaderboardEntry.cost_per_quality: float | None` = `total_estimated_cost_usd / avg_score` when `avg_score > 0`, else `None`. Computed in `build_leaderboard`; sort key unchanged.
2. `feat(receipt): $/quality column + RECEIPT_VERSION 7` — shared `_cost_per_quality_label` helper (`None→"—"`, `0→"Free"`, else `$x.xxxx`), `$ / quality` column in MD + HTML (after Pass rate), auto in JSON; samples regenerated.
3. `feat(leaderboard): cost_per_quality schema + pure format helpers` — `api.ts` schema field (`.nullable().optional()` for pre-v7 receipts); new `leaderboardFormat.ts` (`passRateTone`, `formatCostPerQuality`, `medalFor`).
4. `feat(leaderboard): rank+medals, traffic-light pass-rate bar, $/quality column` — `Leaderboard.tsx` 7→9 columns; bar uses **status tokens** (`--color-ok`/`--color-warn`/`--color-danger`), never the accent.
5. `feat(badges): strengthen the local privacy tag (lock glyph + stronger ink)` — `ProviderTag` `local` variant → `Lock` icon + `text-(--color-ink) font-semibold`; cloud/mock unchanged. Green (`--color-ok`) deliberately **not** used for local (reserved for PASS).

## Verification (evidence, not claims)

- **Backend:** `uv run pytest -q` → **259 passed** (+5 new: `cost_per_quality` value / `None` / `Free` / ranking-unchanged; receipt v7 + column). `ruff` clean.
- **Frontend:** `pnpm --dir web test --run` → **110 passed** (27 files; +9 helper, +4 Leaderboard, +1 badges). `tsc --noEmit` exit 0.
- **Types:** `pyright` on the 3 changed backend files → **0 new errors**. (3 pre-existing errors in `export.py` — `_scored_by`'s untyped `rubric`, and the `_verdict`/`_recommendation_line` `top: … | None` narrowing — confirmed present *before* this change at `git show HEAD~4`; left untouched per "no unrelated refactoring".)
- **Samples:** regenerated; diff is only `cost_per_quality` + `receipt_version` 7 + the new column. **`config_hash 467ddd96c9a5` unchanged** in all three formats.
- **Receipt quality:** no secrets/keys in any sample format; `$ / quality` shows "Free" (winner, cost $0) / "—" (avg_score 0); clear "Ship" verdict naming the winner; `receipt_version: 7`.
- **Browser (`:5175` live source → `:8790` API):** the React leaderboard in the Decide step renders 🥇🥈 medals (winner state), a green 100% pass-rate bar, the `$ / quality` column, and the Recommended badge; the strengthened **Local** tag (lock + bold) reads clearly more prominent than the muted **Cloud** tag in leaderboard rows; the HTML receipt preview shows **Receipt schema v7** and the `$ / quality` column. (Old pre-v7 runs show `$/quality` "—" via the schema's graceful `.nullable().optional()` — correct degradation.)
- **Build + e2e:** `bash scripts/build.sh` embeds the current cockpit; `playwright test proof` → **9 passed, 1 failed**. The pass set includes `proof.spec.ts:100 "prompt compare → leaderboard + receipt section"`, which exercises these changes.

## Risks / follow-ups (out of scope this slice)

1. **Pre-existing e2e failure** — `proof.spec.ts:89 "decision recipes pre-fill the setup"` asserts a button `/Same model, different providers/i`, but the recipe was renamed to **"Different providers"** (decision question "Same model, different hosts…") in a prior session. Neither `recipes.json` nor `proof.spec.ts` was touched by this slice. **Fix = one-line e2e assertion update** to match the current recipe title. Flagged, not silently changed.
2. **Stored "Recommended on 0/5"** — exploring a 2026-06-21 stored no-winner run (Ollama 0/5) in the cockpit shows a "Recommended" badge + medals, because its **persisted** `LeaderboardEntry` has `recommended: true` — data saved before the 2026-06-20 recommend-gate took effect in that session. New runs compute correctly (gate is in `build_leaderboard`). Worth a one-off backfill/recompute pass if old runs should display honestly; not a regression from this slice.

## Product impact

The leaderboard now answers "who do I trust, and is it worth the cost?" at a glance — rank/podium for trust order, a traffic-light bar for pass rate, and `$/quality` for efficiency — and that efficiency number now travels in the client-shareable Proof Receipt. The local-first promise reads louder via the strengthened Local tag, without turning the calm instrument panel into a noisy dashboard.

## Next recommended step

**Sub-project 3: Quick-Compare → Proof Receipt** — a thin 1-prompt × 2-candidate "Quick Compare"
entry mode reusing the existing matrix engine + exporter (head-to-head bars + pick-a-winner; "Save
as Proof Receipt" labeled a single-example quick check). **Brainstorm scope FIRST.** Do NOT build
the free-form chat lane or live token streaming.
