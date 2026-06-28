import { describe, expect, test } from "vitest";

import {
  SLOTS,
  emptyTrend,
  pushSample,
  sparklinePath,
  trendFromSeries,
  type Trend,
} from "./sparkline";

// Push a list of samples through the accumulator, returning the final trend.
function feed(values: (number | null)[], bucket = 1): Trend {
  let t = emptyTrend();
  for (const v of values) t = pushSample(t, v, { bucket });
  return t;
}

describe("pushSample — peak-bucket accumulator", () => {
  test("with bucket=1, each sample seals its own finalized bar", () => {
    const t = feed([10, 20, 30]);
    expect(t.finalized).toEqual([10, 20, 30]);
    expect(t.forming).toBeNull();
  });

  test("buckets keep the PEAK over the window, sealing every `bucket` samples", () => {
    // bucket=3: samples [5,9,2] seal to peak 9; [4,...] is the forming (in-progress) bucket.
    const t = feed([5, 9, 2, 4], 3);
    expect(t.finalized).toEqual([9]);
    expect(t.forming).toBe(4); // forming bucket holds the running peak so far
  });

  test("FIFO: the ring never exceeds SLOTS finalized bars; oldest drops off", () => {
    const t = feed(Array.from({ length: SLOTS + 5 }, (_, i) => i));
    expect(t.finalized).toHaveLength(SLOTS);
    // The first 5 (0..4) FIFO'd off; the window now starts at 5.
    expect(t.finalized[0]).toBe(5);
    expect(t.finalized[t.finalized.length - 1]).toBe(SLOTS + 4);
  });

  test("null sample leaves a gap, never a fabricated zero", () => {
    const t = feed([10, null, 30]);
    expect(t.finalized).toEqual([10, null, 30]);
  });

  test("forming bucket tracks the running peak, ignoring nulls within the window", () => {
    const t = feed([7, null, 3], 5); // all within one unsealed bucket
    expect(t.finalized).toEqual([]);
    expect(t.forming).toBe(7); // peak of {7,3}; null ignored
  });

  test("emptyTrend is the honest at-rest start", () => {
    const t = emptyTrend();
    expect(t.finalized).toEqual([]);
    expect(t.forming).toBeNull();
  });
});

describe("sparklinePath — SVG geometry", () => {
  test("returns null path for an empty trend (nothing to draw)", () => {
    const p = sparklinePath([], { w: 60, h: 16 });
    expect(p.line).toBeNull();
    expect(p.formingPoint).toBeNull();
  });

  test("maps values into the box: max value hits the top, 0 hits the bottom", () => {
    // Two points, max=100; second value 100 → y≈0 (top), first 0 → y≈h (bottom).
    const p = sparklinePath([0, 100], { w: 60, h: 16, max: 100 });
    expect(p.line).toMatch(/^M /);
    // Last point y should be near the top (small y), first near the bottom (large y).
    const ys = [...p.line!.matchAll(/[ML] [\d.]+ ([\d.]+)/g)].map((m) => Number(m[1]));
    expect(ys[0]).toBeGreaterThan(ys[ys.length - 1]);
  });

  test("auto-scales to the data max when no max is given", () => {
    const p = sparklinePath([2, 4], { w: 60, h: 16 });
    expect(p.line).not.toBeNull();
  });

  test("skips null gaps in the path (no line drawn through missing data)", () => {
    const p = sparklinePath([10, null, 30], { w: 60, h: 16, max: 30 });
    // A gap means the path lifts the pen (a new M after the null), not one continuous L.
    expect((p.line!.match(/M /g) ?? []).length).toBeGreaterThanOrEqual(2);
  });

  test("forming flag dims the last point so the live edge reads as in-progress", () => {
    const p = sparklinePath([10, 20], { w: 60, h: 16, max: 20, forming: true });
    expect(p.formingPoint).not.toBeNull();
    expect(p.formingPoint!.x).toBeGreaterThan(0);
  });

  test("returns a closed area path that drops from the line to the baseline", () => {
    const p = sparklinePath([0, 100], { w: 60, h: 16, max: 100 });
    expect(p.area).not.toBeNull();
    // The area closes back to the baseline (y≈h) and ends with a Z (closed fill region).
    expect(p.area!).toMatch(/Z$/);
    // It visits the baseline y (h, here 16) — the fill anchors the line to the x-axis.
    expect(p.area!).toMatch(/ 16(\.0)?(?: |Z)/);
  });

  test("area is null when there's nothing to draw", () => {
    expect(sparklinePath([], { w: 60, h: 16 }).area).toBeNull();
  });

  test("a single point still fills (a baseline rectangle, not an invisible dot)", () => {
    const p = sparklinePath([50], { w: 60, h: 16, max: 100 });
    expect(p.area).not.toBeNull();
    expect(p.area!).toMatch(/Z$/);
  });

  test("null gaps split the area into separate closed regions (no fill under missing data)", () => {
    const p = sparklinePath([10, null, 30], { w: 60, h: 16, max: 30 });
    // Two contiguous runs → two closed sub-areas (two Z's, two M's).
    expect((p.area!.match(/Z/g) ?? []).length).toBeGreaterThanOrEqual(2);
    expect((p.area!.match(/M /g) ?? []).length).toBeGreaterThanOrEqual(2);
  });
});

describe("trendFromSeries — seed a dimmed trend from a persisted per-bucket series", () => {
  test("loads the stored peaks as finalized bars with no forming edge", () => {
    const t = trendFromSeries([20, 45, 70, 30]);
    expect(t.finalized).toEqual([20, 45, 70, 30]);
    expect(t.forming).toBeNull();
    expect(t.count).toBe(0);
  });

  test("an empty series yields an empty trend (nothing to draw)", () => {
    const t = trendFromSeries([]);
    expect(t.finalized).toEqual([]);
    expect(t.forming).toBeNull();
  });

  test("respects the FIFO ring — never more than SLOTS bars", () => {
    const t = trendFromSeries(Array.from({ length: SLOTS + 5 }, (_, i) => i));
    expect(t.finalized).toHaveLength(SLOTS);
  });
});
