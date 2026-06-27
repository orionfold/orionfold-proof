import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ReceiptDetailView } from "./ReceiptDetailView";
import { SAMPLE_REPORT } from "../../test/fixtures";
import { type ProofReport, type ResultRow } from "../../lib/api";

test("renders the receipt artifact in a sandboxed iframe with downloads", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  const frame = screen.getByTitle("Proof Receipt preview");
  expect(frame.getAttribute("src")).toContain("/api/runs/run_abc123def456/receipt.html?inline=1");
  expect(frame).toHaveAttribute("sandbox");

  for (const label of ["Markdown", "HTML", "JSON"]) {
    expect(screen.getByRole("link", { name: label })).toHaveAttribute(
      "href",
      expect.stringContaining("/api/runs/run_abc123def456/receipt."),
    );
  }
});

test("the preview iframe pins the cockpit's resolved theme", () => {
  // Pin an explicit choice so this asserts the iframe reflects the resolved theme, independent
  // of the first-run default (which is dark).
  localStorage.setItem("orionfold-theme", "light");
  try {
    render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);
    const frame = screen.getByTitle("Proof Receipt preview");
    expect(frame.getAttribute("src")).toContain("theme=light");
  } finally {
    localStorage.removeItem("orionfold-theme");
  }
});

test("fires onExplore and onBack from the nav buttons", () => {
  const onBack = vi.fn();
  const onExplore = vi.fn();
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={onBack} onExplore={onExplore} />);

  fireEvent.click(screen.getByRole("button", { name: /Explore in cockpit/ }));
  expect(onExplore).toHaveBeenCalledWith(SAMPLE_REPORT);

  fireEvent.click(screen.getByRole("button", { name: /Receipts/ }));
  expect(onBack).toHaveBeenCalled();
});

// Slice 5: the L3 detail view absorbs the old right Inspector. It now carries the full record —
// config + hardware, the leaderboard/frontier/cost for a scored run, and the failure cases — so
// nothing the side panel showed is lost when it's deleted.

test("shows the run-config provenance the old Inspector carried", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  // Run config stanza with the repro spine.
  expect(screen.getByRole("heading", { name: "Run config" })).toBeInTheDocument();
  // Config hash appears in the stanza (the header also references it; both is fine).
  expect(screen.getAllByText("a1b2c3d4e5f6").length).toBeGreaterThan(0);
  expect(screen.getByText("Dataset")).toBeInTheDocument();
  expect(screen.getByText("Rubric")).toBeInTheDocument();
});

test("renders the leaderboard, frontier and cost for a scored run", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  // The leaderboard names the recommended candidate; the failure-cases section is present.
  expect(screen.getAllByText("Mock · good").length).toBeGreaterThan(0);
  expect(screen.getByRole("region", { name: /Failure cases/i })).toBeInTheDocument();
});

const QUICK_REPORT: ProofReport = {
  ...SAMPLE_REPORT,
  run: { ...SAMPLE_REPORT.run, mode: "quick" },
  leaderboard: [],
};

test("omits the leaderboard block for a quick-compare run (no scoring)", () => {
  render(<ReceiptDetailView report={QUICK_REPORT} onBack={() => {}} onExplore={() => {}} />);

  // The receipt artifact + config still render, but there's no Failure cases region to mine when
  // there's no scored leaderboard.
  expect(screen.getByTitle("Proof Receipt preview")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Run config" })).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: /Failure cases/i })).not.toBeInTheDocument();
});

const FAILED_ROW: ResultRow = {
  candidate_id: "mock_good",
  example_index: 0,
  input_text: "Summarize Q3 memo",
  expected_text: "revenue up 12%",
  output_text: "revenue flat",
  score: 0.1,
  passed: false,
  latency_ms: 20,
  estimated_cost_usd: 0,
  input_tokens: 0,
  output_tokens: 0,
  judge_cost_usd: 0,
  judge_latency_ms: 0,
  privacy: "local",
  error: null,
};

const REPORT_WITH_FAILURE: ProofReport = {
  ...SAMPLE_REPORT,
  results: [FAILED_ROW],
};

test("selecting a failure case reveals its input/expected/output detail", () => {
  render(<ReceiptDetailView report={REPORT_WITH_FAILURE} onBack={() => {}} onExplore={() => {}} />);

  // The failure-case browser is interactive in the standalone detail view — clicking a row shows
  // its detail (the detail view owns the selection locally; no App lift needed).
  fireEvent.click(screen.getByText(/Summarize Q3 memo/));
  expect(screen.getByText("revenue up 12%")).toBeInTheDocument();
  expect(screen.getByText("revenue flat")).toBeInTheDocument();
});

const UNSAMPLED_REPORT: ProofReport = {
  ...SAMPLE_REPORT,
  host: {
    chip: "Apple M3 Max",
    arch: "arm64",
    cpu_cores: 16,
    memory_gb: 64,
    os_label: "macOS 15.0",
    gpu_label: null,
    local_runtime: "Ollama",
  },
  telemetry: null,
};

test("hardware stanza is honest when the run was not sampled (no peaks)", () => {
  render(<ReceiptDetailView report={UNSAMPLED_REPORT} onBack={() => {}} onExplore={() => {}} />);

  expect(screen.getByText("Hardware")).toBeInTheDocument();
  expect(screen.getByText(/Apple M3 Max · Ollama/)).toBeInTheDocument();
  // No telemetry → no "CPU peak" line.
  expect(screen.queryByText(/CPU peak/)).not.toBeInTheDocument();
});
