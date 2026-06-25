import { describe, expect, it } from "vitest";

import { behaviorMeta, citationIds, requirementChips } from "./exampleShape";
import type { Example } from "../../lib/api";

function ex(over: Partial<Example> = {}): Example {
  return { input_text: "i", expected_text: "e", keypoints: [], ...over };
}

describe("behaviorMeta", () => {
  it("maps each behavior to a label and icon", () => {
    expect(behaviorMeta("answer").label).toBe("Answer");
    expect(behaviorMeta("route").label).toBe("Route");
    expect(behaviorMeta("refuse").label).toBe("Refuse");
  });
  it("marks refuse as the caution-toned expectation, others neutral", () => {
    expect(behaviorMeta("refuse").tone).toBe("warn");
    expect(behaviorMeta("answer").tone).toBe("neutral");
    expect(behaviorMeta("route").tone).toBe("neutral");
  });
  it("defaults a null behavior to answer (mirrors the backend scorer)", () => {
    expect(behaviorMeta(null).label).toBe("Answer");
    expect(behaviorMeta(undefined).label).toBe("Answer");
  });
});

describe("requirementChips", () => {
  it("lists only the set gates, in cite · refuse · route order", () => {
    expect(requirementChips(ex({ requires_citation: true, requires_route: true }))).toEqual(["cite", "route"]);
    expect(requirementChips(ex({ requires_refusal: true }))).toEqual(["refuse"]);
    expect(requirementChips(ex())).toEqual([]);
  });
});

describe("citationIds", () => {
  it("separates expected (all) from accepted (any), defaulting to empty", () => {
    expect(citationIds(ex({ expected_citations: ["a"], accepted_source_ids: ["b", "c"] }))).toEqual({
      expected: ["a"],
      accepted: ["b", "c"],
    });
    expect(citationIds(ex())).toEqual({ expected: [], accepted: [] });
  });
});
