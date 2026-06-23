// Pure client-side sort for the leaderboard table (WS-F F2) — kept out of the component so the
// ordering rules are unit-tested in one place.
//
// The leaderboard arrives already ranked by the server's documented key
// (`_all_errored, -pass_rate, -avg_score, avg_latency_ms, total_estimated_cost_usd`). That ranking
// is the verdict, so it is the DEFAULT on load (`column: null`): the rows render in the order given,
// the recommended row is highlighted, and the podium medals are meaningful. A user can then click a
// header to *explore* a single dimension; doing so leaves the verdict order and enters a transient
// sort, which is why medals are suppressed once a column is active (see `Leaderboard.tsx`).

import type { LeaderboardEntry } from "../../lib/api";

// Only columns with a meaningful scalar order are sortable. The rank (`#`) and Provider (identity)
// columns are not — Provider is categorical identity, and `#` reflects the server ranking itself.
export type SortColumn =
  | "label"
  | "pass_rate"
  | "cost_per_quality"
  | "avg_score"
  | "avg_latency_ms"
  | "total_estimated_cost_usd"
  | "failure_count";

export type SortDirection = "asc" | "desc";

export interface SortState {
  // `null` = the server's default ranking (rows as given). Any column = a transient explore sort.
  column: SortColumn | null;
  direction: SortDirection;
}

export const DEFAULT_SORT: SortState = { column: null, direction: "desc" };

// Most metrics read "best first" descending (higher pass rate / avg score first); cost, latency,
// failures, and $/quality read "best first" ascending (cheaper / faster / fewer / better value
// first), and the label sorts A→Z. This is the direction a *first* click on a header applies; a
// second click flips it.
const FIRST_CLICK_DIRECTION: Record<SortColumn, SortDirection> = {
  label: "asc",
  pass_rate: "desc",
  cost_per_quality: "asc",
  avg_score: "desc",
  avg_latency_ms: "asc",
  total_estimated_cost_usd: "asc",
  failure_count: "asc",
};

// Click handling: a fresh column adopts its natural first-click direction; clicking the active
// column flips direction. (We never cycle back to the unsorted default via clicks — the explicit
// reset path can do that if ever needed; keeping clicks simple matches the reference.)
export function nextSort(current: SortState, column: SortColumn): SortState {
  if (current.column === column) {
    return { column, direction: current.direction === "asc" ? "desc" : "asc" };
  }
  return { column, direction: FIRST_CLICK_DIRECTION[column] };
}

// A nullish `cost_per_quality` (no quality to price) always sorts to the BOTTOM regardless of
// direction — it has no comparable value, so it should never out-rank a real number.
function compareValues(a: LeaderboardEntry, b: LeaderboardEntry, column: SortColumn): number {
  if (column === "label") {
    return a.label.localeCompare(b.label);
  }
  if (column === "cost_per_quality") {
    const av = a.cost_per_quality;
    const bv = b.cost_per_quality;
    const aNull = av === null || av === undefined;
    const bNull = bv === null || bv === undefined;
    if (aNull && bNull) return 0;
    if (aNull) return 1; // a after b
    if (bNull) return -1; // a before b
    return av - bv;
  }
  return a[column] - b[column];
}

// Stable sort that preserves the server ranking as the tiebreak: equal cells keep their given
// order, so a sort never scrambles otherwise-tied rows. `column: null` returns the input order
// untouched (the default ranking).
export function sortEntries(entries: LeaderboardEntry[], sort: SortState): LeaderboardEntry[] {
  if (sort.column === null) return entries;
  const column = sort.column;
  const factor = sort.direction === "asc" ? 1 : -1;
  return entries
    .map((entry, index) => ({ entry, index }))
    .sort((a, b) => {
      // Null $/quality stays at the bottom irrespective of direction — undo the factor for it.
      if (column === "cost_per_quality") {
        const raw = compareValues(a.entry, b.entry, column);
        const aNull = a.entry.cost_per_quality === null || a.entry.cost_per_quality === undefined;
        const bNull = b.entry.cost_per_quality === null || b.entry.cost_per_quality === undefined;
        if (aNull || bNull) return raw; // already returns +1/-1/0 with a-after-b for nulls
        return factor * raw || a.index - b.index;
      }
      return factor * compareValues(a.entry, b.entry, column) || a.index - b.index;
    })
    .map(({ entry }) => entry);
}

// `aria-sort` value for a header given the current sort state.
export function ariaSortFor(column: SortColumn, sort: SortState): "none" | "ascending" | "descending" {
  if (sort.column !== column) return "none";
  return sort.direction === "asc" ? "ascending" : "descending";
}
