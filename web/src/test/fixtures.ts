import { type ProofReport } from "../lib/api";

// A minimal but schema-valid ProofReport for view tests — one recommended candidate, no result
// rows needed. Shaped to satisfy the Zod schemas in lib/api.ts so tests fail if the models drift.
export const SAMPLE_REPORT: ProofReport = {
  run: {
    id: "run_abc123def456",
    brief: {
      task_name: "Investment memo summarization",
      decision_question: "Which model should I trust for client memo summaries?",
      success_criteria: "",
    },
    dataset_id: "investment-memo-summarization",
    dataset_name: "Investment memo summarization",
    rubric: { kind: "contains", threshold: 0.5, case_sensitive: false },
    candidates: [
      { id: "mock_good", label: "Mock · good", provider_id: "mock_good", privacy: "local" },
    ],
    config_hash: "a1b2c3d4e5f6",
    created_at: "2026-06-20T09:00:00Z",
    status: "complete",
  },
  leaderboard: [
    {
      candidate_id: "mock_good",
      label: "Mock · good",
      provider_id: "mock_good",
      privacy: "local",
      total: 5,
      pass_count: 5,
      pass_rate: 1,
      avg_score: 1,
      avg_latency_ms: 12,
      total_estimated_cost_usd: 0,
      failure_count: 0,
      recommended: true,
    },
  ],
  results: [],
};
