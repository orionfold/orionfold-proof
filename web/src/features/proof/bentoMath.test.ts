import { describe, expect, test } from "vitest";

import type { CostRollup, CostTrendPoint } from "../../lib/api";
import { SAMPLE_REPORT } from "../../test/fixtures";
import { costSplitLine, formatUsd, latestProof, trendChartData } from "./bentoMath";

describe("latestProof", () => {
  test("null when there are no runs", () => {
    expect(latestProof([])).toBeNull();
  });

  test("takes the head (newest-first server order) and counts the rest", () => {
    const older = { ...SAMPLE_REPORT, run: { ...SAMPLE_REPORT.run, id: "run_old" } };
    const newest = { ...SAMPLE_REPORT, run: { ...SAMPLE_REPORT.run, id: "run_new" } };
    const lp = latestProof([newest, older]);
    expect(lp?.row.runId).toBe("run_new");
    expect(lp?.totalRuns).toBe(2);
  });
});

describe("trendChartData", () => {
  const trend: CostTrendPoint[] = [
    { run_id: "a", created_at: "2026-06-20T09:00:00Z", total_cost_usd: 0.0, pass_rate: 0.857 },
    { run_id: "b", created_at: "2026-06-27T10:00:00Z", total_cost_usd: 0.36, pass_rate: 0.76 },
  ];

  test("preserves oldest-first order and shapes the dual axes", () => {
    const data = trendChartData(trend);
    expect(data.map((d) => d.runId)).toEqual(["a", "b"]);
    expect(data[0]).toEqual({ runId: "a", label: "06-20", passRatePct: 86, costUsd: 0 });
    expect(data[1]).toEqual({ runId: "b", label: "06-27", passRatePct: 76, costUsd: 0.36 });
  });

  test("falls back to the raw string for a non-ISO created_at", () => {
    expect(trendChartData([{ run_id: "x", created_at: "whenever", total_cost_usd: 1, pass_rate: 1 }])[0].label).toBe("whenever");
  });
});

function rollup(over: Partial<CostRollup>): CostRollup {
  return { window: "today", run_count: 0, eval_cost_usd: 0, judge_cost_usd: 0, total_cost_usd: 0, trend: [], ...over };
}

describe("costSplitLine", () => {
  test("null when there's no judge spend (calm common case)", () => {
    expect(costSplitLine(rollup({ eval_cost_usd: 0.36, judge_cost_usd: 0, total_cost_usd: 0.36 }))).toBeNull();
  });
  test("shows the split when a judge ran", () => {
    expect(costSplitLine(rollup({ eval_cost_usd: 0.34, judge_cost_usd: 0.02, total_cost_usd: 0.36 }))).toBe("$0.34 eval + $0.02 judge");
  });
});

describe("formatUsd", () => {
  test("a real zero reads $0.00, not a dash", () => {
    expect(formatUsd(0)).toBe("$0.00");
  });
  test("cents under $10", () => {
    expect(formatUsd(0.36)).toBe("$0.36");
  });
  test("whole dollars at/over $10", () => {
    expect(formatUsd(12.4)).toBe("$12");
  });
});
