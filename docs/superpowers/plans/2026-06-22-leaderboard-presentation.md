# Leaderboard Presentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the leaderboard rank visually — rank + podium medals, a traffic-light pass-rate bar, a `$/quality` efficiency column, and a stronger local tag — and surface `$/quality` in the exported Proof Receipt, without changing what the numbers mean or how candidates are ordered.

**Architecture:** One new derived field (`cost_per_quality`) is computed in the leaderboard builder and stored on the `LeaderboardEntry` report object (never the engine-hashed domain models). It is serialized into the receipt (Markdown/HTML/JSON), bumping `RECEIPT_VERSION` 6 → 7. Everything else is pure presentation in the React leaderboard table and the privacy badge. The ranking sort key is untouched.

**Tech Stack:** Python 3.12 + Pydantic + pytest (backend); React + TypeScript + Tailwind v4 + Vitest + Testing Library (frontend).

## Global Constraints

Every task implicitly includes these (copied verbatim from the spec):

- **`config_hash` `467ddd96c9a5` must not change.** `cost_per_quality` lives only on the derived `LeaderboardEntry`, never on the domain `Dataset`/`Example`/`Candidate`/`ResultRow` models, and there is **no change to `proof/engine.py`, the provider boundary, or `run.*`.**
- **Ranking determinism held:** the `build_leaderboard` sort key stays `(_all_errored, -pass_rate, -avg_score, avg_latency_ms, total_estimated_cost_usd)`. The new field never enters the sort.
- **`RECEIPT_VERSION` 6 → 7** (additive schema change; required by `.claude/rules/receipts.md`).
- **`$/quality` display rule (identical on every surface):** `None → "—"`, `0 → "Free"`, else `$` + value to **4 decimals** (`$0.0012`).
- **`$/quality` formula:** `total_estimated_cost_usd / avg_score` when `avg_score > 0`, else `None`. (Cost 0 with score > 0 → `0.0` → "Free".)
- **DS skin:** the score bar uses **status tokens** `--color-ok` (≥0.8), `--color-warn` (≥0.5), `--color-danger` (<0.5) — **never** the cyan `--color-accent` (interactive only). **Do NOT use `--color-ok` (green) for the local tag** — green is reserved for PASS/verified status only; strengthen the local tag with stronger neutral ink instead. Tailwind v4 CSS-var shorthand `bg-(--color-x)`, never `bg-[--color-x]`.
- **No migration** (the field is a derived report value, not a persisted dataset column). Mocks stay bare-id. No secrets in receipts/UI/logs.
- **Medals gate:** 🥇🥈🥉 appear on the top 3 rows **only when a real winner exists** (`entries.some((e) => e.recommended)`); otherwise plain rank numbers.

---

### Task 1: Backend — `cost_per_quality` field + computation

**Files:**
- Modify: `src/orionfold/domain/models.py:103-120` (add field to `LeaderboardEntry`)
- Modify: `src/orionfold/proof/leaderboard.py:22-49` (compute it) and docstring `:1-7`
- Test: `tests/unit/test_leaderboard.py` (extend)

**Interfaces:**
- Produces: `LeaderboardEntry.cost_per_quality: float | None` — `total_estimated_cost_usd / avg_score` when `avg_score > 0`, else `None`. Used by Task 2 (receipt) and Task 3/4 (frontend).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_leaderboard.py`:

```python
def test_cost_per_quality_is_cost_over_avg_score():
    # 0.10 total cost at avg_score 0.5 -> 0.20 dollars per quality point.
    cands = [_cand("c")]
    results = [
        _row("c", 0, score=0.5, passed=False, latency=100, cost=0.05),
        _row("c", 1, score=0.5, passed=True, latency=100, cost=0.05),
    ]
    [entry] = build_leaderboard(cands, results)
    assert entry.avg_score == 0.5
    assert entry.total_estimated_cost_usd == 0.10
    assert entry.cost_per_quality == 0.20


