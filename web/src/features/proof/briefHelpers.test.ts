import { describe, expect, it } from "vitest";

import { effectiveDecisionQuestion, quickDecisionHeadline } from "./briefHelpers";

describe("effectiveDecisionQuestion", () => {
  it("clears an untouched question (so it can't contradict a new dataset)", () => {
    expect(effectiveDecisionQuestion("Which model for memos?", false)).toBe("");
  });

  it("keeps the question once the user has touched it", () => {
    expect(effectiveDecisionQuestion("Which model for memos?", true)).toBe(
      "Which model for memos?",
    );
  });

  it("keeps an empty touched question empty", () => {
    expect(effectiveDecisionQuestion("", true)).toBe("");
  });
});

describe("quickDecisionHeadline", () => {
  it("uses the prompt verbatim when short", () => {
    expect(quickDecisionHeadline("Summarize this memo")).toBe("Summarize this memo");
  });

  it("collapses whitespace and trims", () => {
    expect(quickDecisionHeadline("  Summarize\n  this   memo \t")).toBe("Summarize this memo");
  });

  it("returns empty for a blank prompt", () => {
    expect(quickDecisionHeadline("   \n  ")).toBe("");
  });

  it("truncates a long prompt to a headline with an ellipsis", () => {
    const long = "a ".repeat(200).trim();
    const headline = quickDecisionHeadline(long);
    expect(headline.length).toBeLessThanOrEqual(120);
    expect(headline.endsWith("…")).toBe(true);
  });
});
