import { describe, expect, test } from "vitest";

import type { LeaderboardEntry } from "../../lib/api";
import {
  ariaSortFor,
  DEFAULT_SORT,
  nextSort,
  sortEntries,
  type SortState,
} from "./leaderboardSort";

function entry(over: Partial<LeaderboardEntry>): LeaderboardEntry {
  return {
    candidate_id: over.candidate_id ?? "c",
    label: over.label ?? "model",
    provider_id: over.provider_id ?? "openai",
    privacy: over.privacy ?? "cloud",
    total: over.total ?? 5,
    pass_count: over.pass_count ?? 0,
    pass_rate: over.pass_rate ?? 0,
    avg_score: over.avg_score ?? 0,
    avg_latency_ms: over.avg_latency_ms ?? 0,
    total_estimated_cost_usd: over.total_estimated_cost_usd ?? 0,
    failure_count: over.failure_count ?? 0,
    error_count: over.error_count ?? 0,
    recommended: over.recommended ?? false,
    cost_per_quality: over.cost_per_quality,
  };
}

const A = entry({ candidate_id: "a", label: "alpha", pass_rate: 0.4, avg_score: 0.4, total_estimated_cost_usd: 0.03, avg_latency_ms: 300, failure_count: 3, cost_per_quality: 0.075 });
const B = entry({ candidate_id: "b", label: "bravo", pass_rate: 0.8, avg_score: 0.7, total_estimated_cost_usd: 0.01, avg_latency_ms: 100, failure_count: 1, cost_per_quality: 0.0125 });
const C = entry({ candidate_id: "c", label: "charlie", pass_rate: 0.6, avg_score: 0.5, total_estimated_cost_usd: 0.02, avg_latency_ms: 200, failure_count: 2, cost_per_quality: null });

const ENTRIES = [B, C, A]; // arrives in server ranking order (B recommended/top)

function ids(entries: LeaderboardEntry[]): string[] {
  return entries.map((e) => e.candidate_id);
}

describe("sortEntries", () => {
  test("the default (column: null) preserves the server ranking order untouched", () => {
    expect(sortEntries(ENTRIES, DEFAULT_SORT)).toBe(ENTRIES);
    expect(ids(sortEntries(ENTRIES, DEFAULT_SORT))).toEqual(["b", "c", "a"]);
  });

  test("pass_rate desc puts the highest pass rate first", () => {
    const sorted = sortEntries(ENTRIES, { column: "pass_rate", direction: "desc" });
    expect(ids(sorted)).toEqual(["b", "c", "a"]);
  });

  test("pass_rate asc reverses it", () => {
    const sorted = sortEntries(ENTRIES, { column: "pass_rate", direction: "asc" });
    expect(ids(sorted)).toEqual(["a", "c", "b"]);
  });

  test("est. cost asc puts the cheapest first", () => {
    const sorted = sortEntries(ENTRIES, { column: "total_estimated_cost_usd", direction: "asc" });
    expect(ids(sorted)).toEqual(["b", "c", "a"]);
  });

  test("label asc sorts A→Z", () => {
    const sorted = sortEntries(ENTRIES, { column: "label", direction: "asc" });
    expect(ids(sorted)).toEqual(["a", "b", "c"]); // alpha, bravo, charlie
  });

  test("null $/quality always sorts to the bottom, both directions", () => {
    // C has cost_per_quality null — it must land last whichever way the real numbers sort.
    const asc = sortEntries(ENTRIES, { column: "cost_per_quality", direction: "asc" });
    expect(ids(asc)).toEqual(["b", "a", "c"]); // 0.0125, 0.075, then null
    const desc = sortEntries(ENTRIES, { column: "cost_per_quality", direction: "desc" });
    expect(ids(desc)).toEqual(["a", "b", "c"]); // 0.075, 0.0125, then null
  });

  test("sort is stable — tied rows keep their given (ranking) order", () => {
    const t1 = entry({ candidate_id: "t1", pass_rate: 0.5 });
    const t2 = entry({ candidate_id: "t2", pass_rate: 0.5 });
    const t3 = entry({ candidate_id: "t3", pass_rate: 0.5 });
    const sorted = sortEntries([t1, t2, t3], { column: "pass_rate", direction: "desc" });
    expect(ids(sorted)).toEqual(["t1", "t2", "t3"]);
  });

  test("does not mutate the input array", () => {
    const input = [B, C, A];
    sortEntries(input, { column: "pass_rate", direction: "asc" });
    expect(ids(input)).toEqual(["b", "c", "a"]);
  });
});

describe("nextSort", () => {
  test("a fresh column adopts its natural first-click direction", () => {
    expect(nextSort(DEFAULT_SORT, "pass_rate")).toEqual({ column: "pass_rate", direction: "desc" });
    expect(nextSort(DEFAULT_SORT, "total_estimated_cost_usd")).toEqual({
      column: "total_estimated_cost_usd",
      direction: "asc",
    });
    expect(nextSort(DEFAULT_SORT, "label")).toEqual({ column: "label", direction: "asc" });
  });

  test("clicking the active column flips direction", () => {
    const s1: SortState = { column: "pass_rate", direction: "desc" };
    expect(nextSort(s1, "pass_rate")).toEqual({ column: "pass_rate", direction: "asc" });
    expect(nextSort({ column: "pass_rate", direction: "asc" }, "pass_rate")).toEqual({
      column: "pass_rate",
      direction: "desc",
    });
  });
});

describe("ariaSortFor", () => {
  test("returns none for inactive columns and the matching value for the active one", () => {
    const s: SortState = { column: "avg_score", direction: "desc" };
    expect(ariaSortFor("pass_rate", s)).toBe("none");
    expect(ariaSortFor("avg_score", s)).toBe("descending");
    expect(ariaSortFor("avg_score", { column: "avg_score", direction: "asc" })).toBe("ascending");
  });
});
