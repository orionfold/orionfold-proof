import { screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";
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

function mockServer() {
  vi.spyOn(globalThis, "fetch").mockImplementation(
    mockFetchByUrl({
      health: HEALTH,
      datasets: DATASETS,
      candidates: CANDIDATES,
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
