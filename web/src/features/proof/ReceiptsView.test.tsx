import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ReceiptsView } from "./ReceiptsView";
import { SAMPLE_REPORT } from "../../test/fixtures";
import { type ProofReport } from "../../lib/api";
import { mockFetchByUrl, renderWithQuery } from "../../test/renderWithQuery";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockRuns(runs: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(
    mockFetchByUrl({ runs }) as typeof fetch,
  );
}

// A quick-compare run is unscored ({kind:"none"}), so NOTHING is recommended in the
// leaderboard. The decided winner lives on run.chosen_winner (the human pick), not on a
// `recommended` flag — the list summary must read it from there.
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
    {
      candidate_id: "mock_bad", label: "Mock · bad", provider_id: "mock_bad", privacy: "local",
      total: 1, pass_count: 0, pass_rate: 0, avg_score: 0, avg_latency_ms: 159,
      total_estimated_cost_usd: 0, failure_count: 0, error_count: 0,
      recommended: false, cost_per_quality: null,
    },
  ],
};

test("lists a past run with its winner and three download links", async () => {
  mockRuns([SAMPLE_REPORT]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);

  await waitFor(() =>
    expect(
      screen.getByText("Which model should I trust for client memo summaries?"),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText("Mock · good")).toBeInTheDocument();
  expect(screen.getByText("100% (5/5)")).toBeInTheDocument();

  for (const label of ["Markdown", "HTML", "JSON"]) {
    const link = screen.getByRole("link", { name: label });
    expect(link).toHaveAttribute("href", expect.stringContaining("/api/runs/run_abc123def456/receipt."));
  }
});

test("shows the human pick for a quick-compare run instead of 'No clear winner'", async () => {
  mockRuns([QUICK_REPORT]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);

  await waitFor(() =>
    expect(
      screen.getByText("Which model should I trust for client memo summaries?"),
    ).toBeInTheDocument(),
  );
  // The decided pick — resolved to the candidate's label, matching the receipt detail.
  expect(screen.getByText(/Picked/)).toBeInTheDocument();
  expect(screen.getByText("Mock · good")).toBeInTheDocument();
  // The unscored leaderboard must NOT collapse to the misleading full-run fallback.
  expect(screen.queryByText("No clear winner")).not.toBeInTheDocument();
});

test("shows a tie for a quick-compare run with no clear pick", async () => {
  mockRuns([{ ...QUICK_REPORT, run: { ...QUICK_REPORT.run, chosen_winner: "tie" } }]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);

  await waitFor(() =>
    expect(
      screen.getByText("Which model should I trust for client memo summaries?"),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText(/Tie/)).toBeInTheDocument();
});

test("clicking a run calls onOpenReceipt with that report", async () => {
  mockRuns([SAMPLE_REPORT]);
  const onOpenReceipt = vi.fn();
  renderWithQuery(<ReceiptsView onOpenReceipt={onOpenReceipt} />);

  const heading = await screen.findByText(
    "Which model should I trust for client memo summaries?",
  );
  fireEvent.click(heading.closest("button")!);
  expect(onOpenReceipt).toHaveBeenCalledWith(SAMPLE_REPORT);
});

test("shows a calm empty state when there are no runs", async () => {
  mockRuns([]);
  renderWithQuery(<ReceiptsView onOpenReceipt={() => {}} />);
  await waitFor(() => expect(screen.getByText(/No proof runs yet/)).toBeInTheDocument());
  // No past-runs list is rendered.
  expect(screen.queryByLabelText("Past proof runs")).not.toBeInTheDocument();
  // Sanity: the within import is exercised by the title region.
  expect(within(screen.getByRole("main")).getByRole("heading", { name: "Receipts" })).toBeInTheDocument();
});
