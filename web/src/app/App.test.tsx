import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";
import { SAMPLE_REPORT } from "../test/fixtures";
import { mockFetchByUrl, renderWithQuery } from "../test/renderWithQuery";

const HEALTH = { status: "ok", service: "orionfold-proof", version: "0.1.0" };
const DATASETS = [
  {
    id: "investment-memo-summarization",
    name: "Investment memo summarization",
    description: "demo",
    examples: [{ input_text: "in", expected_text: "out" }],
  },
];
const CANDIDATES = [
  { id: "mock_good", label: "Mock · good", provider_id: "mock_good", privacy: "local" },
  { id: "mock_bad", label: "Mock · bad", provider_id: "mock_bad", privacy: "local" },
];

afterEach(() => {
  vi.restoreAllMocks();
});

function mockServer(runs: unknown = [SAMPLE_REPORT]) {
  vi.spyOn(globalThis, "fetch").mockImplementation(
    mockFetchByUrl({
      health: HEALTH,
      datasets: DATASETS,
      candidates: CANDIDATES,
      runs,
    }) as typeof fetch,
  );
}

test("renders the brand heading", () => {
  mockServer();
  renderWithQuery(<App />);
  expect(screen.getByRole("heading", { name: "Orionfold Proof" })).toBeInTheDocument();
});

test("shows the connected engine when health succeeds", async () => {
  mockServer();
  renderWithQuery(<App />);
  await waitFor(() => expect(screen.getByText(/Connected/)).toBeInTheDocument());
  expect(screen.getByText(/v0\.1\.0/)).toBeInTheDocument();
});

test("renders the proof setup with a Run button once datasets load", async () => {
  mockServer();
  renderWithQuery(<App />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Run proof/ })).toBeInTheDocument(),
  );
  // Both candidates are offered.
  expect(screen.getByText("Mock · good")).toBeInTheDocument();
  expect(screen.getByText("Mock · bad")).toBeInTheDocument();
});

test("navigates to the Datasets view from the rail", async () => {
  mockServer();
  renderWithQuery(<App />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Run proof/ })).toBeInTheDocument(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Datasets" }));
  // The view's own heading appears (distinct from the nav button).
  expect(screen.getByRole("heading", { name: "Datasets" })).toBeInTheDocument();
});

test("opens a past run from Receipts back into the cockpit", async () => {
  mockServer();
  renderWithQuery(<App />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Run proof/ })).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Receipts" }));
  const openButton = await screen.findByRole("button", {
    name: /Which model should I trust/,
  });
  fireEvent.click(openButton);

  // The selected run is now loaded in the cockpit: the leaderboard renders and the
  // receipts list is gone.
  await waitFor(() =>
    expect(screen.getByRole("region", { name: "Leaderboard" })).toBeInTheDocument(),
  );
  expect(screen.queryByLabelText("Past proof runs")).not.toBeInTheDocument();
});
