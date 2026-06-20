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
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
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

test("syncs the Task name to the selected dataset until the user edits it", async () => {
  const TWO_DATASETS = [
    DATASETS[0],
    {
      id: "client-memo-summaries",
      name: "Client memo summaries v1",
      description: "imported",
      examples: [{ input_text: "in", expected_text: "out" }],
    },
  ];
  vi.spyOn(globalThis, "fetch").mockImplementation(
    mockFetchByUrl({
      health: HEALTH,
      datasets: TWO_DATASETS,
      candidates: CANDIDATES,
      runs: [],
    }) as typeof fetch,
  );
  renderWithQuery(<App />);

  const taskName = (await screen.findByLabelText("Task name")) as HTMLInputElement;
  // Defaults to the first (pre-selected) dataset's name, not a hardcoded string.
  expect(taskName.value).toBe("Investment memo summarization");

  // Selecting another dataset re-syncs the untouched Task name to its name.
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "client-memo-summaries" } });
  expect(taskName.value).toBe("Client memo summaries v1");

  // Once the user edits the Task name, it stops auto-syncing on dataset change.
  fireEvent.change(taskName, { target: { value: "My own task" } });
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "investment-memo-summarization" },
  });
  expect(taskName.value).toBe("My own task");
});

test("theme switcher persists a choice and sets data-theme", async () => {
  mockServer();
  renderWithQuery(<App />);
  const dark = await screen.findByRole("radio", { name: "Dark" });
  fireEvent.click(dark);
  expect(dark).toHaveAttribute("aria-checked", "true");
  expect(localStorage.getItem("orionfold-theme")).toBe("dark");
  expect(document.documentElement.dataset.theme).toBe("dark");
});

test("opens a receipt into its detail view, then explores it in the cockpit", async () => {
  mockServer();
  renderWithQuery(<App />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Run proof/ })).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Receipts" }));
  const card = await screen.findByRole("button", { name: /Which model should I trust/ });
  fireEvent.click(card);

  // The receipt detail view renders the artifact; the archive list is gone.
  const frame = await screen.findByTitle("Proof Receipt preview");
  expect(frame).toHaveAttribute("src", expect.stringContaining("receipt.html?inline=1"));
  expect(screen.queryByLabelText("Past proof runs")).not.toBeInTheDocument();

  // Explore in cockpit loads the run into the workspace.
  fireEvent.click(screen.getByRole("button", { name: /Explore in cockpit/ }));
  await waitFor(() =>
    expect(screen.getByRole("region", { name: "Leaderboard" })).toBeInTheDocument(),
  );
});
