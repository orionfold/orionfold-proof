import { describe, expect, it } from "vitest";

import { buildStoppedSummary } from "./stoppedSummary";
import type { RunStartEvent } from "../../lib/api";

const start = (total: number): RunStartEvent => ({
  type: "start",
  total,
  n_examples: total,
  candidates: [],
});

describe("buildStoppedSummary", () => {
  it("sums incurred cost and counts received cells", () => {
    const s = buildStoppedSummary(start(10), [{ cost: 0.002 }, { cost: 0.003 }]);
    expect(s).toEqual({ completedCells: 2, totalCells: 10, incurredCost: 0.005 });
  });

  it("zero cost stays zero (no NaN; the view omits the dollar line)", () => {
    const s = buildStoppedSummary(start(4), [{ cost: 0 }, { cost: 0 }]);
    expect(s.incurredCost).toBe(0);
    expect(s.completedCells).toBe(2);
    expect(s.totalCells).toBe(4);
  });

  it("no start event yet → totalCells 0, never NaN", () => {
    const s = buildStoppedSummary(null, []);
    expect(s).toEqual({ completedCells: 0, totalCells: 0, incurredCost: 0 });
  });

  it("tolerates a missing cost field on a cell (defaults to 0)", () => {
    const s = buildStoppedSummary(start(3), [{}, { cost: 0.01 }]);
    expect(s.incurredCost).toBe(0.01);
    expect(s.completedCells).toBe(2);
  });
});
