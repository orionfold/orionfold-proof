import { describe, it, expect } from "vitest";

import { paretoFrontier, buildScatterPoints } from "./paretoFrontier";
import type { LeaderboardEntry } from "../../lib/api";

const frontierIdx = (pts: { cost: number; quality: number }[]) =>
  [...paretoFrontier(pts)].sort((a, b) => a - b);

describe("paretoFrontier (lower cost + higher quality = better)", () => {
  it("keeps the cheaper-and-better point and drops the dominated one", () => {
    // B is cheaper AND higher quality than A → A is dominated.
    const pts = [
      { cost: 1.0, quality: 0.6 }, // A — dominated by B
      { cost: 0.5, quality: 0.8 }, // B — dominates A
    ];
    expect(frontierIdx(pts)).toEqual([1]);
  });

  it("keeps both ends of a genuine trade-off (cheap-worse and dear-better)", () => {
    const pts = [
      { cost: 0.2, quality: 0.5 }, // cheap, lower quality — non-dominated
      { cost: 1.0, quality: 0.9 }, // dear, higher quality — non-dominated
      { cost: 0.6, quality: 0.4 }, // dearer than #0 yet worse → dominated
    ];
    expect(frontierIdx(pts)).toEqual([0, 1]);
  });

  it("does NOT treat higher cost as better (orientation guard)", () => {
    // If the math mistakenly favored higher x, the dear point would dominate.
    const pts = [
      { cost: 0.1, quality: 0.9 }, // cheapest AND best → sole frontier
      { cost: 0.9, quality: 0.9 }, // same quality, dearer → dominated
      { cost: 0.9, quality: 0.7 }, // dearer and worse → dominated
    ];
    expect(frontierIdx(pts)).toEqual([0]);
  });

  it("keeps tied (cost, quality) points both on the frontier", () => {
    const pts = [
      { cost: 0.5, quality: 0.8 },
      { cost: 0.5, quality: 0.8 }, // identical → neither strictly dominates
    ];
    expect(frontierIdx(pts)).toEqual([0, 1]);
  });

  it("at equal cost keeps only the higher-quality point", () => {
    const pts = [
      { cost: 0.5, quality: 0.6 }, // same cost, worse → dominated
      { cost: 0.5, quality: 0.9 }, // same cost, better → frontier
    ];
    expect(frontierIdx(pts)).toEqual([1]);
  });

  it("all-free runs (cost 0) → frontier is the max-quality point(s)", () => {
    const pts = [
      { cost: 0, quality: 0.4 },
      { cost: 0, quality: 0.9 }, // best of the free tier
      { cost: 0, quality: 0.9 }, // tie at best → also kept
    ];
    expect(frontierIdx(pts)).toEqual([1, 2]);
  });

  it("single candidate is trivially on the frontier", () => {
    expect(frontierIdx([{ cost: 0.3, quality: 0.7 }])).toEqual([0]);
  });

  it("empty input → empty set", () => {
    expect(frontierIdx([])).toEqual([]);
  });

  it("classic skyline: a chain of improving trade-offs all survive", () => {
    const pts = [
      { cost: 0.1, quality: 0.3 },
      { cost: 0.2, quality: 0.5 },
      { cost: 0.4, quality: 0.7 },
      { cost: 0.8, quality: 0.95 },
      { cost: 0.3, quality: 0.4 }, // dearer than #1 yet worse → dominated
    ];
    expect(frontierIdx(pts)).toEqual([0, 1, 2, 3]);
  });
});

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

describe("buildScatterPoints", () => {
  it("maps cost/quality and flags the frontier + recommended", () => {
    const pts = buildScatterPoints([
      entry({ candidate_id: "a", total_estimated_cost_usd: 1.0, pass_rate: 0.6 }),
      entry({ candidate_id: "b", total_estimated_cost_usd: 0.5, pass_rate: 0.8, recommended: true }),
    ]);
    const a = pts.find((p) => p.candidateId === "a")!;
    const b = pts.find((p) => p.candidateId === "b")!;
    expect(a.cost).toBe(1.0);
    expect(a.quality).toBe(0.6);
    expect(a.onFrontier).toBe(false); // dominated by b
    expect(b.onFrontier).toBe(true);
    expect(b.recommended).toBe(true);
    expect(a.recommended).toBe(false);
  });

  it("plots an all-errored candidate at quality 0 (failure stays visible)", () => {
    const pts = buildScatterPoints([
      entry({ candidate_id: "x", pass_rate: 0, total_estimated_cost_usd: 0.2 }),
    ]);
    expect(pts[0].quality).toBe(0);
  });

  it('metric "avg_score" reads avg_score for quality and recomputes the frontier', () => {
    // Pass-rate flat at 0 for all (scorer mismatch) — only avg score separates them.
    // On avg_score, the cheaper-and-higher-score point dominates the dearer-lower one.
    const pts = buildScatterPoints(
      [
        entry({ candidate_id: "a", total_estimated_cost_usd: 1.0, pass_rate: 0, avg_score: 0.06 }),
        entry({ candidate_id: "b", total_estimated_cost_usd: 0.5, pass_rate: 0, avg_score: 0.15, recommended: true }),
      ],
      "avg_score",
    );
    const a = pts.find((p) => p.candidateId === "a")!;
    const b = pts.find((p) => p.candidateId === "b")!;
    expect(a.quality).toBe(0.06); // reads avg_score, not pass_rate
    expect(b.quality).toBe(0.15);
    expect(b.onFrontier).toBe(true); // cheaper AND higher avg score
    expect(a.onFrontier).toBe(false);
    // recommended passes through from the leaderboard, not re-derived from the metric.
    expect(b.recommended).toBe(true);
  });

  it("default metric stays pass_rate (WS-D1 behaviour) when omitted", () => {
    const pts = buildScatterPoints([
      entry({ candidate_id: "a", pass_rate: 0.6, avg_score: 0.9 }),
    ]);
    expect(pts[0].quality).toBe(0.6); // pass_rate, not avg_score
  });
});
