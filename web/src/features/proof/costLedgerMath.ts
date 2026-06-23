// Run-level cost ledger math (WS-D2) — pure, unit-tested, no React.
//
// The verdict banner already prints the run total ("Run cost: candidate $X ·
// judge $Y · total $Z") straight off report.cost_summary, which the engine rolls
// up as Σ estimated_cost_usd (candidate) + Σ judge_cost_usd (judge) over every
// ResultRow. This module rolls the SAME rows up PER CANDIDATE so the panel can
// show who spent what — and, by construction, the per-candidate rows sum back to
// cost_summary exactly. No backend field, no new source of truth to drift from.

import type { LeaderboardEntry, Privacy, ResultRow } from "../../lib/api";

export interface CandidateCost {
  candidateId: string;
  label: string;
  providerId: string;
  privacy: Privacy;
  candidateCostUsd: number; // Σ estimated_cost_usd for this candidate's cells
  judgeCostUsd: number; // Σ judge_cost_usd for this candidate's cells (0 if no judge)
  totalCostUsd: number; // candidate + judge
  inputTokens: number;
  outputTokens: number;
  share: number; // 0–1 fraction of the run's total spend (0 when the run is free)
}

export interface CostLedger {
  candidates: CandidateCost[]; // ordered to match the leaderboard (recommended first)
  candidateCostUsd: number; // run totals — equal report.cost_summary by construction
  judgeCostUsd: number;
  totalCostUsd: number;
  inputTokens: number;
  outputTokens: number;
}

// Roll result rows up per candidate, ordered and labelled by the leaderboard.
// We key spend off `results` (not LeaderboardEntry) because the leaderboard only
// carries candidate $ — judge $ and token counts live per-cell on ResultRow.
// Leaderboard order is preserved so the recommended candidate leads, matching the
// table above it; a leaderboard entry with no rows still appears (all-zero).
export function buildCostLedger(
  leaderboard: ReadonlyArray<LeaderboardEntry>,
  results: ReadonlyArray<ResultRow>,
): CostLedger {
  // Aggregate each candidate's cells in one pass.
  const byCandidate = new Map<
    string,
    { candidate: number; judge: number; inTok: number; outTok: number }
  >();
  for (const r of results) {
    const acc = byCandidate.get(r.candidate_id) ?? {
      candidate: 0,
      judge: 0,
      inTok: 0,
      outTok: 0,
    };
    acc.candidate += r.estimated_cost_usd;
    acc.judge += r.judge_cost_usd;
    acc.inTok += r.input_tokens;
    acc.outTok += r.output_tokens;
    byCandidate.set(r.candidate_id, acc);
  }

  const totals = { candidate: 0, judge: 0, inTok: 0, outTok: 0 };
  for (const acc of byCandidate.values()) {
    totals.candidate += acc.candidate;
    totals.judge += acc.judge;
    totals.inTok += acc.inTok;
    totals.outTok += acc.outTok;
  }
  const grandTotal = totals.candidate + totals.judge;

  const candidates: CandidateCost[] = leaderboard.map((e) => {
    const acc = byCandidate.get(e.candidate_id) ?? {
      candidate: 0,
      judge: 0,
      inTok: 0,
      outTok: 0,
    };
    const total = acc.candidate + acc.judge;
    return {
      candidateId: e.candidate_id,
      label: e.label,
      providerId: e.provider_id,
      privacy: e.privacy,
      candidateCostUsd: acc.candidate,
      judgeCostUsd: acc.judge,
      totalCostUsd: total,
      inputTokens: acc.inTok,
      outputTokens: acc.outTok,
      share: grandTotal > 0 ? total / grandTotal : 0,
    };
  });

  return {
    candidates,
    candidateCostUsd: totals.candidate,
    judgeCostUsd: totals.judge,
    totalCostUsd: grandTotal,
    inputTokens: totals.inTok,
    outputTokens: totals.outTok,
  };
}
