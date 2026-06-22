import { describe, expect, test } from "vitest";

import { formatCostPerQuality, medalFor, passRateTone } from "./leaderboardFormat";

describe("passRateTone (traffic-light on pass rate)", () => {
  test("green at >= 0.8", () => expect(passRateTone(0.8)).toBe("ok"));
  test("amber in [0.5, 0.8)", () => expect(passRateTone(0.6)).toBe("warn"));
  test("red below 0.5", () => expect(passRateTone(0.2)).toBe("danger"));
});

describe("formatCostPerQuality", () => {
  test("null -> em dash", () => expect(formatCostPerQuality(null)).toBe("—"));
  test("undefined -> em dash", () => expect(formatCostPerQuality(undefined)).toBe("—"));
  test("zero -> Free", () => expect(formatCostPerQuality(0)).toBe("Free"));
  test("value -> 4-decimal dollars", () => expect(formatCostPerQuality(0.004)).toBe("$0.0040"));
});

describe("medalFor", () => {
  test("podium medals only when a winner exists", () => {
    expect(medalFor(0, true)).toBe("🥇");
    expect(medalFor(1, true)).toBe("🥈");
    expect(medalFor(2, true)).toBe("🥉");
    expect(medalFor(3, true)).toBeNull();
  });
  test("no medals in the no-winner state", () => {
    expect(medalFor(0, false)).toBeNull();
  });
});
