import { describe, it, expect } from "vitest";

import { deriveDecideInsight } from "./decideInsights";
import type { LeaderboardEntry } from "../../lib/api";

function entry(over: Partial<LeaderboardEntry>): LeaderboardEntry {
  return {
    candidate_id: "c",
    label: "Cand",
    provider_id: "mock",
    privacy: "local",
    total: 5,
    pass_count: 3,
    pass_rate: 0.6,
    avg_score: 0.6,
    avg_latency_ms: 100,
    total_estimated_cost_usd: 0.01,
    failure_count: 2,
    error_count: 0,
    recommended: false,
    ...over,
  };
}

describe("deriveDecideInsight", () => {
  it("empty leaderboard → null", () => {
    expect(deriveDecideInsight([])).toBeNull();
  });

  it("all-errored → warn about keys/host before scores (rule 1)", () => {
    const out = deriveDecideInsight([
      entry({ candidate_id: "a", total: 5, error_count: 5, pass_rate: 0, avg_score: 0 }),
      entry({ candidate_id: "b", total: 5, error_count: 5, pass_rate: 0, avg_score: 0 }),
    ])!;
    expect(out.tone).toBe("warn");
    expect(out.headline).toMatch(/no candidate produced output/i);
    expect(out.detail).toMatch(/keys|host/i);
  });

  it("all-fail but real scores → names leader + suggests LLM judge (rule 2, the case we hit)", () => {
    // The 2026-06-23 3-tier Anthropic case: 0% pass for all, scores 0.06/0.06/0.15.
    const out = deriveDecideInsight([
      entry({ candidate_id: "haiku", label: "Claude Haiku", pass_rate: 0, avg_score: 0.06 }),
      entry({ candidate_id: "sonnet", label: "Claude Sonnet", pass_rate: 0, avg_score: 0.06 }),
      entry({ candidate_id: "opus", label: "Claude Opus", pass_rate: 0, avg_score: 0.15 }),
    ])!;
    expect(out.tone).toBe("warn");
    expect(out.headline).toMatch(/0% pass/i);
    // Opus (0.15) is the avg-score leader, not the first row.
    expect(out.detail).toContain("Claude Opus");
    expect(out.detail).toMatch(/6%–15%/); // min–max avg-score range
    expect(out.detail).toMatch(/LLM judge|threshold/i);
  });

  it("all-fail with a single avg-score value → range collapses to one figure", () => {
    const out = deriveDecideInsight([
      entry({ candidate_id: "a", label: "A", pass_rate: 0, avg_score: 0.1 }),
      entry({ candidate_id: "b", label: "B", pass_rate: 0, avg_score: 0.1 }),
    ])!;
    expect(out.tone).toBe("warn");
    expect(out.detail).toMatch(/at 10% —/); // not "10%–10%"
  });

  it("all-fail but scores are noise (< floor) → falls through, not a scorer-mismatch claim", () => {
    const out = deriveDecideInsight([
      entry({ candidate_id: "a", label: "A", pass_rate: 0, avg_score: 0.0 }),
      entry({ candidate_id: "b", label: "B", pass_rate: 0, avg_score: 0.01 }),
    ])!;
    // Not the rule-2 headline — no real signal to rescue.
    expect(out.headline).not.toMatch(/0% pass, but/i);
    expect(out.tone).toBe("info");
  });

  it("clear winner, well separated → ok tone naming the winner (rule 3)", () => {
    const out = deriveDecideInsight([
      entry({ candidate_id: "w", label: "Winner", pass_rate: 0.9, recommended: true, total_estimated_cost_usd: 0.5 }),
      entry({ candidate_id: "r", label: "Runner", pass_rate: 0.6 }),
    ])!;
    expect(out.tone).toBe("ok");
    expect(out.headline).toMatch(/Winner is the clear pick/i);
    expect(out.detail).toMatch(/90%/);
    expect(out.detail).toMatch(/\$0\.5000/);
  });

  it("winner but tight cluster → info tone, decide on cost/latency (rule 4)", () => {
    const out = deriveDecideInsight([
      entry({ candidate_id: "w", label: "Winner", pass_rate: 0.62, recommended: true }),
      entry({ candidate_id: "r", label: "Runner", pass_rate: 0.6 }),
    ])!;
    expect(out.tone).toBe("info");
    expect(out.headline).toMatch(/edges it/i);
    expect(out.detail).toMatch(/cost or latency/i);
  });

  it("single candidate → fallback names it (rule 5)", () => {
    const out = deriveDecideInsight([entry({ candidate_id: "solo", label: "Solo", pass_rate: 0.7 })])!;
    expect(out.tone).toBe("info");
    expect(out.headline).toMatch(/Solo, on its own/i);
    expect(out.detail).toMatch(/add a second/i);
  });

  it("no winner, partial passes → fallback names the pass-rate leader (rule 5)", () => {
    const out = deriveDecideInsight([
      entry({ candidate_id: "a", label: "Alpha", pass_rate: 0.4, recommended: false }),
      entry({ candidate_id: "b", label: "Beta", pass_rate: 0.45, recommended: false }),
    ])!;
    expect(out.tone).toBe("info");
    expect(out.headline).toMatch(/Beta leads/i);
    expect(out.detail).toMatch(/no candidate was recommended/i);
  });
});
