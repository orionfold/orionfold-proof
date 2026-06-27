import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ReceiptsView } from "./ReceiptsView";
import { SAMPLE_REPORT } from "../../test/fixtures";
import { type CostRollup, type ProofReport } from "../../lib/api";
import { mockFetchByUrl, renderWithQuery } from "../../test/renderWithQuery";

afterEach(() => {
  vi.restoreAllMocks();
});

const EMPTY_ROLLUP: CostRollup = {
  window: "all",
  run_count: 0,
  eval_cost_usd: 0,
  judge_cost_usd: 0,
  total_cost_usd: 0,
  trend: [],
};

// The view + bento fetch runs, datasets, and both cost-summary windows. Route them all so no fetch
// rejects as unmocked. `cost-summary` matches both ?window=today and ?window=all via substring.
function mockAll(runs: unknown, opts: { datasets?: unknown; trackRecord?: unknown } = {}) {
  vi.spyOn(globalThis, "fetch").mockImplementation(
    mockFetchByUrl({
      "/api/runs": runs,
      "/api/datasets": opts.datasets ?? [],
      "/api/cost-summary": EMPTY_ROLLUP,
      "/api/track-record": opts.trackRecord ?? [],
    }) as typeof fetch,
  );
}

const QUICK_REPORT: ProofReport = {
  ...SAMPLE_REPORT,
  run: {
    ...SAMPLE_REPORT.run,
    id: "run_quick0001",
    rubric: { kind: "none", threshold: 0, case_sensitive: false },
    mode: "quick",
    chosen_winner: "mock_good",
    candidates: [
      { id: "mock_good", label: "Mock · good", provider_id: "mock_good", privacy: "local" },
      { id: "mock_bad", label: "Mock · bad", provider_id: "mock_bad", privacy: "local" },
    ],
  },
  leaderboard: [
    {
      candidate_id: "mock_good", label: "Mock · good", provider_id: "mock_good", privacy: "local",
      total: 1, pass_count: 0, pass_rate: 0, avg_score: 0, avg_latency_ms: 79,
      total_estimated_cost_usd: 0, failure_count: 0, error_count: 0,
      recommended: false, cost_per_quality: null,
    },
  ],
};

test("lists a past run in the Runs table with its verdict and download links", async () => {
  mockAll([SAMPLE_REPORT]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);

  // Heading appears in both the bento Latest-proof tile and the table row, so scope to the table.
  const table = await screen.findByRole("table");
  expect(
    within(table).getByText("Which model should I trust for client memo summaries?"),
  ).toBeInTheDocument();
  expect(within(table).getByText("100%")).toBeInTheDocument(); // tone-colored pass cell

  for (const label of ["MD", "HTML", "JSON"]) {
    const link = within(table).getByRole("link", { name: label });
    expect(link).toHaveAttribute("href", expect.stringContaining("/api/runs/run_abc123def456/receipt."));
  }
});

test("shows the human pick for a quick-compare run, never the recommended fallback", async () => {
  mockAll([QUICK_REPORT]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);

  const table = await screen.findByRole("table");
  expect(within(table).getByText("Picked")).toBeInTheDocument();
  expect(within(table).getByText("Mock · good")).toBeInTheDocument();
  expect(within(table).queryByText("No clear winner")).not.toBeInTheDocument();
});

test("shows a tie for a quick-compare run with no clear pick", async () => {
  mockAll([{ ...QUICK_REPORT, run: { ...QUICK_REPORT.run, chosen_winner: "tie" } }]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);

  const table = await screen.findByRole("table");
  expect(within(table).getByText("Tie")).toBeInTheDocument();
});

test("clicking a run's open arrow calls onOpenReceipt with that report", async () => {
  mockAll([SAMPLE_REPORT]);
  const onOpenReceipt = vi.fn();
  renderWithQuery(<ReceiptsView onOpenReceipt={onOpenReceipt} />);

  const open = await screen.findByRole("button", {
    name: /Open Which model should I trust/,
  });
  fireEvent.click(open);
  expect(onOpenReceipt).toHaveBeenCalledWith(SAMPLE_REPORT);
});

test("the Track Record toggle switches to the standings cards", async () => {
  mockAll([SAMPLE_REPORT], {
    trackRecord: [
      {
        dataset_id: "investment-memo-summarization",
        dataset_name: "Investment memo summarization",
        rubric_kind: "contains",
        runs: 2,
        entries: [
          {
            candidate_id: "mock_good", label: "Mock · good", provider_id: "mock_good",
            privacy: "local", runs: 2, total_examples: 10, total_passes: 9, pass_rate: 0.9,
            avg_cost_usd: 0, times_recommended: 2,
          },
        ],
      },
    ],
  });
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);

  await screen.findByRole("table"); // Runs mode is the default
  fireEvent.click(screen.getByRole("tab", { name: "Track Record" }));

  await waitFor(() => expect(screen.getByText("won 2×")).toBeInTheDocument());
  expect(screen.getByText("9/10 examples passed")).toBeInTheDocument();
  // The Runs table is gone in Track Record mode.
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

test("opens directly in Track Record mode when initialMode says so (rail drill-down)", async () => {
  mockAll([SAMPLE_REPORT], {
    trackRecord: [
      {
        dataset_id: "investment-memo-summarization",
        dataset_name: "Investment memo summarization",
        rubric_kind: "contains", runs: 2,
        entries: [
          {
            candidate_id: "mock_good", label: "Mock · good", provider_id: "mock_good",
            privacy: "local", runs: 2, total_examples: 10, total_passes: 9, pass_rate: 0.9,
            avg_cost_usd: 0, times_recommended: 0,
          },
        ],
      },
    ],
  });
  renderWithQuery(<ReceiptsView initialMode="track-record" onOpenReceipt={() => {}} />);

  await waitFor(() => expect(screen.getByText("9/10 examples passed")).toBeInTheDocument());
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
});

test("shows a calm empty state when there are no runs", async () => {
  mockAll([]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);
  await waitFor(() =>
    expect(screen.getByText(/No proof runs yet/)).toBeInTheDocument(),
  );
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  expect(within(screen.getByRole("main")).getByRole("heading", { name: "Receipts" })).toBeInTheDocument();
});
