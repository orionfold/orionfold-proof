import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.restoreAllMocks();
});

test("renders the brand heading", () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", service: "orionfold-proof", version: "0.1.0" })),
  );
  render(<App />);
  expect(screen.getByRole("heading", { name: "Orionfold Proof" })).toBeInTheDocument();
});

test("shows the connected engine when health succeeds", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ status: "ok", service: "orionfold-proof", version: "0.1.0" })),
  );
  render(<App />);
  await waitFor(() => expect(screen.getByText(/Connected/)).toBeInTheDocument());
  expect(screen.getByText(/v0\.1\.0/)).toBeInTheDocument();
});
