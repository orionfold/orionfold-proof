import { describe, expect, it } from "vitest";

import { tagToken } from "./tags";

describe("tagToken", () => {
  it("is stable and case-insensitive for the same label", () => {
    expect(tagToken("Legal")).toBe(tagToken("legal"));
  });
  it("returns a valid categorical token", () => {
    expect(["t1", "t2", "t3", "t5", "t7"]).toContain(tagToken("Finance"));
  });
});
