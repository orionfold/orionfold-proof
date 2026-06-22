import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { QuickCompare } from "./QuickCompare";
import * as api from "../../lib/api";

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

function quickReport(): api.ProofReport {
  const cand = (id: string, label: string) => ({
    id, label, provider_id: "mock_good", privacy: "local" as const, model: null, system_prompt: null,
  });
  const row = (id: string, out: string, latency: number) => ({
    candidate_id: id, example_index: 0, input_text: "p", expected_text: "", output_text: out,
    score: null, passed: null, latency_ms: latency, estimated_cost_usd: 0, input_tokens: 5,
    output_tokens: 7, judge_cost_usd: 0, judge_latency_ms: 0, privacy: "local" as const, error: null,
  });
  const entry = (id: string, label: string, latency: number) => ({
    candidate_id: id, label, provider_id: "mock_good", privacy: "local" as const, model: null,
    system_prompt: null, total: 1, pass_count: 0, pass_rate: 0, avg_score: 0, avg_latency_ms: latency,
    total_estimated_cost_usd: 0, failure_count: 0, error_count: 0, recommended: false,
    cost_per_quality: null,
  });
  return {
    run: {
      id: "run_q",
      brief: { task_name: "T", decision_question: "Q", success_criteria: "" },
      dataset_id: "quick-compare", dataset_name: "Quick Compare",
      rubric: { kind: "none", threshold: 0, case_sensitive: false },
      candidates: [cand("a", "Alpha"), cand("b", "Beta")],
      config_hash: "abc", created_at: "2026-06-22T00:00:00Z", status: "complete",
      mode: "quick", chosen_winner: null,
    },
    leaderboard: [entry("a", "Alpha", 420), entry("b", "Beta", 980)],
    results: [row("a", "alpha output", 420), row("b", "beta output", 980)],
    cost_summary: { candidate_cost_usd: 0, judge_cost_usd: 0, total_cost_usd: 0 },
  } as api.ProofReport;
}

describe("QuickCompare", () => {
  it("renders both outputs and gates Save until a pick", () => {
    render(wrap(<QuickCompare report={quickReport()} onReport={vi.fn()} onPromote={vi.fn()} />));
    expect(screen.getByText("alpha output")).toBeInTheDocument();
    expect(screen.getByText("beta output")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save as proof receipt/i })).toBeDisabled();
  });

  it("saves the pick via patchWinner", async () => {
    const onReport = vi.fn();
    const picked = { ...quickReport(), run: { ...quickReport().run, chosen_winner: "a" } };
    const spy = vi.spyOn(api, "patchWinner").mockResolvedValue(picked as api.ProofReport);
    render(wrap(<QuickCompare report={quickReport()} onReport={onReport} onPromote={vi.fn()} />));
    fireEvent.click(screen.getByRole("button", { name: /alpha wins/i }));
    fireEvent.click(screen.getByRole("button", { name: /save as proof receipt/i }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith("run_q", "a"));
    await waitFor(() => expect(onReport).toHaveBeenCalledWith(picked));
  });
});
