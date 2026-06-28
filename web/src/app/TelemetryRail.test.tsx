import { screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { TelemetryRail } from "./TelemetryRail";
import { renderWithQuery } from "../test/renderWithQuery";
import { SAMPLE_REPORT } from "../test/fixtures";

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

const SETTINGS = {
  sandbox_enabled: true,
  powermetrics_gpu_optin: false,
  provider_max_retries: 2,
  thresholds: { similarity: 0.8, keypoint: 0.8, judge: 0.8 },
};

// Routes cost-summary by its window query (the shared mockFetchByUrl helper matches by substring,
// which can't tell the two windows apart), serves the host profile, the latest stored run (default
// null = empty store), settings (for the GPU opt-in gate), and gpu-idle. `opts` overrides settings
// + the gpu-idle reading, and exposes a counter so tests can assert the privileged read is gated.
function mockRail(
  today: unknown,
  all: unknown,
  latest: unknown = null,
  opts: { settings?: unknown; gpuIdle?: unknown } = {},
) {
  const counters = { gpuIdle: 0 };
  vi.spyOn(globalThis, "fetch").mockImplementation(((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("telemetry/gpu-idle")) {
      counters.gpuIdle += 1;
      return Promise.resolve(new Response(JSON.stringify(opts.gpuIdle ?? { gpu_util: null })));
    }
    if (url.includes("runs/latest")) return Promise.resolve(new Response(JSON.stringify(latest)));
    if (url.includes("cost-summary?window=today")) return Promise.resolve(new Response(JSON.stringify(today)));
    if (url.includes("cost-summary?window=all")) return Promise.resolve(new Response(JSON.stringify(all)));
    if (url.includes("telemetry/host")) return Promise.resolve(new Response(JSON.stringify(HOST)));
    if (url.includes("/api/settings")) return Promise.resolve(new Response(JSON.stringify(opts.settings ?? SETTINGS)));
    return Promise.reject(new Error(`unmocked url: ${url}`));
  }) as typeof fetch);
  return counters;
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

test("at rest with no in-memory report, Last result/receipt hydrate from the latest stored run", async () => {
  // lastReport is null (fresh page, nothing open in the cockpit) but a run exists in the store.
  mockRail(rollup({ window: "today" }), rollup({ window: "all" }), SAMPLE_REPORT);
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  // The recommended winner's pooled pass count + label, from the fetched latest run — not "—".
  await waitFor(() => expect(screen.getByText("5/5")).toBeInTheDocument());
  expect(screen.getByText("Mock · good")).toBeInTheDocument();
});

test("the in-memory report wins over the latest stored run when both are present", async () => {
  // A different run is open in the cockpit; it must take precedence over the at-rest fetch.
  const open = {
    ...SAMPLE_REPORT,
    leaderboard: [{ ...SAMPLE_REPORT.leaderboard[0], label: "Open · run", pass_count: 3, total: 4 }],
  };
  mockRail(rollup({ window: "today" }), rollup({ window: "all" }), SAMPLE_REPORT);
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={open} onOpenReceipts={() => {}} />,
  );
  await waitFor(() => expect(screen.getByText("3/4")).toBeInTheDocument());
  expect(screen.getByText("Open · run")).toBeInTheDocument();
  expect(screen.queryByText("5/5")).not.toBeInTheDocument();
});

test("at rest, the dimmed last-run sparkline is seeded from the stored run's trend series", async () => {
  const withTrend = {
    ...SAMPLE_REPORT,
    telemetry: {
      sampled: true,
      n_samples: 6,
      cpu_util_mean: 40,
      cpu_util_max: 70,
      mem_used_gb_max: 30,
      process_rss_gb_max: 8,
      gpu_util_mean: null,
      gpu_util_max: null,
      cpu_series: [20, 45, 70, 30],
      gpu_series: [],
      mem_series: [10, 12, 11, 14],
    },
  };
  mockRail(rollup({ window: "today" }), rollup({ window: "all" }), withTrend);
  const { container } = renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  // Once the latest-run fetch resolves, the CPU + memory cells draw a (dimmed) sparkline path; the
  // empty gpu_series draws nothing. Sparklines are the distinctively-sized 56×16 svgs (Lucide icons
  // are 24×24), so count those — at least 2 (CPU + Memory) appear from the persisted series.
  await waitFor(() => {
    const sparks = container.querySelectorAll('svg[width="56"] path[d]');
    expect(sparks.length).toBeGreaterThanOrEqual(2);
  });
});

test("at rest with neither an in-memory nor a stored run, Last result reads '—'", async () => {
  mockRail(rollup({ window: "today" }), rollup({ window: "all" }), null);
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  await waitFor(() => expect(screen.getByText("Host")).toBeInTheDocument());
  // Last result + Last receipt both honest "—" (at least 2 dashes among the cells).
  expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
});

test("at rest with the GPU opt-in OFF, the rail never reads gpu-idle and the cell stays 'unavailable'", async () => {
  const counters = mockRail(rollup({ window: "today" }), rollup({ window: "all" }), null, {
    settings: { ...SETTINGS, powermetrics_gpu_optin: false },
  });
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  await waitFor(() => expect(screen.getByText("Host")).toBeInTheDocument());
  // Give any (incorrect) poll a chance to fire, then assert it didn't.
  await new Promise((r) => setTimeout(r, 50));
  expect(counters.gpuIdle).toBe(0);
  expect(screen.getByText("unavailable")).toBeInTheDocument();
});

test("at rest with the GPU opt-in ON and the tab visible, the rail reads gpu-idle and shows the idle %", async () => {
  const counters = mockRail(rollup({ window: "today" }), rollup({ window: "all" }), null, {
    settings: { ...SETTINGS, powermetrics_gpu_optin: true },
    gpuIdle: { gpu_util: 21 },
  });
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  await waitFor(() => expect(screen.getByText("21%")).toBeInTheDocument());
  expect(counters.gpuIdle).toBeGreaterThanOrEqual(1);
  // With the opt-in on but a (transient) null reading the label would read "at rest", never
  // "unavailable" — but here we have a real %, so neither label shows.
  expect(screen.queryByText("unavailable")).not.toBeInTheDocument();
});

test("opt-in ON but a null reading shows 'at rest', not 'unavailable'", async () => {
  mockRail(rollup({ window: "today" }), rollup({ window: "all" }), null, {
    settings: { ...SETTINGS, powermetrics_gpu_optin: true },
    gpuIdle: { gpu_util: null },
  });
  renderWithQuery(
    <TelemetryRail runActive={false} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  // The GPU cell reads "at rest" (enabled, awaiting a sample) — like CPU — not "unavailable".
  await waitFor(() => expect(screen.getAllByText("at rest").length).toBeGreaterThanOrEqual(2));
  expect(screen.queryByText("unavailable")).not.toBeInTheDocument();
});

test("during a run, the rail does not poll gpu-idle (live SSE owns the GPU cell)", async () => {
  const counters = mockRail(rollup({ window: "today" }), rollup({ window: "all" }), null, {
    settings: { ...SETTINGS, powermetrics_gpu_optin: true },
    gpuIdle: { gpu_util: 21 },
  });
  renderWithQuery(
    <TelemetryRail runActive={true} runProgress={null} lastReport={null} onOpenReceipts={() => {}} />,
  );
  await waitFor(() => expect(screen.getByText("Host")).toBeInTheDocument());
  await new Promise((r) => setTimeout(r, 50));
  expect(counters.gpuIdle).toBe(0);
});
