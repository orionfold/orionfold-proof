# Leaderboard Recommendation Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the leaderboard from recommending a candidate that produced nothing (an errored candidate wins the 0%-pass tiebreak at 0ms/$0.00 and is crowned unconditionally), and bundle the catalog cleanup that surfaced it.

**Architecture:** Add an error-aware ranking signal (`error_count`) so a fully-errored candidate sorts strictly last; gate the `recommended` flag on `pass_count > 0`; render a calm "No clear winner" state in the receipt (verdict + reason) and the cockpit/receipts UI when nothing passes. Bump `RECEIPT_VERSION` 3 → 4 for the additive field. Remove `claude-fable-5` from the catalog.

**Tech Stack:** Python 3.12+ (Pydantic, pytest), FastAPI; React + TypeScript + Zod + Vitest; Tailwind v4.

## Global Constraints

- **Receipt is the protected artifact** (`.claude/rules/receipts.md`): any schema change bumps the `version` field. We add `error_count` → `RECEIPT_VERSION` becomes **4**.
- **Provenance untouched:** no change to `config_hash`, `run.*`, `proof/engine.py`, `domain/models.py` `Candidate`/`ResultRow`, or the provider boundary. Only `LeaderboardEntry` gains a field.
- **No secrets** in receipts/UI/logs (these surfaces are unchanged here).
- **Keyless mock default** must not regress: existing happy-path tests stay green because the bundled sample keeps `mock_good` at 5/5.
- **Tailwind v4 CSS-var shorthand:** `bg-(--color-x)`, never `bg-[--color-x]`.
- **Test-contract strings that must stay green:** `"100% (5/5)"`, `"Failure cases (5)"`, `"simulated provider failure"`, heading "Orionfold Proof", button `/Run proof/`, regions Leaderboard / Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON".
- **Anthropic default stays `claude-haiku-4-5`** — `test_catalog.py` drift-guard must remain green after removing fable-5.
- **Commands:** `uv run pytest`, `uv run ruff check src tests`, `pnpm --dir web test`, `pnpm --dir web build`, `pnpm --dir web e2e` (rebuild embed first: `bash scripts/build.sh`). Restart `orionfold up` after backend/catalog edits.

---

### Task 1: Error-aware ranking + recommend gate (backend, pure)

**Files:**
- Modify: `src/orionfold/domain/models.py` (add `error_count` to `LeaderboardEntry`, after `failure_count`)
- Modify: `src/orionfold/proof/leaderboard.py` (compute `error_count`, new sort key, gated recommend, docstring)
- Test: `tests/unit/test_leaderboard.py` (new file)

**Interfaces:**
- Consumes: `Candidate`, `ResultRow`, `LeaderboardEntry` from `orionfold.domain.models`; `build_leaderboard(candidates, results)`.
- Produces: `LeaderboardEntry.error_count: int`; `build_leaderboard` ranks fully-errored candidates last and sets `recommended` only when `entries[0].pass_count > 0`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_leaderboard.py`:

```python
"""build_leaderboard ranking + recommend-gate (the 'what to trust' verdict)."""

from __future__ import annotations

from orionfold.domain.models import Candidate, ResultRow
from orionfold.proof.leaderboard import build_leaderboard


def _cand(cid: str) -> Candidate:
    return Candidate(id=cid, label=cid, provider_id=cid)


def _row(cid: str, idx: int, *, score: float, passed: bool, latency: int,
         cost: float = 0.0, error: str | None = None) -> ResultRow:
    return ResultRow(
        candidate_id=cid,
        example_index=idx,
        input_text="in",
        expected_text="exp",
        output_text="" if error else "out",
        score=score,
        passed=passed,
        latency_ms=latency,
        estimated_cost_usd=cost,
        privacy="local",
        error=error,
    )


