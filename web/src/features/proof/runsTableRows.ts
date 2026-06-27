// Pure row model + sort for the Receipts Runs table (Slice 4) — kept out of the component so the
// mode-specific verdict resolution and ordering are unit-tested in one place.
//
// The Runs table replaces the old tall ReceiptCard list with a compact, scannable, sortable table.
// Each row distils one ProofReport to its takeaway. The verdict is MODE-SPECIFIC (a hard invariant):
// a full run reads `leaderboard.recommended` ("Mock · good — 100%"); a quick run reads
// `run.chosen_winner` resolved against `run.candidates` ("Picked …" / "Tie"). We never collapse a
// quick run onto the `recommended` path — nothing is ever recommended in an unscored run.

import type { ProofReport } from "../../lib/api";

// A "tie" / no-winner reads as a verdict with no candidate; the table shows the text only.
export interface RunRow {
  runId: string;
  heading: string; // decision question or task name
  isSample: boolean; // seeded sample receipts (run_sample…) get a badge
  isQuick: boolean; // quick-compare (unscored) runs
  // Verdict — the one-glance outcome. `label` is the winning candidate's name (null for a tie /
  // no clear winner); `passText` is "5/5" for scored full runs (null otherwise); `verb` is the
  // mode word ("Winner" / "Picked" / "Tie" / "No clear winner").
  verb: "Winner" | "Picked" | "Tie" | "No clear winner";
  winnerLabel: string | null;
  winnerProviderId: string | null;
  winnerPrivacy: "local" | "cloud" | null;
  passRate: number | null; // 0–1 for scored full runs; null for quick / no-winner (sorts last)
  passText: string | null; // "5/5" for scored full runs
  scoredBy: string; // human label of the rubric kind
  datasetName: string;
  costUsd: number; // run total spend (candidate + judge)
  createdAt: string; // ISO string, rendered as-is (matches the old card)
  configHash: string;
}

// The rubric-kind → human label, mirroring `scoredByLabel` but taking only the kind (the table
// shows the family, not the judge model, to stay compact). Quick runs are "Quick check".
const SCORED_BY: Record<string, string> = {
  exact: "Exact match",
  contains: "Contains",
  similarity: "Similarity",
  keypoint: "Keypoint",
  judge: "LLM judge",
  bench: "Governance bench",
  none: "Quick check",
};

export function toRunRow(report: ProofReport): RunRow {
  const { run } = report;
  const isQuick = run.mode === "quick";
  const heading = run.brief.decision_question || run.brief.task_name;
  const base = {
    runId: run.id,
    heading,
    isSample: run.id.startsWith("run_sample"),
    isQuick,
    datasetName: run.dataset_name,
    costUsd: report.cost_summary.total_cost_usd,
    createdAt: run.created_at,
    configHash: run.config_hash,
    scoredBy: SCORED_BY[run.rubric.kind] ?? run.rubric.kind,
  };

  if (isQuick) {
    // A quick run's verdict is the human pick on chosen_winner (candidate id, "tie", or null).
    if (run.chosen_winner === "tie") {
      return { ...base, verb: "Tie", winnerLabel: null, winnerProviderId: null, winnerPrivacy: null, passRate: null, passText: null };
    }
    const picked = run.chosen_winner
      ? run.candidates.find((c) => c.id === run.chosen_winner)
      : undefined;
    if (picked) {
      return {
        ...base, verb: "Picked", winnerLabel: picked.label, winnerProviderId: picked.provider_id,
        winnerPrivacy: picked.privacy, passRate: null, passText: null,
      };
    }
    // An un-picked quick draft (chosen_winner null) — list_runs hides these, but be defensive.
    return { ...base, verb: "No clear winner", winnerLabel: null, winnerProviderId: null, winnerPrivacy: null, passRate: null, passText: null };
  }

  // Full run: the verdict is the recommended leaderboard entry.
  const winner = report.leaderboard.find((e) => e.recommended);
  if (winner) {
    return {
      ...base, verb: "Winner", winnerLabel: winner.label, winnerProviderId: winner.provider_id,
      winnerPrivacy: winner.privacy, passRate: winner.pass_rate,
      passText: `${winner.pass_count}/${winner.total}`,
    };
  }
  return { ...base, verb: "No clear winner", winnerLabel: null, winnerProviderId: null, winnerPrivacy: null, passRate: null, passText: null };
}

// Sortable columns of the Runs table. The default (column: null) preserves the server order
// (getRuns returns newest-first), which is the meaningful default — most-recent proof on top.
export type RunSortColumn = "heading" | "passRate" | "costUsd" | "createdAt";
export type SortDirection = "asc" | "desc";

export interface RunSortState {
  column: RunSortColumn | null;
  direction: SortDirection;
}

export const DEFAULT_RUN_SORT: RunSortState = { column: null, direction: "desc" };

// First-click direction per column: time/cost newest/cheapest-first reads naturally desc/asc;
// pass-rate best-first desc; heading A→Z asc.
const FIRST_CLICK: Record<RunSortColumn, SortDirection> = {
  heading: "asc",
  passRate: "desc",
  costUsd: "asc",
  createdAt: "desc",
};

export function nextRunSort(current: RunSortState, column: RunSortColumn): RunSortState {
  if (current.column === column) {
    return { column, direction: current.direction === "asc" ? "desc" : "asc" };
  }
  return { column, direction: FIRST_CLICK[column] };
}

// A null passRate (quick / no-winner) always sorts to the BOTTOM regardless of direction — it has
// no comparable quality value, so it should never out-rank a real one.
function compare(a: RunRow, b: RunRow, column: RunSortColumn): number {
  if (column === "heading") return a.heading.localeCompare(b.heading);
  if (column === "createdAt") return a.createdAt.localeCompare(b.createdAt);
  if (column === "costUsd") return a.costUsd - b.costUsd;
  // passRate, null-last
  const av = a.passRate;
  const bv = b.passRate;
  if (av == null && bv == null) return 0;
  if (av == null) return 1;
  if (bv == null) return -1;
  return av - bv;
}

// `aria-sort` value for a column header given the active sort — mirrors leaderboardSort's helper.
export function ariaSortFor(column: RunSortColumn, sort: RunSortState): "none" | "ascending" | "descending" {
  if (sort.column !== column) return "none";
  return sort.direction === "asc" ? "ascending" : "descending";
}

export function sortRunRows(rows: ReadonlyArray<RunRow>, sort: RunSortState): RunRow[] {
  if (sort.column === null) return rows as RunRow[];
  const col = sort.column;
  const dir = sort.direction === "asc" ? 1 : -1;
  // null-last entries (passRate) must stay last in BOTH directions, so apply direction only to the
  // comparable portion: a fixed +1/-1 from compare() for nulls is NOT flipped.
  return [...rows].sort((a, b) => {
    const raw = compare(a, b, col);
    if (col === "passRate") {
      const aNull = a.passRate == null;
      const bNull = b.passRate == null;
      if (aNull || bNull) return raw; // null-last, direction-independent
    }
    return raw * dir;
  });
}