def test_cost_per_quality_is_none_when_avg_score_zero():
    # No quality to be efficient about -> undefined (renders "—"), never a divide-by-zero.
    cands = [_cand("z")]
    results = [_row("z", 0, score=0.0, passed=False, latency=0, error="boom")]
    [entry] = build_leaderboard(cands, results)
    assert entry.avg_score == 0.0
    assert entry.cost_per_quality is None


def test_cost_per_quality_is_zero_when_free():
    # Local/mock cost 0 with real quality -> 0.0 (renders "Free"), the local-first win.
    cands = [_cand("free")]
    results = [_row("free", 0, score=1.0, passed=True, latency=10, cost=0.0)]
    [entry] = build_leaderboard(cands, results)
    assert entry.cost_per_quality == 0.0


def test_cost_per_quality_does_not_change_ranking():
    # A cheap high-quality candidate still outranks an expensive low-quality one on pass_rate,
    # not on the new efficiency field.
    cands = [_cand("good"), _cand("bad")]
    results = [
        _row("good", 0, score=1.0, passed=True, latency=40, cost=0.50),
        _row("bad", 0, score=0.1, passed=False, latency=10, cost=0.00),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "good"  # pass_rate wins; cheaper "bad" does not jump it
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_leaderboard.py -k cost_per_quality -v`
Expected: FAIL — `AttributeError: 'LeaderboardEntry' object has no attribute 'cost_per_quality'` (or a Pydantic validation error).

- [ ] **Step 3: Add the model field**

In `src/orionfold/domain/models.py`, add to `LeaderboardEntry` immediately after `recommended: bool = False` (line 120):

```python
    recommended: bool = False
    cost_per_quality: float | None = None  # $ per quality point (cost/avg_score); None if avg_score==0. Presentation only — never affects ranking.
```

- [ ] **Step 4: Compute it in the builder**

In `src/orionfold/proof/leaderboard.py`, inside the per-candidate loop, after `total_cost = sum(...)` (line 31) add:

```python
        total_cost = sum(r.estimated_cost_usd for r in rows)
        cost_per_quality = total_cost / avg_score if avg_score > 0 else None
```

Then add the field to the `LeaderboardEntry(...)` constructor (after `error_count=error_count,`):

```python
                error_count=error_count,
                cost_per_quality=cost_per_quality,
```

Update the module docstring (`leaderboard.py:1-7`) with a closing sentence:

```python
The standing also carries ``cost_per_quality`` (cost per quality point) for presentation;
it does not affect ranking.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_leaderboard.py -v`
Expected: PASS (all existing + 4 new). Then `uv run pyright src/orionfold/proof/leaderboard.py src/orionfold/domain/models.py` — clean.

- [ ] **Step 6: Commit**

```bash
git add src/orionfold/domain/models.py src/orionfold/proof/leaderboard.py tests/unit/test_leaderboard.py
git commit -m "feat(leaderboard): cost_per_quality efficiency field (ranking unchanged)"
```

---

### Task 2: Backend — receipt v7 + `$ / quality` column + sample regen

**Files:**
- Modify: `src/orionfold/receipts/export.py` (version, helper, MD header+row, HTML thead+row)
- Test: `tests/unit/test_receipts.py` (version + column assertions)
- Regenerate: `samples/receipts/*` via `scripts/gen_samples.py`

**Interfaces:**
- Consumes: `LeaderboardEntry.cost_per_quality` (Task 1), present in `e.model_dump()`.
- Produces: `RECEIPT_VERSION == 7`; a `$ / quality` column between Pass rate and Avg score in MD + HTML; the field auto-present in JSON.

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_receipts.py`, change `test_receipt_version_is_6` (line 126) to:

```python
def test_receipt_version_is_7():
    assert export.RECEIPT_VERSION == 7
```

Update the `data["receipt_version"] == 6` assertion (line ~191) to `== 7`. Then add:

```python
def test_receipt_has_cost_per_quality_column_and_field():
    report = _sample_report()  # reuse the module's existing report builder/fixture
    md = export.to_markdown(report)
    html = export.to_html(report)
    assert "$ / quality" in md
    assert "$ / quality" in html
    # Mock winner has cost 0 with real quality -> "Free" in every format.
    assert "Free" in md
    json_out = export.to_json(report)
    assert '"cost_per_quality"' in json_out
```

> If the test module builds its report inline rather than via a helper named `_sample_report`, mirror that module's existing pattern to construct `report` (see the `LeaderboardEntry(...)` construction around line 177) and pass `cost_per_quality=0.0` on the winning entry so "Free" is asserted.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_receipts.py -k "version_is_7 or cost_per_quality" -v`
Expected: FAIL — `RECEIPT_VERSION == 7` fails (still 6) and `"$ / quality"` not found.

- [ ] **Step 3: Bump the version + add the shared display helper**

In `src/orionfold/receipts/export.py`, change line 25 and add a comment line above it:

```python
# v7: leaderboard entries carry a `cost_per_quality` field ($ per quality point); the receipt
# adds a "$ / quality" efficiency column. Presentation only — ranking is unchanged.
# Bump on any schema change so downstream consumers can detect drift.
RECEIPT_VERSION = 7
```

Add a helper near `_failures_label` (after line 55):

```python
def _cost_per_quality_label(v: float | None) -> str:
    """Display rule for the $/quality efficiency cell, shared by MD and HTML."""
    if v is None:
        return "—"
    if v == 0:
        return "Free"
    return f"${v:.4f}"
```

- [ ] **Step 4: Add the column to Markdown**

In `to_markdown`, replace the two header lines (177-178) with:

```python
        "| Candidate | Provider | Privacy | Pass rate | $ / quality | Avg score | Avg latency | Est. cost | Failures |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
```

In the row loop (182-187), insert the `$ / quality` cell after the pass-rate cell:

```python
        lines.append(
            f"| {_md_cell(e['label'])}{marker} | {_md_cell(e['provider_id'])} | "
            f"{_md_cell(e['privacy'])} | "
            f"{e['pass_rate']:.0%} ({e['pass_count']}/{e['total']}) | "
            f"{_cost_per_quality_label(e['cost_per_quality'])} | {e['avg_score']:.2f} | "
            f"{e['avg_latency_ms']}ms | ${e['total_estimated_cost_usd']:.2f} | {_failures_label(e)} |"
        )
```

- [ ] **Step 5: Add the column to HTML**

In `to_html`, in the `rows` join (234-246), insert the `$ / quality` `<td>` after the pass-rate `<td>`:

```python
        f"<td>{e['pass_rate']:.0%} ({e['pass_count']}/{e['total']})</td>"
        f"<td>{html.escape(_cost_per_quality_label(e['cost_per_quality']))}</td>"
        f"<td>{e['avg_score']:.2f}</td>"
```

And add the matching `<th>` in the `<thead>` (348-349):

```python
      <th>Candidate</th><th>Provider</th><th>Privacy</th><th>Pass rate</th>
      <th>$ / quality</th>
      <th>Avg score</th><th>Avg latency</th><th>Est. cost</th><th>Failures</th>
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_receipts.py -v`
Expected: PASS. Then run the full no-winner receipt test and grep for any other hardcoded version:

```bash
grep -rn "version_is_6\|receipt_version.*6\|== 6" tests/unit/test_receipt_no_winner.py tests/unit/test_receipts.py
uv run pytest tests/unit/test_receipt_no_winner.py -v
```
Expected: no stray `6` version assertions remain; no-winner tests PASS. Fix any found (flip 6 → 7).

- [ ] **Step 7: Regenerate sample receipts**

Run: `uv run python scripts/gen_samples.py`
Then inspect the diff:

```bash
git diff --stat samples/
git diff samples/ | grep -E "receipt_version|cost_per_quality|\\$ / quality" | head
```
Expected: every leaderboard entry gains `cost_per_quality`; `receipt_version` is 7; the MD/HTML samples show the `$ / quality` column. The bundled winner (`mock_good`, cost $0.00) shows "Free".

- [ ] **Step 8: Commit**

```bash
git add src/orionfold/receipts/export.py tests/unit/test_receipts.py tests/unit/test_receipt_no_winner.py samples/
git commit -m "feat(receipt): \$/quality column + RECEIPT_VERSION 7"
```

---

### Task 3: Frontend — schema field + pure presentation helpers

**Files:**
- Modify: `web/src/lib/api.ts:95-111` (add `cost_per_quality` to the Zod schema)
- Create: `web/src/features/proof/leaderboardFormat.ts`
- Test: `web/src/features/proof/leaderboardFormat.test.ts`

**Interfaces:**
- Produces:
  - `passRateTone(passRate: number): "ok" | "warn" | "danger"`
  - `formatCostPerQuality(v: number | null | undefined): string`
  - `medalFor(index: number, hasWinner: boolean): string | null`
  - `LeaderboardEntry.cost_per_quality?: number | null` (inferred from the schema)

- [ ] **Step 1: Write the failing tests**

Create `web/src/features/proof/leaderboardFormat.ts` with only the type exports so imports resolve, then write `web/src/features/proof/leaderboardFormat.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import { formatCostPerQuality, medalFor, passRateTone } from "./leaderboardFormat";

describe("passRateTone (traffic-light on pass rate)", () => {
  test("green at >= 0.8", () => expect(passRateTone(0.8)).toBe("ok"));
  test("amber in [0.5, 0.8)", () => expect(passRateTone(0.6)).toBe("warn"));
  test("red below 0.5", () => expect(passRateTone(0.2)).toBe("danger"));
});

describe("formatCostPerQuality", () => {
  test("null -> em dash", () => expect(formatCostPerQuality(null)).toBe("—"));
  test("undefined -> em dash", () => expect(formatCostPerQuality(undefined)).toBe("—"));
  test("zero -> Free", () => expect(formatCostPerQuality(0)).toBe("Free"));
  test("value -> 4-decimal dollars", () => expect(formatCostPerQuality(0.004)).toBe("$0.0040"));
});

describe("medalFor", () => {
  test("podium medals only when a winner exists", () => {
    expect(medalFor(0, true)).toBe("🥇");
    expect(medalFor(1, true)).toBe("🥈");
    expect(medalFor(2, true)).toBe("🥉");
    expect(medalFor(3, true)).toBeNull();
  });
  test("no medals in the no-winner state", () => {
    expect(medalFor(0, false)).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm --dir web test leaderboardFormat -- --run`
Expected: FAIL — `formatCostPerQuality`/`medalFor`/`passRateTone` not exported.

- [ ] **Step 3: Implement the helpers**

Write `web/src/features/proof/leaderboardFormat.ts`:

```ts
// Pure presentation helpers for the leaderboard — unit-tested without rendering, so the
// thresholds and the $/quality display rule live in exactly one place.

// Traffic-light tone for a pass rate (0–1), mapped to STATUS tokens (never the cyan accent).
export type PassRateTone = "ok" | "warn" | "danger";

export function passRateTone(passRate: number): PassRateTone {
  if (passRate >= 0.8) return "ok";
  if (passRate >= 0.5) return "warn";
  return "danger";
}

// $/quality cell text: null/undefined → "—" (no quality to price), 0 → "Free" (local/mock),
// else "$0.0012" to 4 decimals. Mirrors the receipt's _cost_per_quality_label exactly.
export function formatCostPerQuality(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (v === 0) return "Free";
  return `$${v.toFixed(4)}`;
}

// Podium medal for a 0-based row index, only when a real winner exists; otherwise null.
export function medalFor(index: number, hasWinner: boolean): string | null {
  if (!hasWinner) return null;
  return ["🥇", "🥈", "🥉"][index] ?? null;
}
```

- [ ] **Step 4: Add the schema field**

In `web/src/lib/api.ts`, add to `leaderboardEntrySchema` (after `recommended: z.boolean(),`, line 110):

```ts
  recommended: z.boolean(),
  cost_per_quality: z.number().nullable().optional(),
```

(`.nullable().optional()` mirrors `model`/`system_prompt`, so receipts that predate v7 still parse.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `pnpm --dir web test leaderboardFormat -- --run`
Expected: PASS. Then `pnpm --dir web exec tsc --noEmit` — clean.

- [ ] **Step 6: Commit**

```bash
git add web/src/lib/api.ts web/src/features/proof/leaderboardFormat.ts web/src/features/proof/leaderboardFormat.test.ts
git commit -m "feat(leaderboard): cost_per_quality schema + pure format helpers"
```

---

### Task 4: Frontend — leaderboard table (rank/medals, score bar, `$ / quality`)

**Files:**
- Modify: `web/src/features/proof/Leaderboard.tsx`
- Modify: `web/src/test/fixtures.ts` (add `cost_per_quality` to entries)
- Test: `web/src/features/proof/Leaderboard.test.tsx` (new)

**Interfaces:**
- Consumes: `passRateTone`, `formatCostPerQuality`, `medalFor` (Task 3); `LeaderboardEntry.cost_per_quality` (Task 3).

- [ ] **Step 1: Add `cost_per_quality` to the shared fixtures**

In `web/src/test/fixtures.ts`, add `cost_per_quality` to each leaderboard entry:
- `SAMPLE_REPORT` winner (line ~37): add `cost_per_quality: 0,` after `recommended: true,`.
- `NO_WINNER_REPORT` `real` entry (line ~52): add `cost_per_quality: 0,`.
- `NO_WINNER_REPORT` `erro` entry (line ~58): add `cost_per_quality: null,`.

- [ ] **Step 2: Write the failing tests**

Create `web/src/features/proof/Leaderboard.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { Leaderboard } from "./Leaderboard";
import type { LeaderboardEntry } from "../../lib/api";

function entry(over: Partial<LeaderboardEntry>): LeaderboardEntry {
  return {
    candidate_id: "c", label: "Cand", provider_id: "ollama", privacy: "local",
    total: 5, pass_count: 4, pass_rate: 0.8, avg_score: 0.8, avg_latency_ms: 100,
    total_estimated_cost_usd: 0.01, failure_count: 1, error_count: 0,
    recommended: false, cost_per_quality: 0.0125, ...over,
  };
}

test("medals decorate the top 3 only when a winner exists", () => {
  const entries = [
    entry({ candidate_id: "a", recommended: true, pass_rate: 1, pass_count: 5, failure_count: 0 }),
    entry({ candidate_id: "b" }),
    entry({ candidate_id: "c" }),
    entry({ candidate_id: "d" }),
  ];
  render(<Leaderboard entries={entries} />);
  expect(screen.getByText("🥇")).toBeInTheDocument();
  expect(screen.getByText("🥈")).toBeInTheDocument();
  expect(screen.getByText("🥉")).toBeInTheDocument();
});

test("no medals in the no-winner state — plain rank numbers", () => {
  const entries = [
    entry({ candidate_id: "a", recommended: false, pass_rate: 0.2, pass_count: 1, failure_count: 4 }),
    entry({ candidate_id: "b", recommended: false }),
  ];
  const { container } = render(<Leaderboard entries={entries} />);
  expect(container.textContent).not.toContain("🥇");
  expect(screen.getByText("1")).toBeInTheDocument();
  expect(screen.getByText("2")).toBeInTheDocument();
});

test("score bar uses the traffic-light status token for the pass rate", () => {
  const { container } = render(
    <Leaderboard entries={[entry({ pass_rate: 0.2, pass_count: 1, failure_count: 4 })]} />,
  );
  // A <0.5 pass rate paints the bar danger — a status token, never the accent.
  expect(container.innerHTML).toContain("bg-(--color-danger)");
  expect(container.innerHTML).not.toContain("--color-accent");
});

test("$/quality cell renders Free / em-dash / value", () => {
  render(
    <Leaderboard
      entries={[
        entry({ candidate_id: "free", cost_per_quality: 0 }),
        entry({ candidate_id: "none", cost_per_quality: null }),
        entry({ candidate_id: "paid", cost_per_quality: 0.004 }),
      ]}
    />,
  );
  expect(screen.getByText("Free")).toBeInTheDocument();
  expect(screen.getByText("—")).toBeInTheDocument();
  expect(screen.getByText("$0.0040")).toBeInTheDocument();
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pnpm --dir web test Leaderboard.test -- --run`
Expected: FAIL — no medals/bar token/`$0.0040` rendered yet.

- [ ] **Step 4: Implement the table changes**

Rewrite `web/src/features/proof/Leaderboard.tsx`:

```tsx
import { BadgeCheck } from "lucide-react";

import type { LeaderboardEntry } from "../../lib/api";
import { ProviderTag } from "./badges";
import { formatCostPerQuality, medalFor, passRateTone, type PassRateTone } from "./leaderboardFormat";

// Bar fill per traffic-light tone — STATUS tokens only (never the cyan accent).
const TONE_BAR: Record<PassRateTone, string> = {
  ok: "bg-(--color-ok)",
  warn: "bg-(--color-warn)",
  danger: "bg-(--color-danger)",
};

// The leaderboard is the verdict: who to trust, ranked. The recommended row is highlighted
// so the decision reads at a glance — a calm instrument panel, not a wall of metrics.
export function Leaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  const hasWinner = entries.some((e) => e.recommended);
  return (
    <section aria-label="Leaderboard" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
        Leaderboard
      </h2>
      <div className="overflow-x-auto rounded-xl border border-(--color-panel-line)">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left text-(--color-ink-faint)">
              <th className="p-3 font-medium">#</th>
              <th className="p-3 font-medium">Candidate</th>
              <th className="p-3 font-medium">Provider</th>
              <th className="p-3 font-medium">Pass rate</th>
              <th className="p-3 font-medium">$ / quality</th>
              <th className="p-3 font-medium">Avg score</th>
              <th className="p-3 font-medium">Avg latency</th>
              <th className="p-3 font-medium">Est. cost</th>
              <th className="p-3 font-medium">Failures</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr
                key={e.candidate_id}
                className={
                  "border-t border-(--color-panel-line) " +
                  (e.recommended ? "bg-(--color-accent)/[0.08]" : "")
                }
              >
                <td className="p-3 tabular-nums text-(--color-ink-muted)">
                  {medalFor(i, hasWinner) ?? i + 1}
                </td>
                <td className="p-3">
                  {e.label}
                  {e.recommended && (
                    <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-(--color-accent)/20 px-2 py-0.5 text-xs text-(--color-accent)">
                      <BadgeCheck aria-hidden className="h-3 w-3 shrink-0" />
                      Recommended
                    </span>
                  )}
                </td>
                <td className="p-3">
                  <ProviderTag candidate={e} />
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-(--color-panel-line)">
                      <div
                        className={"h-full rounded-full " + TONE_BAR[passRateTone(e.pass_rate)]}
                        style={{ width: `${Math.round(e.pass_rate * 100)}%` }}
                      />
                    </div>
                    <span className="tabular-nums">
                      {Math.round(e.pass_rate * 100)}% ({e.pass_count}/{e.total})
                    </span>
                  </div>
                </td>
                <td className="p-3 tabular-nums">{formatCostPerQuality(e.cost_per_quality)}</td>
                <td className="p-3">{e.avg_score.toFixed(2)}</td>
                <td className="p-3">{e.avg_latency_ms}ms</td>
                <td className="p-3">${e.total_estimated_cost_usd.toFixed(2)}</td>
                <td className="p-3">
                  {e.failure_count}
                  {e.total > 0 && e.error_count === e.total && (
                    <span className="ml-1 text-(--color-ink-faint)">(errored, no output)</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pnpm --dir web test Leaderboard.test -- --run`
Expected: PASS. Then `pnpm --dir web exec tsc --noEmit` — clean. Run the existing view tests to confirm no regression: `pnpm --dir web test DecisionSummary -- --run`.

- [ ] **Step 6: Commit**

```bash
git add web/src/features/proof/Leaderboard.tsx web/src/features/proof/Leaderboard.test.tsx web/src/test/fixtures.ts
git commit -m "feat(leaderboard): rank+medals, traffic-light pass-rate bar, \$/quality column"
```

---

### Task 5: Frontend — strengthen the local privacy tag

**Files:**
- Modify: `web/src/features/proof/badges.tsx:1-41`
- Test: `web/src/features/proof/badges.test.tsx` (extend)

**Interfaces:**
- Consumes/Produces: `ProviderTag` — same props, restyled `local` variant (lock glyph + stronger neutral ink). `cloud`/`mock` unchanged.

- [ ] **Step 1: Write the failing test**

Append to `web/src/features/proof/badges.test.tsx`:

```tsx
test("local provider tag is strengthened (stronger neutral ink) without green or the accent", () => {
  // 'Local & private' is the product promise — the local tag reads more prominently than cloud,
  // but green is reserved for PASS status and cyan for controls, so neither appears here.
  const { container } = render(
    <ProviderTag candidate={{ provider_id: "ollama", privacy: "local" }} />,
  );
  const el = container.querySelector("span")!;
  expect(el.className).toContain("text-(--color-ink)");
  expect(el.className).toContain("font-semibold");
  expect(el.className).not.toContain("--color-ok");
  expect(el.className).not.toContain("accent");
  // Still the neutral receipt-stub shape, not a pill.
  expect(el.className).toContain("rounded");
  expect(el.className).not.toContain("rounded-full");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test badges.test -- --run`
Expected: FAIL — local tag currently uses `text-(--color-ink-muted)`, no `font-semibold`.

- [ ] **Step 3: Implement the strengthened local variant**

In `web/src/features/proof/badges.tsx`, change the `lucide-react` import (line 2) to swap in `Lock`:

```tsx
import { Cloud, CircleX, FlaskConical, HardDrive, Lock, TriangleAlert, type LucideIcon } from "lucide-react";
```

Give each kind an explicit class and use a lock glyph for local (replace `PROVIDER_STYLE`, lines 19-23):

```tsx
const PROVIDER_STYLE: Record<ProviderKind, { label: string; Icon: LucideIcon; cls: string }> = {
  // Cloud/Mock stay neutral & muted. Local is strengthened — stronger neutral ink + a lock glyph
  // — so 'local & private' reads at a glance. No green (PASS-only) and no cyan accent (controls-only).
  mock: { label: "Mock", Icon: FlaskConical, cls: "text-(--color-ink-muted)" },
  local: { label: "Local", Icon: Lock, cls: "text-(--color-ink) font-semibold" },
  cloud: { label: "Cloud", Icon: Cloud, cls: "text-(--color-ink-muted)" },
};
```

Update the destructure + span `className` (lines 30-36) to apply `cls` and drop the now-duplicated `text-(--color-ink-muted)` from the base:

```tsx
  const { label, Icon, cls } = PROVIDER_STYLE[providerKind(candidate.provider_id, candidate.privacy)];
  return (
    <span
      // `rounded` (not a pill): identity tags take the receipt-stub shape so they never read as
      // interactive. Local is strengthened via per-kind `cls`; cloud/mock stay neutral ink-muted.
      className={`inline-flex items-center gap-1 rounded border border-(--color-panel-line) bg-(--color-panel-card) px-2 py-0.5 text-[11px] font-medium ${cls}`}
    >
```

> Note: `HardDrive` is no longer used. Remove it from the import to keep the lint clean.

Final import line:

```tsx
import { Cloud, CircleX, FlaskConical, Lock, TriangleAlert, type LucideIcon } from "lucide-react";
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test badges.test -- --run`
Expected: PASS (new + the existing cloud-based "neutral, not a pill" test, which still sees `text-(--color-ink-muted)` on the cloud tag). Then `pnpm --dir web exec tsc --noEmit` — clean (no unused `HardDrive`).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/badges.tsx web/src/features/proof/badges.test.tsx
git commit -m "feat(badges): strengthen the local privacy tag (lock glyph + stronger ink)"
```

---

### Task 6: Verification gate (visual + receipt quality + full suites)

**Files:** none modified unless a defect is found (then fix + re-run the owning task's tests).

- [ ] **Step 1: Full backend + frontend suites + types**

```bash
uv run pytest -q
uv run ruff check src tests
uv run pyright src/orionfold/receipts/export.py src/orionfold/proof/leaderboard.py src/orionfold/domain/models.py
pnpm --dir web test -- --run
pnpm --dir web exec tsc --noEmit
```
Expected: all green. Confirm `config_hash` is untouched: `grep -rn "467ddd96c9a5" tests samples | head` still matches (the sample receipts' hash did not change — only `cost_per_quality`/`receipt_version` did).

- [ ] **Step 2: Browser visual verification (`browser-visual-verification` skill)**

Build + render the leaderboard, screenshot a **winner** run and a **no-winner** run. Confirm against the design: medals 🥇🥈🥉 only when a winner exists; the pass-rate bar color matches the tone (green ≥0.8 / amber ≥0.5 / red <0.5); the `$ / quality` column reads "Free"/"—"/`$…`; the local tag is clearly more prominent than cloud — and the whole thing still reads calm, not a noisy dashboard. Build note from HANDOFF: for the embedded path run `bash scripts/build.sh` first; or live source via `pnpm --dir web dev` proxied to the running API (`:8790` here; `:8787` may be occupied).

- [ ] **Step 3: Receipt quality review (`receipt-quality-review` skill)**

Receipt structure changed, so run the skill: generate a sample receipt, inspect the new `$ / quality` column in Markdown/HTML/JSON, confirm **no secrets**, confirm the column reads clearly and the receipt stays client-shareable, and confirm `receipt_version` is 7.

- [ ] **Step 4: Playwright smoke + worklog/handoff**

```bash
bash scripts/build.sh
# run the existing leaderboard/receipt Playwright smoke (per the repo's e2e setup)
```
Then append a `docs/worklog/2026-06-22-leaderboard-presentation.md` entry (Summary · Verification · Product impact · Risks · Next step) and overwrite `HANDOFF.md` to point at sub-project 3 (Quick-Compare). Commit:

```bash
git add docs/worklog/ HANDOFF.md
git commit -m "docs: leaderboard presentation worklog + handoff to sub-project 3"
```

---

## Self-Review

**Spec coverage:**
- Rank column + top-3 medals → Task 4 (`medalFor`, rank cell). ✓
- Traffic-light pass-rate score bar → Task 3 (`passRateTone`) + Task 4 (`TONE_BAR`, bar markup). ✓
- `$/quality` stored + in receipt, `RECEIPT_VERSION` 6→7 → Task 1 (field/compute) + Task 2 (MD/HTML/JSON + version). ✓
- `$/quality` on screen → Task 3 (`formatCostPerQuality`) + Task 4 (column). ✓
- Strengthen per-row local badge → Task 5. ✓
- Ranking unchanged / `config_hash` held → Task 1 (`test_cost_per_quality_does_not_change_ranking`), Task 6 Step 1 grep. ✓
- No-winner state respected → Task 4 (`hasWinner` gate + test). ✓
- Sample regen → Task 2 Step 7. ✓
- Deferred (sort toggle, Pareto scatter) → not built. ✓

**Placeholder scan:** No TBD/TODO; every code step shows full code. The one conditional (Task 2 Step 1's `_sample_report` note) gives an explicit fallback. ✓

**Type consistency:** `cost_per_quality` is `float | None` (Py) / `number | null | undefined` (TS) everywhere; the display rule (`None/null/undefined → "—"`, `0 → "Free"`, else 4-dp `$`) is identical in `_cost_per_quality_label` and `formatCostPerQuality`; `passRateTone` returns `"ok"|"warn"|"danger"` consumed by `TONE_BAR`; `medalFor(index, hasWinner)` matches its Task 4 call site. ✓
