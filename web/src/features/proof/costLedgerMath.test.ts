import { describe, it, expect } from "vitest";

import { buildCostLedger } from "./costLedgerMath";
import type { LeaderboardEntry, ResultRow } from "../../lib/api";

// Minimal leaderboard entry — only the fields the ledger reads matter.
const entry = (over: Partial<LeaderboardEntry>): LeaderboardEntry => ({
  candidate_id: "c",
  label: "Candidate",
  provider_id: "anthropic",
  privacy: "cloud",
  total: 5,
  pass_count: 3,
  pass_rate: 0.6,
  avg_score: 0.6,
  avg_latency_ms: 100,
  total_estimated_cost_usd: 0,
  failure_count: 0,
  error_count: 0,
  recommended: false,
  ...over,
});

// Minimal result row — one matrix cell for one candidate.
const row = (over: Partial<ResultRow>): ResultRow => ({
  candidate_id: "c",
  example_index: 0,
  input_text: "in",
  expected_text: "exp",
  output_text: "out",
  score: 1,
  passed: true,
  latency_ms: 100,
  estimated_cost_usd: 0,
  input_tokens: 0,
  output_tokens: 0,
  judge_cost_usd: 0,
  judge_latency_ms: 0,
  privacy: "cloud",
  error: null,
  ...over,
});

describe("buildCostLedger", () => {
  it("rolls per-candidate candidate + judge cost and tokens up from result rows", () => {
    const lb = [
      entry({ candidate_id: "a", label: "Opus" }),
      entry({ candidate_id: "b", label: "Haiku" }),
    ];
    const results = [
      row({ candidate_id: "a", estimated_cost_usd: 0.03, judge_cost_usd: 0.01, input_tokens: 100, output_tokens: 20 }),
      row({ candidate_id: "a", estimated_cost_usd: 0.02, judge_cost_usd: 0.01, input_tokens: 80, output_tokens: 10 }),
      row({ candidate_id: "b", estimated_cost_usd: 0.005, judge_cost_usd: 0, input_tokens: 50, output_tokens: 5 }),
    ];
    const ledger = buildCostLedger(lb, results);

    const a = ledger.candidates.find((c) => c.candidateId === "a")!;
    expect(a.candidateCostUsd).toBeCloseTo(0.05, 6);
    expect(a.judgeCostUsd).toBeCloseTo(0.02, 6);
    expect(a.totalCostUsd).toBeCloseTo(0.07, 6);
    expect(a.inputTokens).toBe(180);
    expect(a.outputTokens).toBe(30);

    const b = ledger.candidates.find((c) => c.candidateId === "b")!;
    expect(b.totalCostUsd).toBeCloseTo(0.005, 6);
    expect(b.judgeCostUsd).toBe(0);
  });

  it("INVARIANT: per-candidate totals sum back to the run cost_summary (the verdict line)", () => {
    // The verify gate: Σ candidate rows must equal what build_cost_summary computes,
    // because both roll up the SAME result rows.
    const lb = [entry({ candidate_id: "a" }), entry({ candidate_id: "b" })];
    const results = [
      row({ candidate_id: "a", estimated_cost_usd: 0.0413, judge_cost_usd: 0 }),
      row({ candidate_id: "a", estimated_cost_usd: 0.0414, judge_cost_usd: 0 }),
      row({ candidate_id: "b", estimated_cost_usd: 0.0827, judge_cost_usd: 0 }),
    ];
    const ledger = buildCostLedger(lb, results);

    const summedCandidate = ledger.candidates.reduce((s, c) => s + c.candidateCostUsd, 0);
    const summedJudge = ledger.candidates.reduce((s, c) => s + c.judgeCostUsd, 0);
    const summedTotal = ledger.candidates.reduce((s, c) => s + c.totalCostUsd, 0);

    // These three are exactly what DecisionSummary prints from cost_summary.
    const expectedCandidate = results.reduce((s, r) => s + r.estimated_cost_usd, 0);
    const expectedJudge = results.reduce((s, r) => s + r.judge_cost_usd, 0);

    expect(summedCandidate).toBeCloseTo(expectedCandidate, 9);
    expect(summedJudge).toBeCloseTo(expectedJudge, 9);
    expect(summedTotal).toBeCloseTo(expectedCandidate + expectedJudge, 9);
    expect(ledger.candidateCostUsd).toBeCloseTo(expectedCandidate, 9);
    expect(ledger.judgeCostUsd).toBeCloseTo(expectedJudge, 9);
    expect(ledger.totalCostUsd).toBeCloseTo(expectedCandidate + expectedJudge, 9);
  });

  it("computes each candidate's share of the run total (0–1)", () => {
    const lb = [entry({ candidate_id: "a" }), entry({ candidate_id: "b" })];
    const results = [
      row({ candidate_id: "a", estimated_cost_usd: 0.075 }),
      row({ candidate_id: "b", estimated_cost_usd: 0.025 }),
    ];
    const ledger = buildCostLedger(lb, results);
    expect(ledger.candidates.find((c) => c.candidateId === "a")!.share).toBeCloseTo(0.75, 6);
    expect(ledger.candidates.find((c) => c.candidateId === "b")!.share).toBeCloseTo(0.25, 6);
  });

  it("preserves leaderboard order (recommended-first), not result-row order", () => {
    const lb = [
      entry({ candidate_id: "win", label: "Winner", recommended: true }),
      entry({ candidate_id: "other", label: "Other" }),
    ];
    const results = [
      row({ candidate_id: "other", estimated_cost_usd: 0.01 }),
      row({ candidate_id: "win", estimated_cost_usd: 0.02 }),
    ];
    const ledger = buildCostLedger(lb, results);
    expect(ledger.candidates.map((c) => c.candidateId)).toEqual(["win", "other"]);
  });

  it("is free-run safe: zero total → zero shares, no divide-by-zero NaN", () => {
    const lb = [entry({ candidate_id: "mock_good" })];
    const results = [row({ candidate_id: "mock_good", estimated_cost_usd: 0, judge_cost_usd: 0 })];
    const ledger = buildCostLedger(lb, results);
    expect(ledger.totalCostUsd).toBe(0);
    expect(ledger.candidates[0].share).toBe(0);
    expect(Number.isNaN(ledger.candidates[0].share)).toBe(false);
  });

  it("includes a leaderboard candidate with no result rows as all-zero", () => {
    const lb = [entry({ candidate_id: "ran" }), entry({ candidate_id: "norows" })];
    const results = [row({ candidate_id: "ran", estimated_cost_usd: 0.01 })];
    const ledger = buildCostLedger(lb, results);
    const norows = ledger.candidates.find((c) => c.candidateId === "norows")!;
    expect(norows.totalCostUsd).toBe(0);
    expect(norows.inputTokens).toBe(0);
  });
});
