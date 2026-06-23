import { describe, expect, it } from "vitest";
import { objectiveBar, totalTokens } from "./quickCompareFormat";

describe("objectiveBar", () => {
  it("scales value against max", () => {
    expect(objectiveBar(420, 980)).toBeCloseTo(420 / 980);
    expect(objectiveBar(980, 980)).toBe(1);
  });
  it("is zero-safe", () => {
    expect(objectiveBar(0, 0)).toBe(0);
    expect(objectiveBar(5, 0)).toBe(0);
  });
});

describe("totalTokens", () => {
  it("sums input + output", () => {
    expect(totalTokens({ input_tokens: 12, output_tokens: 30 })).toBe(42);
  });
});