def test_all_errored_candidate_ranks_below_a_real_low_scorer():
    # 'erro' errors on every example (0ms/$0.00); 'real' runs but scores low.
    cands = [_cand("erro"), _cand("real")]
    results = [
        _row("erro", 0, score=0.0, passed=False, latency=0, error="boom"),
        _row("erro", 1, score=0.0, passed=False, latency=0, error="boom"),
        _row("real", 0, score=0.05, passed=False, latency=3000),
        _row("real", 1, score=0.05, passed=False, latency=3000),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "real"  # any real output beats a total error
    assert entries[1].candidate_id == "erro"


def test_real_zero_score_still_beats_total_error_on_tie():
    # Both 0/5 at avg_score 0.0; the errored one reports 0ms so the OLD tiebreak crowned it.
    cands = [_cand("erro"), _cand("real")]
    results = [
        _row("erro", 0, score=0.0, passed=False, latency=0, error="boom"),
        _row("real", 0, score=0.0, passed=False, latency=2500),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "real"


def test_no_candidate_recommended_when_top_passes_zero():
    cands = [_cand("a"), _cand("b")]
    results = [
        _row("a", 0, score=0.1, passed=False, latency=100),
        _row("b", 0, score=0.0, passed=False, latency=50, error="boom"),
    ]
    entries = build_leaderboard(cands, results)
    assert all(not e.recommended for e in entries)


def test_top_recommended_when_it_passes_at_least_one():
    cands = [_cand("good"), _cand("bad")]
    results = [
        _row("good", 0, score=1.0, passed=True, latency=40),
        _row("bad", 0, score=0.1, passed=False, latency=120),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "good"
    assert entries[0].recommended is True
    assert entries[1].recommended is False


def test_error_count_is_computed():
    cands = [_cand("mix")]
    results = [
        _row("mix", 0, score=0.0, passed=False, latency=0, error="boom"),
        _row("mix", 1, score=0.3, passed=False, latency=120),
    ]
    [entry] = build_leaderboard(cands, results)
    assert entry.error_count == 1
    assert entry.failure_count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_leaderboard.py -v`
Expected: FAIL — `test_error_count_is_computed` errors on unknown field / `validation error` for `error_count`, and the ranking/recommend tests fail (old logic crowns the errored candidate and recommends unconditionally).

- [ ] **Step 3a: Add the `error_count` field**

In `src/orionfold/domain/models.py`, inside `class LeaderboardEntry`, add `error_count` immediately after `failure_count`:

```python
    failure_count: int
    error_count: int = 0
```

- [ ] **Step 3b: Compute `error_count` and fix ranking + gate**

In `src/orionfold/proof/leaderboard.py`, inside the per-candidate loop add the error count alongside the other aggregates:

```python
        pass_count = sum(1 for r in rows if r.passed)
        failure_count = total - pass_count
        error_count = sum(1 for r in rows if r.error is not None)
```

Pass it to the `LeaderboardEntry(...)` constructor (add `error_count=error_count,` after `failure_count=failure_count,`).

Replace the sort + recommend block (currently lines 47-50):

```python
    # Best first: a candidate that produced any real output always outranks a fully-errored
    # one (which reports 0ms/$0.00 and would otherwise win the latency/cost tiebreak); then
    # highest pass rate, then highest avg score, then lowest latency, then lowest cost.
    def _all_errored(e: LeaderboardEntry) -> bool:
        return e.total > 0 and e.error_count == e.total

    entries.sort(
        key=lambda e: (
            _all_errored(e),
            -e.pass_rate,
            -e.avg_score,
            e.avg_latency_ms,
            e.total_estimated_cost_usd,
        )
    )
    # Only crown a winner that actually passed at least one example — never recommend a
    # candidate that produced nothing.
    if entries and entries[0].pass_count > 0:
        entries[0].recommended = True
    return entries
```

Update the module docstring's second sentence to: "The top entry is marked ``recommended`` only when it passed at least one example, so the receipt never crowns a candidate that produced nothing."

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_leaderboard.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/domain/models.py src/orionfold/proof/leaderboard.py tests/unit/test_leaderboard.py
git commit -m "fix(leaderboard): rank errored candidates last; recommend only when a candidate passes

An errored candidate reports 0ms/\$0.00 and won the 0%-pass latency/cost
tiebreak, then got recommended unconditionally. Add error_count, sort
all-errored candidates strictly last, and gate recommended on pass_count>0.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Receipt "No clear winner" verdict + version bump (backend)

**Files:**
- Modify: `src/orionfold/receipts/export.py` (`RECEIPT_VERSION`, `build_receipt` verdict/recommendation branch, MD + HTML errored-row annotation)
- Test: `tests/unit/test_receipt_no_winner.py` (new file)

**Interfaces:**
- Consumes: `build_receipt(report)`, `to_markdown(report)` from `orionfold.receipts.export`; `LeaderboardEntry.error_count` (Task 1).
- Produces: receipt dict with `receipt_version == 4`; `verdict == "No clear winner"` and a threshold-bearing `recommendation` when no candidate passed; "errored, no output" annotation on all-errored leaderboard rows.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_receipt_no_winner.py`:

```python
"""Receipt presents a calm 'No clear winner' state when nothing passed."""

from __future__ import annotations

from orionfold.domain.models import (
    Candidate,
    LeaderboardEntry,
    ProofBrief,
    ProofReport,
    ProofRun,
    ResultRow,
    Rubric,
)
from orionfold.receipts.export import RECEIPT_VERSION, build_receipt, to_markdown


def _report(*, pass_count: int, error_count: int) -> ProofReport:
    cand = Candidate(id="erro", label="Erro", provider_id="erro")
    run = ProofRun(
        id="run_test01",
        brief=ProofBrief(task_name="t", decision_question="q?"),
        dataset_id="d",
        dataset_name="D",
        rubric=Rubric(threshold=0.8),
        candidates=[cand],
        config_hash="hash",
        created_at="2026-06-20T00:00:00Z",
    )
    entry = LeaderboardEntry(
        candidate_id="erro", label="Erro", provider_id="erro", privacy="local",
        total=5, pass_count=pass_count, pass_rate=pass_count / 5,
        avg_score=0.0, avg_latency_ms=0, total_estimated_cost_usd=0.0,
        failure_count=5 - pass_count, error_count=error_count,
    )
    rows = [
        ResultRow(candidate_id="erro", example_index=i, input_text="in",
                  expected_text="exp", output_text="", score=0.0, passed=False,
                  latency_ms=0, estimated_cost_usd=0.0, privacy="local", error="boom")
        for i in range(5)
    ]
    return ProofReport(run=run, leaderboard=[entry], results=rows)


def test_no_winner_verdict_and_reason():
    data = build_receipt(_report(pass_count=0, error_count=5))
    assert data["receipt_version"] == 4
    assert data["verdict"] == "No clear winner"
    assert "No candidate passed the rubric" in data["recommendation"]
    assert "0.80" in data["recommendation"]


def test_markdown_marks_all_errored_row_and_has_no_star():
    md = to_markdown(_report(pass_count=0, error_count=5))
    assert "⭐" not in md
    assert "errored, no output" in md


def test_version_is_four_with_a_winner():
    data = build_receipt(_report(pass_count=5, error_count=0))
    assert data["receipt_version"] == 4
    assert data["verdict"] != "No clear winner"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_receipt_no_winner.py -v`
Expected: FAIL — `receipt_version` is 3; `verdict` is "Reject" not "No clear winner"; "errored, no output" absent.

- [ ] **Step 3a: Bump the version + no-winner branch in `build_receipt`**

In `src/orionfold/receipts/export.py`, change the version constant + comment:

```python
# v4: leaderboard entries carry an `error_count` field; a fully-errored candidate ranks last
# and is never recommended, and the receipt shows a "No clear winner" state when none passed.
# Bump on any schema change so downstream consumers can detect drift.
RECEIPT_VERSION = 4
```

In `build_receipt`, replace the `top` line and the `verdict`/`recommendation` entries:

```python
    top = report.leaderboard[0] if report.leaderboard else None
    has_winner = top is not None and top.pass_count > 0
```

```python
        "verdict": _verdict(top) if has_winner else ("No clear winner" if top else "No run"),
        "recommendation": (
            _recommendation_line(top)
            if has_winner
            else (
                f"No candidate passed the rubric (threshold {run.rubric.threshold:.2f})."
                if top
                else "No candidates were run."
            )
        ),
```

- [ ] **Step 3b: Annotate all-errored rows in Markdown + HTML**

Add a small helper near `_md_cell` in `export.py`:

```python
def _failures_label(e: dict) -> str:
    """Annotate a fully-errored candidate so the standings read honestly."""
    if e["total"] and e["error_count"] == e["total"]:
        return f"{e['failure_count']} (errored, no output)"
    return str(e["failure_count"])
```

In `to_markdown`'s leaderboard loop, replace the trailing `{e['failure_count']} |` with `{_failures_label(e)} |`.

In `to_html`'s row builder, replace `<td>{e['failure_count']}</td>` with `<td>{html.escape(_failures_label(e))}</td>`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_receipt_no_winner.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/receipts/export.py tests/unit/test_receipt_no_winner.py
git commit -m "feat(receipts): 'No clear winner' state + error annotation; RECEIPT_VERSION 4

When no candidate passes the rubric, the receipt states 'No clear winner'
with the threshold instead of crowning a loser, and fully-errored rows are
marked 'errored, no output'. error_count is a new leaderboard field (v4).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Remove `claude-fable-5` from the catalog (Finding 3)

**Files:**
- Modify: `src/orionfold/catalog/catalog.json` (remove the `claude-fable-5` entry; add `"latest": true` to `claude-opus-4-8`)
- Test: `tests/unit/test_catalog.py` (add an assertion that fable-5 is gone)

**Interfaces:**
- Consumes: `load_catalog()`, `default_model_for(provider_id)` from `orionfold.catalog`.
- Produces: a catalog with no `claude-fable-5`; the claude family's only frontier model (`claude-opus-4-8`) flagged `latest`. `default_model_for("anthropic")` unchanged (`claude-haiku-4-5`).

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_catalog.py`, add:

```python
def test_fable_5_not_in_catalog():
    catalog = load_catalog()
    ids = [m.id for p in catalog.providers for m in p.models]
    assert "claude-fable-5" not in ids


def test_anthropic_frontier_is_opus_and_flagged_latest():
    catalog = load_catalog()
    anthropic = next(p for p in catalog.providers if p.id == "anthropic")
    frontier = [m for m in anthropic.models if m.tier == "frontier"]
    assert [m.id for m in frontier] == ["claude-opus-4-8"]
    assert frontier[0].latest is True
```

> Note: if `load_catalog()`'s provider/model attribute names differ (e.g. `.entries`), match the existing accessors already used elsewhere in `test_catalog.py`. Check the top of that file for the established pattern before writing.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_catalog.py -v`
Expected: FAIL — fable-5 still present; opus-4-8 not flagged `latest`.

- [ ] **Step 3: Edit the catalog JSON**

In `src/orionfold/catalog/catalog.json`: delete the entire `claude-fable-5` object (the block at lines ~57-72, including its leading comma so the array stays valid), and add `"latest": true,` to the `claude-opus-4-8` object (e.g. right after its `"cost_class": "$$$",` line, mirroring how fable-5 placed `"latest": true`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_catalog.py -v`
Expected: PASS — including the existing `test_default_model_for_matches_current_defaults` (anthropic → `claude-haiku-4-5`, unaffected).

Also confirm valid JSON: `uv run python -c "import json; json.load(open('src/orionfold/catalog/catalog.json'))"` → no output (success).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/catalog/catalog.json tests/unit/test_catalog.py
git commit -m "fix(catalog): remove claude-fable-5 (unavailable); flag opus-4-8 as latest frontier

Fable 5 errors on the account and made the cost-vs-quality 'Frontier' arm
resolve to an unavailable model. Removing it resolves Frontier to
claude-opus-4-8; the anthropic default (claude-haiku-4-5) is unchanged.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Frontend "No clear winner" state + error annotation

**Files:**
- Modify: `web/src/lib/api.ts` (add `error_count` to `leaderboardEntrySchema`)
- Modify: `web/src/features/proof/ProofCockpit.tsx` (`DecisionSummary` null-safe + no-winner card)
- Modify: `web/src/features/proof/ReceiptsView.tsx` (`winnerOf` → null when no winner; no-winner summary line)
- Modify: `web/src/features/proof/Leaderboard.tsx` (errored-row annotation)
- Modify: `web/src/test/fixtures.ts` (add `error_count` to the sample entry; add a no-winner fixture)
- Test: `web/src/features/proof/DecisionSummary.test.tsx` (new file)

**Interfaces:**
- Consumes: `LeaderboardEntry` (now with `error_count`), `SAMPLE_REPORT`, a new `NO_WINNER_REPORT` fixture.
- Produces: `DecisionSummary` renders a calm no-winner card (no "Recommended" badge) when no entry is `recommended`; `Leaderboard` shows "errored, no output" for `error_count === total`.

- [ ] **Step 1: Write the failing test**

First extend `web/src/test/fixtures.ts` — add `error_count: 0,` to the existing entry (after `failure_count: 0,`), then append a no-winner fixture:

```typescript
// No candidate passed: one ran-but-failed, one fully errored. Nothing recommended.
export const NO_WINNER_REPORT: ProofReport = {
  ...SAMPLE_REPORT,
  leaderboard: [
    {
      candidate_id: "real", label: "Real · ran", provider_id: "ollama", privacy: "local",
      model: "llama3.2", total: 5, pass_count: 0, pass_rate: 0, avg_score: 0.05,
      avg_latency_ms: 3000, total_estimated_cost_usd: 0, failure_count: 5, error_count: 0,
      recommended: false,
    },
    {
      candidate_id: "erro", label: "Erro · errored", provider_id: "anthropic", privacy: "cloud",
      model: "claude-opus-4-8", total: 5, pass_count: 0, pass_rate: 0, avg_score: 0,
      avg_latency_ms: 0, total_estimated_cost_usd: 0, failure_count: 5, error_count: 5,
      recommended: false,
    },
  ],
};
```

Create `web/src/features/proof/DecisionSummary.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NO_WINNER_REPORT, SAMPLE_REPORT } from "../../test/fixtures";
import { ProofCockpit } from "./ProofCockpit";

// DecisionSummary is not exported; assert via the surfaces it renders. If ProofCockpit needs
// providers/query context to mount, prefer exporting DecisionSummary and testing it directly.
describe("DecisionSummary no-winner state", () => {
  it("shows a calm no-winner message when nothing is recommended", () => {
    render(<DecisionSummary brief={NO_WINNER_REPORT.run.brief} leaderboard={NO_WINNER_REPORT.leaderboard} />);
    expect(screen.getByText(/No clear winner/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Recommended$/)).not.toBeInTheDocument();
  });

  it("shows the recommended winner when one passed", () => {
    render(<DecisionSummary brief={SAMPLE_REPORT.run.brief} leaderboard={SAMPLE_REPORT.leaderboard} />);
    expect(screen.getByText(/Recommended/)).toBeInTheDocument();
  });
});
```

> This test imports `DecisionSummary` directly, so Step 3 must `export` it from `ProofCockpit.tsx`. Adjust the import line to `import { DecisionSummary } from "./ProofCockpit";`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test DecisionSummary`
Expected: FAIL — `DecisionSummary` is not exported / no-winner text absent.

- [ ] **Step 3a: Zod schema**

In `web/src/lib/api.ts`, inside `leaderboardEntrySchema`, add after `failure_count: z.number(),`:

```typescript
  error_count: z.number(),
```

- [ ] **Step 3b: `DecisionSummary` no-winner card**

In `web/src/features/proof/ProofCockpit.tsx`, `export` the function (`export function DecisionSummary(...)`) and replace its body's winner logic:

```typescript
  const winner = leaderboard.find((e) => e.recommended) ?? null;
  if (leaderboard.length === 0) return null;
  if (!winner) {
    return (
      <section aria-label="Decision" className="grid gap-3">
        <p className="text-sm text-(--color-ink-muted)">
          {brief.decision_question || brief.task_name}
        </p>
        <div className="rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-5">
          <span className="text-xs uppercase tracking-wide text-(--color-ink-faint)">
            No clear winner
          </span>
          <p className="mt-2 text-sm text-(--color-ink-muted)">
            No candidate passed the rubric. See the standings below — least-bad first; an
            errored candidate produced no output.
          </p>
        </div>
      </section>
    );
  }
```

Keep the existing recommended-card markup for the `winner` case below this block.

- [ ] **Step 3c: `ReceiptsView` null-safe winner**

In `web/src/features/proof/ReceiptsView.tsx`, change `winnerOf`:

```typescript
function winnerOf(leaderboard: LeaderboardEntry[]): LeaderboardEntry | undefined {
  return leaderboard.find((e) => e.recommended) ?? undefined;
}
```

The card already guards `{winner && ...}`, so a no-winner run simply omits the "Winner" line. Directly below that block, add a no-winner note:

```tsx
        {!winner && report.leaderboard.length > 0 && (
          <div className="text-sm text-(--color-ink-muted)">No clear winner</div>
        )}
```

- [ ] **Step 3d: `Leaderboard` errored-row annotation**

In `web/src/features/proof/Leaderboard.tsx`, replace the Failures cell (`<td className="p-3">{e.failure_count}</td>`):

```tsx
                <td className="p-3">
                  {e.failure_count}
                  {e.total > 0 && e.error_count === e.total && (
                    <span className="ml-1 text-(--color-ink-faint)">(errored, no output)</span>
                  )}
                </td>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test DecisionSummary`
Expected: PASS (2 tests).

Then the full unit suite: `pnpm --dir web test`
Expected: PASS (prior 44 + new tests; the fixture change keeps existing view tests green).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/features/proof/ProofCockpit.tsx \
  web/src/features/proof/ReceiptsView.tsx web/src/features/proof/Leaderboard.tsx \
  web/src/test/fixtures.ts web/src/features/proof/DecisionSummary.test.tsx
git commit -m "feat(web): calm 'No clear winner' state + errored-row annotation

DecisionSummary/ReceiptsView no longer badge leaderboard[0] when nothing
passed; they show a neutral 'No clear winner' card. Leaderboard marks
fully-errored candidates 'errored, no output'. error_count added to schema.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Regenerate samples + full verification + receipt review

**Files:**
- Modify: `samples/receipts/sample-proof-receipt.{json,md,html}` (regenerated)

**Interfaces:**
- Consumes: everything from Tasks 1-4.
- Produces: regenerated sample receipts carrying `receipt_version: 4` and `error_count`; a green full test suite + e2e.

- [ ] **Step 1: Regenerate the bundled sample receipts**

Run: `uv run python scripts/gen_samples.py`
Expected: prints `Wrote sample receipts to .../samples/receipts (config_hash=...)`. The `mock_good` candidate stays the 5/5 recommended winner; the diff is `receipt_version` 3→4, the new `error_count` per entry, and `mock_bad`'s non-zero `error_count` (its ~1-in-5 deterministic errors). Confirm the JSON shows `"receipt_version": 4`.

- [ ] **Step 2: Backend gates**

Run: `uv run pytest -q`
Expected: PASS (146 prior + new leaderboard/receipt/catalog tests).
Run: `uv run ruff check src tests`
Expected: clean.

- [ ] **Step 3: Frontend gates + embed rebuild**

Run: `pnpm --dir web test`
Expected: PASS.
Run: `pnpm --dir web build` then `bash scripts/build.sh`
Expected: clean build; embed rebuilt (required before e2e).
Run: `pnpm --dir web e2e`
Expected: 4/4 (the happy-path recipe/run flow is unchanged).

- [ ] **Step 4: Receipt quality review (no-winner copy)**

Invoke the `receipt-quality-review` skill. Generate an ad-hoc all-fail receipt to eyeball the new state — e.g. in a Python REPL build a `ProofReport` with a tightened rubric so `mock_bad`-style candidates all fail, or reuse the `_report(pass_count=0, error_count=5)` helper pattern — and render `to_markdown`/`to_html`/`to_json`. Confirm: verdict reads "No clear winner", the reason names the threshold, no ⭐, errored rows say "errored, no output", and **no secrets** anywhere. Committing an extra no-winner sample file is optional.

- [ ] **Step 5: Live browser check + commit samples**

Restart the server on a provably-free port (assert the listener PID is yours), load the cockpit, and confirm a normal run still shows the recommended winner. Optionally run a deliberately-failing config to see the no-winner card render. Then:

```bash
git add samples/receipts/
git commit -m "chore(samples): regenerate receipts for RECEIPT_VERSION 4 (error_count)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-review notes

- **Spec coverage:** ranking + error_count + recommend gate → Task 1; RECEIPT_VERSION 4 + no-winner verdict/recommendation + errored annotation → Task 2; Finding 3 catalog → Task 3; api schema + DecisionSummary + ReceiptsView + Leaderboard + fixtures → Task 4; sample regen + full verification + receipt-quality-review → Task 5. All spec sections mapped.
- **Type consistency:** `error_count` is the single field name across `models.py`, `leaderboard.py`, `export.py`, `api.ts`, fixtures, and tests. `build_leaderboard`, `build_receipt`, `to_markdown`, `winnerOf`, `DecisionSummary` signatures match their call sites.
- **Verification gotchas folded in:** rebuild embed before e2e; restart server after backend/catalog edits; the catalog test must match the existing `load_catalog()` accessor names (flagged in Task 3 Step 1).
