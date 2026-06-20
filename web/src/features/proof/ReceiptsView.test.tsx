import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { ReceiptsView } from "./ReceiptsView";
import { SAMPLE_REPORT } from "../../test/fixtures";
import { mockFetchByUrl, renderWithQuery } from "../../test/renderWithQuery";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockRuns(runs: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(
    mockFetchByUrl({ runs }) as typeof fetch,
  );
}

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
