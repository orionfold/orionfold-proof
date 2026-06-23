import { fireEvent, screen, waitFor } from "@testing-library/react";
import { expect, test, vi, beforeEach, afterEach } from "vitest";

import { renderWithQuery } from "../../test/renderWithQuery";
import { SettingsView } from "./SettingsView";

beforeEach(() => {
  const THRESHOLDS = { similarity: 0.55, keypoint: 0.8, judge: 0.8 };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const method = (init?.method ?? "GET").toUpperCase();
    if (String(url).endsWith("/api/settings") && method === "GET")
      return new Response(
        JSON.stringify({ sandbox_enabled: false, thresholds: THRESHOLDS }),
        { status: 200 },
      );
    if (String(url).endsWith("/api/settings") && method === "PUT")
      return new Response(
        JSON.stringify({ sandbox_enabled: true, thresholds: THRESHOLDS }),
        { status: 200 },
      );
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

test("renders a default-threshold slider per method showing persisted values", async () => {
  renderWithQuery(<SettingsView />);
  const similarity = await screen.findByRole("slider", { name: /Similarity default threshold/i });
  expect(similarity).toHaveValue("0.55");
  expect(screen.getByRole("slider", { name: /Keypoint default threshold/i })).toHaveValue("0.8");
  expect(screen.getByRole("slider", { name: /LLM judge default threshold/i })).toHaveValue("0.8");
});

test("committing a threshold slider PUTs the new defaults", async () => {
  renderWithQuery(<SettingsView />);
  const similarity = await screen.findByRole("slider", { name: /Similarity default threshold/i });
  fireEvent.change(similarity, { target: { value: "0.3" } });
  fireEvent.pointerUp(similarity);
  await waitFor(() =>
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/settings",
      expect.objectContaining({ method: "PUT" }),
    ),
  );
});

test("the appearance theme switcher persists a choice and sets data-theme", async () => {
  localStorage.removeItem("orionfold-theme");
  renderWithQuery(<SettingsView />);
  const light = await screen.findByRole("radio", { name: "Light" });
  fireEvent.click(light);
  expect(light).toHaveAttribute("aria-checked", "true");
  expect(localStorage.getItem("orionfold-theme")).toBe("light");
  expect(document.documentElement.dataset.theme).toBe("light");
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
