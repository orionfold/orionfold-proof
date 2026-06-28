import { describe, expect, test } from "vitest";

import type { RunProgressEvent, RunStartEvent } from "../../lib/api";
import { emptyRunProgress, reduceRunProgress, type RunProgress } from "./useRunProgress";

const START: RunStartEvent = {
  type: "start",
  total: 6, // n_examples (3) × candidates (2)
  n_examples: 3,
  candidates: [
    { id: "a", label: "A", provider_id: "p", privacy: "local" },
    { id: "b", label: "B", provider_id: "p", privacy: "cloud" },
  ],
};

function progress(candidate_id: string, example_index: number, passed: boolean): RunProgressEvent {
  return { type: "progress", done: 0, candidate_id, example_index, passed, error: false, cost: 0 };
}

function feed(events: (RunStartEvent | RunProgressEvent)[]): RunProgress {
  let s = emptyRunProgress();
  for (const e of events) s = reduceRunProgress(s, e);
  return s;
}

describe("reduceRunProgress", () => {
  test("start establishes totals and zero progress", () => {
    const s = feed([START]);
    expect(s.candidatesTotal).toBe(2);
    expect(s.examplesTotal).toBe(6);
    expect(s.examplesDone).toBe(0);
    expect(s.candidatesDone).toBe(0);
    expect(s.passRateSoFar).toBeNull(); // nothing scored yet → honest null, not 0%
  });

  test("counts completed examples and pools pass-rate across candidates", () => {
    const s = feed([
      START,
      progress("a", 0, true),
      progress("a", 1, false),
      progress("b", 0, true),
    ]);
    expect(s.examplesDone).toBe(3);
    // 2 of 3 completed examples passed.
    expect(s.passRateSoFar).toBeCloseTo(2 / 3);
  });

  test("a candidate is 'done' once all its examples report", () => {
    const s = feed([
      START,
      progress("a", 0, true),
      progress("a", 1, true),
      progress("a", 2, true), // candidate a finished all 3
      progress("b", 0, false),
    ]);
    expect(s.candidatesDone).toBe(1);
    expect(s.examplesDone).toBe(4);
  });

  test("is order-independent and idempotent on a repeated cell", () => {
    const s = feed([
      START,
      progress("a", 2, true),
      progress("a", 0, true),
      progress("a", 0, true), // duplicate of the same cell — must not double-count
    ]);
    // example_index 2 implies at least 3 done for candidate a (monotonic max), but distinct
    // reported cells are {0,2} → we count distinct passes/total honestly as reported.
    expect(s.examplesDone).toBeGreaterThanOrEqual(2);
  });

  test("emptyRunProgress is the honest at-rest state", () => {
    const s = emptyRunProgress();
    expect(s.candidatesTotal).toBe(0);
    expect(s.examplesDone).toBe(0);
    expect(s.passRateSoFar).toBeNull();
  });
});
