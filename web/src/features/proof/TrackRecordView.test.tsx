import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import type { Dataset, TrackRecordEntry, TrackRecordGroup } from "../../lib/api";
import { TrackRecordView } from "./TrackRecordView";

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../../lib/api")>("../../lib/api");
  return { ...actual, getTrackRecord: vi.fn(), getDatasets: vi.fn() };
});
import { getDatasets, getTrackRecord } from "../../lib/api";

function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TrackRecordView />
    </QueryClientProvider>,
  );
}

function entry(over: Partial<TrackRecordEntry> & { candidate_id: string }): TrackRecordEntry {
  return {
    label: over.candidate_id,
    provider_id: "mock_good",
    privacy: "cloud",
    runs: 1,
    total_examples: 10,
    total_passes: 5,
    pass_rate: 0.5,
    avg_cost_usd: 0,
    times_recommended: 0,
    ...over,
  };
}

const DATASETS: Dataset[] = [
  { id: "triage", name: "Support ticket triage", description: "", examples: [] },
  { id: "extract", name: "Contract extraction", description: "", examples: [] },
];

const GROUP: TrackRecordGroup = {
  dataset_id: "triage",
  dataset_name: "Support ticket triage",
  rubric_kind: "exact",
  runs: 4,
  entries: [
    entry({
      candidate_id: "claude-haiku-4-5",
      runs: 4,
      total_examples: 20,
      total_passes: 17,
      pass_rate: 0.85,
      times_recommended: 3,
    }),
    entry({
      candidate_id: "gpt-5.4-nano",
      runs: 4,
      total_examples: 20,
      total_passes: 12,
      pass_rate: 0.6,
      times_recommended: 1,
    }),
  ],
};

describe("TrackRecordView", () => {
  test("renders a comparable slice with its rubric label, run count, and pooled pass-rate", async () => {
    vi.mocked(getDatasets).mockResolvedValue(DATASETS);
    vi.mocked(getTrackRecord).mockResolvedValue([GROUP]);
    renderView();

    // Section header reads dataset · rubric label · run count.
    expect(await screen.findByRole("heading", { name: "Support ticket triage" })).toBeInTheDocument();
    expect(screen.getByText(/Exact match · 4 runs/)).toBeInTheDocument();

    // The pooled pass-rate is shown as a percentage, plus the raw passed/total tally.
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("17/20 examples passed")).toBeInTheDocument();
  });

  test("the best candidate is listed first and surfaces its won count", async () => {
    vi.mocked(getDatasets).mockResolvedValue(DATASETS);
    vi.mocked(getTrackRecord).mockResolvedValue([GROUP]);
    renderView();

    await screen.findByText("claude-haiku-4-5");
    const rows = screen.getAllByRole("listitem");
    // Server order is preserved (best pooled pass-rate first); the view never re-sorts.
    expect(within(rows[0]).getByText("claude-haiku-4-5")).toBeInTheDocument();
    expect(within(rows[1]).getByText("gpt-5.4-nano")).toBeInTheDocument();
    // "won N×" only appears for candidates that were recommended at least once.
    expect(within(rows[0]).getByText(/won 3×/)).toBeInTheDocument();
  });

  test("choosing a dataset narrows the query to that dataset id", async () => {
    vi.mocked(getDatasets).mockResolvedValue(DATASETS);
    vi.mocked(getTrackRecord).mockResolvedValue([GROUP]);
    renderView();

    await screen.findByRole("heading", { name: "Support ticket triage" });
    fireEvent.change(screen.getByLabelText(/filter track record by dataset/i), {
      target: { value: "extract" },
    });

    // The filtered fetch passes the chosen dataset id (queryKey changes → refetch).
    await waitFor(() => expect(getTrackRecord).toHaveBeenCalledWith("extract"));
  });

  test("an empty rollup shows a calm build-up-your-history notice, not an error", async () => {
    vi.mocked(getDatasets).mockResolvedValue(DATASETS);
    vi.mocked(getTrackRecord).mockResolvedValue([]);
    renderView();

    expect(await screen.findByText(/No track record yet/i)).toBeInTheDocument();
  });
});
