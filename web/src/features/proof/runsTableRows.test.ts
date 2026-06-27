import { describe, expect, test } from "vitest";

import type { ProofReport } from "../../lib/api";
import { SAMPLE_REPORT, NO_WINNER_REPORT } from "../../test/fixtures";
import {
  DEFAULT_RUN_SORT,
  nextRunSort,
  sortRunRows,
  toRunRow,
  type RunRow,
} from "./runsTableRows";

function withRun(over: Partial<ProofReport["run"]>, report = SAMPLE_REPORT): ProofReport {
  return { ...report, run: { ...report.run, ...over } };
}

describe("toRunRow — verdict resolution is mode-specific", () => {
  test("a full run reads the recommended leaderboard entry", () => {
    const row = toRunRow(SAMPLE_REPORT);
    expect(row.verb).toBe("Winner");
    expect(row.winnerLabel).toBe("Mock · good");
    expect(row.passText).toBe("5/5");
    expect(row.passRate).toBe(1);
    expect(row.scoredBy).toBe("Contains");
  });

  test("a full run with nothing recommended reads 'No clear winner'", () => {
    const row = toRunRow(NO_WINNER_REPORT);
    expect(row.verb).toBe("No clear winner");
    expect(row.winnerLabel).toBeNull();
    expect(row.passRate).toBeNull();
  });

  test("a quick run reads the human pick on chosen_winner, NOT the leaderboard", () => {
    const report = withRun(
      {
        mode: "quick",
        rubric: { kind: "none", threshold: 0, case_sensitive: false },
        chosen_winner: "mock_good",
        candidates: [{ id: "mock_good", label: "Mock · good", provider_id: "mock_good", privacy: "local" }],
      },
      // leaderboard still has a recommended entry, but quick must ignore it
      SAMPLE_REPORT,
    );
    const row = toRunRow(report);
    expect(row.verb).toBe("Picked");
    expect(row.winnerLabel).toBe("Mock · good");
    expect(row.winnerPrivacy).toBe("local");
    expect(row.passText).toBeNull(); // unscored — no pass count
    expect(row.scoredBy).toBe("Quick check");
  });

  test("a quick run with a tie reads 'Tie'", () => {
    const row = toRunRow(withRun({ mode: "quick", rubric: { kind: "none", threshold: 0, case_sensitive: false }, chosen_winner: "tie" }));
    expect(row.verb).toBe("Tie");
    expect(row.winnerLabel).toBeNull();
  });

  test("flags sample receipts by run-id prefix", () => {
    expect(toRunRow(withRun({ id: "run_sample_xyz" })).isSample).toBe(true);
    expect(toRunRow(withRun({ id: "run_abc123" })).isSample).toBe(false);
  });

  test("carries cost from cost_summary.total_cost_usd", () => {
    const report = { ...SAMPLE_REPORT, cost_summary: { candidate_cost_usd: 0.3, judge_cost_usd: 0.02, total_cost_usd: 0.32 } };
    expect(toRunRow(report).costUsd).toBeCloseTo(0.32);
  });
});

function row(over: Partial<RunRow>): RunRow {
  return {
    runId: over.runId ?? "r", heading: over.heading ?? "h", isSample: false, isQuick: false,
    verb: "Winner", winnerLabel: "w", winnerProviderId: "p", winnerPrivacy: "cloud",
    passRate: over.passRate ?? null, passText: null, scoredBy: "Contains",
    datasetName: "d", costUsd: over.costUsd ?? 0, createdAt: over.createdAt ?? "2026-06-20T00:00:00Z",
    configHash: "abc", ...over,
  };
}

describe("sortRunRows", () => {
  const A = row({ runId: "a", heading: "alpha", passRate: 0.4, costUsd: 0.03, createdAt: "2026-06-20T00:00:00Z" });
  const B = row({ runId: "b", heading: "bravo", passRate: 0.8, costUsd: 0.01, createdAt: "2026-06-25T00:00:00Z" });
  const Q = row({ runId: "q", heading: "quick", passRate: null, costUsd: 0.0, createdAt: "2026-06-22T00:00:00Z" });
  const ROWS = [B, Q, A]; // newest-first server order

  const ids = (rs: RunRow[]) => rs.map((r) => r.runId);

  test("default (column null) preserves server order untouched", () => {
    expect(sortRunRows(ROWS, DEFAULT_RUN_SORT)).toBe(ROWS);
    expect(ids(sortRunRows(ROWS, DEFAULT_RUN_SORT))).toEqual(["b", "q", "a"]);
  });

  test("passRate desc puts highest first, null (quick) last in BOTH directions", () => {
    expect(ids(sortRunRows(ROWS, { column: "passRate", direction: "desc" }))).toEqual(["b", "a", "q"]);
    expect(ids(sortRunRows(ROWS, { column: "passRate", direction: "asc" }))).toEqual(["a", "b", "q"]);
  });

  test("costUsd asc cheapest first", () => {
    expect(ids(sortRunRows(ROWS, { column: "costUsd", direction: "asc" }))).toEqual(["q", "b", "a"]);
  });

  test("createdAt desc newest first", () => {
    expect(ids(sortRunRows(ROWS, { column: "createdAt", direction: "desc" }))).toEqual(["b", "q", "a"]);
  });

  test("heading asc A→Z", () => {
    expect(ids(sortRunRows(ROWS, { column: "heading", direction: "asc" }))).toEqual(["a", "b", "q"]);
  });
});

describe("nextRunSort", () => {
  test("a fresh column adopts its natural first-click direction", () => {
    expect(nextRunSort(DEFAULT_RUN_SORT, "passRate")).toEqual({ column: "passRate", direction: "desc" });
    expect(nextRunSort(DEFAULT_RUN_SORT, "costUsd")).toEqual({ column: "costUsd", direction: "asc" });
  });
  test("clicking the active column flips direction", () => {
    expect(nextRunSort({ column: "passRate", direction: "desc" }, "passRate")).toEqual({ column: "passRate", direction: "asc" });
  });
});
