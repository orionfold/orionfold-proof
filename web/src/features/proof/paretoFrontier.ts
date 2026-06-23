// Pareto frontier math for the cost-vs-quality scatter — pure, unit-tested, no React.
//
// Adapted from the Arena FrontierScatter skyline, REORIENTED: Arena plots
// throughput×quality where higher-x is better, so its sweep keeps points that
// beat every higher-x point on quality. Here X is COST, where LOWER is better —
// so a candidate is Pareto-optimal iff no OTHER candidate is at least as cheap
// AND at least as good (and not identical). The recommended candidate is whatever
// the leaderboard already chose; we never re-derive it here.

import type { LeaderboardEntry } from "../../lib/api";

export interface ScatterPoint {
  candidateId: string;
  label: string;
  cost: number; // x — total estimated $, lower is better
  quality: number; // y — pass rate 0–1, higher is better
  recommended: boolean;
  onFrontier: boolean;
}

// Indices (into the given array) of the Pareto-optimal points for a
// lower-cost-is-better × higher-quality-is-better space.
//
// A point i is dominated iff some other point j has cost_j <= cost_i AND
// quality_j >= quality_i with at least one inequality strict. Equivalently:
// sort by cost ascending (quality descending to break cost ties), sweep, and
// keep a point only when its quality strictly exceeds the best quality seen
// among all strictly-cheaper points. Equal-cost points are resolved as a group
// so a tie on cost doesn't spuriously drop the higher-quality one.
export function paretoFrontier(pts: ReadonlyArray<{ cost: number; quality: number }>): Set<number> {
  const order = pts
    .map((_, i) => i)
    .sort((a, b) => pts[a].cost - pts[b].cost || pts[b].quality - pts[a].quality);

  const onFrontier = new Set<number>();
  // Best quality among all points strictly cheaper than the current cost tier.
  let bestQualityStrictlyCheaper = -Infinity;
  let tierCost = NaN;
  let tierMembers: number[] = [];
  let tierBest = -Infinity;

  // Walk cost-ascending, one cost tier at a time. A point is Pareto-optimal iff
  // it ties the best quality in its own tier (nothing same-cost is strictly
  // better) AND that quality beats everything strictly cheaper. After each tier,
  // its best quality becomes part of the "strictly cheaper" baseline.
  const flushTier = () => {
    if (tierMembers.length === 0) return;
    if (tierBest > bestQualityStrictlyCheaper) {
      for (const idx of tierMembers) {
        if (pts[idx].quality === tierBest) onFrontier.add(idx);
      }
    }
    bestQualityStrictlyCheaper = Math.max(bestQualityStrictlyCheaper, tierBest);
  };

  for (const i of order) {
    const { cost, quality } = pts[i];
    if (cost !== tierCost) {
      flushTier();
      tierCost = cost;
      tierMembers = [];
      tierBest = -Infinity;
    }
    tierMembers.push(i);
    tierBest = Math.max(tierBest, quality);
  }
  flushTier();

  return onFrontier;
}

// Map leaderboard rows to plottable points. Quality is pass rate (the
// leaderboard's headline metric and what "recommended" is gated on); cost is the
// total estimated spend. Entries that never produced output (all errored) still
// plot at quality 0 so the failure is visible, not hidden.
export function buildScatterPoints(entries: ReadonlyArray<LeaderboardEntry>): ScatterPoint[] {
  const base = entries.map((e) => ({
    candidateId: e.candidate_id,
    label: e.label,
    cost: e.total_estimated_cost_usd,
    quality: e.pass_rate,
    recommended: e.recommended,
  }));
  const frontier = paretoFrontier(base);
  return base.map((p, i) => ({ ...p, onFrontier: frontier.has(i) }));
}
