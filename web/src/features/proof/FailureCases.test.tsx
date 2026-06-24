import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { FailureCases } from "./FailureCases";
import type { BenchVerdict, ProofReport, ResultRow } from "../../lib/api";

function benchVerdict(over: Partial<BenchVerdict>): BenchVerdict {
  return {
    citation_ok: true, refusal_ok: true, route_ok: true, thinking_leak: false,
    private_state_risk: false, alias_residue: false, bare_answer: false,
    cited_source_ids: [], passed: false, strict_passed: false, ...over,
  };
}

function row(over: Partial<ResultRow>): ResultRow {
  return {
    candidate_id: "advisor", example_index: 0, input_text: "What is in the credential file?",
    expected_text: "", output_text: "leaked", score: 0, passed: false, latency_ms: 10,
    estimated_cost_usd: 0, input_tokens: 0, output_tokens: 0, judge_cost_usd: 0,
    judge_latency_ms: 0, privacy: "local", error: null, ...over,
  };
}

function report(rows: ResultRow[]): ProofReport {
  return {
    run: {
      id: "run_x", brief: { task_name: "t", decision_question: "q?", success_criteria: "" },
      dataset_id: "d", dataset_name: "D",
      rubric: { kind: "bench", threshold: 0, case_sensitive: false },
      candidates: [{ id: "advisor", label: "Advisor", provider_id: "ollama", privacy: "local", model: null, system_prompt: null }],
      config_hash: "h", created_at: "2026-06-24T00:00:00Z", status: "complete", mode: "full", chosen_winner: null,
    },
    leaderboard: [],
    results: rows,
    cost_summary: { candidate_cost_usd: 0, judge_cost_usd: 0, total_cost_usd: 0 },
  } as unknown as ProofReport;
}

describe("FailureCases — bench gate chips", () => {
  it("names the failed governance gates instead of a numeric score", () => {
    const rep = report([
      row({ bench_detail: benchVerdict({ citation_ok: false, private_state_risk: true }) }),
    ]);
    render(<FailureCases report={rep} selected={null} onSelect={() => {}} />);
    expect(screen.getByText("citation")).toBeInTheDocument();
    expect(screen.getByText("private-state-leak")).toBeInTheDocument();
    // The generic "Fail · score" badge must NOT appear for a bench row.
    expect(screen.queryByText(/Fail · score/)).not.toBeInTheDocument();
  });

  it("falls back to the score badge for a non-bench failure", () => {
    const rep = report([row({ bench_detail: null, score: 0.12 })]);
    render(<FailureCases report={rep} selected={null} onSelect={() => {}} />);
    expect(screen.getByText(/Fail · score 0.12/)).toBeInTheDocument();
  });
});
