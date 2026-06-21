import { describe, it, expect } from "vitest";
import { resolveAutoKind } from "./scoring";
import type { Dataset } from "../../lib/api";

function ds(keypoints: string[][]): Dataset {
  return {
    id: "d",
    name: "D",
    description: "",
    examples: keypoints.map((kp) => ({ input_text: "i", expected_text: "e", keypoints: kp })),
  };
}

describe("resolveAutoKind", () => {
  it("returns keypoint when any example has keypoints", () => {
    expect(resolveAutoKind(ds([[], ["22%"]]))).toBe("keypoint");
  });
  it("returns similarity when no example has keypoints", () => {
    expect(resolveAutoKind(ds([[], []]))).toBe("similarity");
  });
  it("returns similarity for an undefined dataset", () => {
    expect(resolveAutoKind(undefined)).toBe("similarity");
  });
});
