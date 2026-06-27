// Pure shaping for the Receipts bento masthead (Slice 4) — kept out of the component so the
// tile-value derivation and the trend-chart series are unit-tested without rendering.
//
// The bento reads three sources: getRuns() (the receipts archive, newest-first), and the two cost
// rollups (today / all). Everything here is a presentation-only projection of those — no scoring,
// no new source of truth.

import type { CostRollup, CostTrendPoint, ProofReport } from "../../lib/api";
import { toRunRow, type RunRow } from "./runsTableRows";

// The "Latest proof" tile: the most recent receipt distilled to its verdict row, plus a count of
// how many runs total. Null when there are no runs yet (the tile shows an empty state).
export interface LatestProof {
  row: RunRow;
  totalRuns: number;
}

// getRuns() returns newest-first (server order); the head is the latest proof. We reuse the Runs
// table's row model so the tile's verdict matches the table exactly (one resolution path).
export function latestProof(runs: ReadonlyArray<ProofReport>): LatestProof | null {
  if (runs.length === 0) return null;
  return { row: toRunRow(runs[0]), totalRuns: runs.length };
}

// One point on the masthead trend chart. The cost rollup's trend is oldest-first already (so a
// left→right line reads chronologically); we keep that order and add a short axis label.
export interface TrendChartPoint {
  runId: string;
  // A compact axis tick — the date portion of the ISO created_at (YYYY-MM-DD → "MM-DD"). The full
  // timestamp stays available via the tooltip's payload if needed.
  label: string;
  passRatePct: number; // 0–100 for the left (quality) axis
  costUsd: number; // right (spend) axis
}

// "2026-06-27T09:00:00Z" → "06-27". Defensive: if the string isn't an ISO date, fall back to the
// raw value so a malformed timestamp still labels something rather than throwing.
function axisLabel(createdAt: string): string {
  const m = /^\d{4}-(\d{2})-(\d{2})/.exec(createdAt);
  return m ? `${m[1]}-${m[2]}` : createdAt;
}

export function trendChartData(trend: ReadonlyArray<CostTrendPoint>): TrendChartPoint[] {
  return trend.map((p) => ({
    runId: p.run_id,
    label: axisLabel(p.created_at),
    passRatePct: Math.round(p.pass_rate * 100),
    costUsd: p.total_cost_usd,
  }));
}

// The cost-today tile's split sub-line: "eval + judge". Omitted (null) when there's no judge
// spend — the common deterministic-scoring case stays calm. Mirrors the rail's costSplitSub so the
// two surfaces read identically.
export function costSplitLine(roll: CostRollup): string | null {
  if (roll.judge_cost_usd === 0) return null;
  return `$${roll.eval_cost_usd.toFixed(2)} eval + $${roll.judge_cost_usd.toFixed(2)} judge`;
}

// USD for the bento tiles: cents under $10 (so a $0.02 judge cost doesn't vanish), whole dollars
// above. A loaded $0 reads "$0.00" (a real all-local spend), never "—".
export function formatUsd(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 10) return `$${usd.toFixed(2)}`;
  return `$${Math.round(usd)}`;
}
