import { describe, expect, it } from "vitest";

import { computeCoverage } from "./datasetCoverageMath";
import type { Dataset } from "../../lib/api";

function ds(over: Partial<Dataset>): Dataset {
  return {
    id: over.id ?? "d",
    name: over.name ?? "D",
    description: "",
    examples: over.examples ?? [{ input_text: "i", expected_text: "e", keypoints: [] }],
    ...over,
  };
}

// Mirror the bundled library: keypoint/Finance, exact/Support, contains/Legal, similarity/Sales,
// bench/Governance (corpus-bound, 21 rows, ships a system prompt).
function library(): Dataset[] {
  const rows = (n: number) => Array.from({ length: n }, () => ({ input_text: "i", expected_text: "e", keypoints: [] }));
  return [
    ds({ id: "memo", examples: [{ input_text: "i", expected_text: "e", keypoints: ["22%"] }], tags: ["Finance"] }),
    ds({ id: "triage", check_hint: "exact", examples: rows(5), tags: ["Support"] }),
    ds({ id: "contract", check_hint: "substring", examples: rows(5), tags: ["Legal"] }),
    ds({ id: "buyer", examples: rows(5), tags: ["Sales"] }),
    ds({
      id: "bench",
      corpus_id: "ainative-field-notes",
      system_prompt: "You are Orionfold Advisor…",
      examples: rows(21),
      tags: ["Governance"],
    }),
  ];
}

describe("computeCoverage", () => {
  it("counts datasets, examples, and distinct eval types across the library", () => {
    const c = computeCoverage(library());
    expect(c.datasetCount).toBe(5);
    expect(c.totalExamples).toBe(1 + 5 + 5 + 5 + 21);
    expect(c.evalTypeCount).toBe(5); // keypoint, exact, contains, similarity, bench
  });

  it("flags governance bench / contract / corpus datasets", () => {
    const c = computeCoverage(library());
    expect(c.benchCount).toBe(1);
    expect(c.contractCount).toBe(1);
    expect(c.corpusCount).toBe(1);
  });

  it("sorts the distribution by count then examples, and dedups + sorts domains", () => {
    const c = computeCoverage(library());
    // bench carries the most examples (21) so it leads when counts tie at 1 each.
    expect(c.distribution[0].kind).toBe("bench");
    expect(c.distribution.every((s) => s.count > 0)).toBe(true);
    expect(c.domains).toEqual(["Finance", "Governance", "Legal", "Sales", "Support"]);
  });

  it("handles an empty library and a single dataset", () => {
    expect(computeCoverage([])).toMatchObject({ datasetCount: 0, totalExamples: 0, evalTypeCount: 0, distribution: [] });
    const one = computeCoverage([ds({ id: "solo", check_hint: "exact", tags: ["X"] })]);
    expect(one.datasetCount).toBe(1);
    expect(one.distribution).toHaveLength(1);
    expect(one.distribution[0].kind).toBe("exact");
  });
});
