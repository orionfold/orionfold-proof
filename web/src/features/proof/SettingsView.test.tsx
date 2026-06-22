import { fireEvent, screen, waitFor } from "@testing-library/react";
import { expect, test, vi, beforeEach, afterEach } from "vitest";

import { renderWithQuery } from "../../test/renderWithQuery";
import { SettingsView } from "./SettingsView";

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const method = (init?.method ?? "GET").toUpperCase();
    if (String(url).endsWith("/api/settings") && method === "GET")
      return new Response(JSON.stringify({ sandbox_enabled: false }), { status: 200 });
    if (String(url).endsWith("/api/settings") && method === "PUT")
      return new Response(JSON.stringify({ sandbox_enabled: true }), { status: 200 });
    if (String(url).endsWith("/api/data") && method === "DELETE")
      return new Response(JSON.stringify({ datasets: 0, receipts: 0 }), { status: 200 });
    return new Response("{}", { status: 200 });
  });
});

afterEach(() => vi.restoreAllMocks());

test("renders the three data actions and the sandbox toggle", async () => {
  renderWithQuery(<SettingsView />);
  expect(await screen.findByRole("button", { name: /Seed sample data/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Remove sample data/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Clear all data/i })).toBeInTheDocument();
  expect(screen.getByRole("switch", { name: /Sandbox/i })).toBeInTheDocument();
});

test("Clear all data needs a second confirm step", async () => {
  renderWithQuery(<SettingsView />);
  const clear = await screen.findByRole("button", { name: /Clear all data/i });
  fireEvent.click(clear);
  // First click reveals an explicit Confirm; nothing destructive fired yet.
  const confirm = await screen.findByRole("button", { name: /Confirm clear/i });
  fireEvent.click(confirm);
  await waitFor(() =>
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/data",
      expect.objectContaining({ method: "DELETE" }),
    ),
  );
});
