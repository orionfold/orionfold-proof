import { screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { TelemetryRail } from "./TelemetryRail";
import { renderWithQuery } from "../test/renderWithQuery";

afterEach(() => vi.restoreAllMocks());

const HOST = {
  arch: "arm64",
  chip: "Apple M3 Max",
  cpu_cores: 16,
  memory_gb: 64,
  os_label: "macOS 15",
  local_runtime: "Ollama",
  gpu_label: null,
};

// Routes cost-summary by its window query (the shared mockFetchByUrl helper matches by substring,
// which can't tell the two windows apart), and serves the host profile.
function mockRail(today: unknown, all: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("cost-summary?window=today")) return Promise.resolve(new Response(JSON.stringify(today)));
    if (url.includes("cost-summary?window=all")) return Promise.resolve(new Response(JSON.stringify(all)));
    if (url.includes("telemetry/host")) return Promise.resolve(new Response(JSON.stringify(HOST)));
    return Promise.reject(new Error(`unmocked url: ${url}`));
  }) as typeof fetch);
}

function rollup(over: Record<string, unknown>) {
  return { window: "all", run_count: 0, eval_cost_usd: 0, judge_cost_usd: 0, total_cost_usd: 0, trend: [], ...over };
}

test("shows today's total with the eval+judge split and cumulative to-date", async () => {
  mockRail(
    rollup({ window: "today", run_count: 2, eval_cost_usd: 0.34, judge_cost_usd: 0.02, total_cost_usd: 0.36 }),
    rollup({ window: "all", run_count: 5, eval_cost_usd: 1.2, judge_cost_usd: 0.05, total_cost_usd: 1.25 }),
  );
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  await waitFor(() => expect(screen.getByText("$0.36")).toBeInTheDocument());
  // Split shown beneath today's total.
  expect(screen.getByText("0.34 + 0.02")).toBeInTheDocument();
  // Cumulative to-date rounds to whole dollars above $10? No — $1.25 keeps cents.
  expect(screen.getByText("$1.25")).toBeInTheDocument();
  expect(screen.getByText("5 runs")).toBeInTheDocument();
});

test("a loaded $0.00 is shown honestly (a real all-local spend), not '—'", async () => {
  mockRail(rollup({ window: "today", run_count: 1 }), rollup({ window: "all", run_count: 1 }));
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  await waitFor(() => expect(screen.getAllByText("$0.00").length).toBeGreaterThanOrEqual(2));
  // No judge spend → no split sub-line under today's cell.
  expect(screen.queryByText(/\+/)).not.toBeInTheDocument();
});
