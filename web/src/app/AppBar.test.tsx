import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { AppBar } from "./AppBar";
import { mockFetchByUrl, renderWithQuery } from "../test/renderWithQuery";

const HEALTH = { status: "ok", service: "orionfold-proof", version: "0.2.0" };

afterEach(() => {
  vi.restoreAllMocks();
});

function mockHealth() {
  vi.spyOn(globalThis, "fetch").mockImplementation(
    mockFetchByUrl({ health: HEALTH }) as typeof fetch,
  );
}

test("renders the four standing tabs", () => {
  mockHealth();
  renderWithQuery(<AppBar view="proof" onNavigate={() => {}} />);
  for (const label of ["Prove", "Datasets", "Receipts", "Settings"]) {
    expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
  }
});

test("marks the active tab with aria-current", () => {
  mockHealth();
  renderWithQuery(<AppBar view="datasets" onNavigate={() => {}} />);
  expect(screen.getByRole("button", { name: "Datasets" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("button", { name: "Prove" })).not.toHaveAttribute("aria-current");
});

test("fires onNavigate with the tab's id when clicked", () => {
  mockHealth();
  const onNavigate = vi.fn();
  renderWithQuery(<AppBar view="proof" onNavigate={onNavigate} />);
  fireEvent.click(screen.getByRole("button", { name: "Receipts" }));
  expect(onNavigate).toHaveBeenCalledWith("receipts");
});

test("shows the connected engine status once health resolves", async () => {
  mockHealth();
  renderWithQuery(<AppBar view="proof" onNavigate={() => {}} />);
  await waitFor(() => expect(screen.getByText(/Connected/)).toBeInTheDocument());
  expect(screen.getByText(/v0\.2\.0/)).toBeInTheDocument();
});
