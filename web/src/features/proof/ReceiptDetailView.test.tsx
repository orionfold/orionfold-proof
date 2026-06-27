import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ReceiptDetailView } from "./ReceiptDetailView";
import { SAMPLE_REPORT } from "../../test/fixtures";
import { type ProofReport, type ResultRow } from "../../lib/api";

// R1b: the L3 detail view is a TABBED IA — Receipt · Run config · Leaderboard · Cost · Failure
// cases — so no single panel needs the long vertical scroll the old one-page scroll had. The
// Receipt tab is the default; the analysis tabs (Leaderboard/Cost/Failures) only exist for a
// scored run. The receipt artifact stays a sandboxed iframe (security unchanged), just maximized.

test("opens on the Receipt tab: sandboxed iframe + downloads", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  // Receipt tab is selected by default.
  expect(screen.getByRole("tab", { name: /Receipt/ })).toHaveAttribute("aria-selected", "true");

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

// The tabs split the record so each panel fits the fold. The full set for a scored run:
test("a scored run exposes Receipt, Run config, Leaderboard, Cost and Failure cases tabs", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  for (const name of [/Receipt/, /Run config/, /Leaderboard/, /Cost/, /Failure cases/]) {
    expect(screen.getByRole("tab", { name })).toBeInTheDocument();
  }
});

test("Run config tab shows the repro spine the old Inspector carried", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  fireEvent.click(screen.getByRole("tab", { name: /Run config/ }));
  expect(screen.getByRole("heading", { name: "Run config" })).toBeInTheDocument();
  expect(screen.getAllByText("a1b2c3d4e5f6").length).toBeGreaterThan(0);
  expect(screen.getByText("Dataset")).toBeInTheDocument();
  expect(screen.getByText("Rubric")).toBeInTheDocument();
});

test("Leaderboard tab names the recommended candidate (and Cost tab is its own panel)", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  fireEvent.click(screen.getByRole("tab", { name: /Leaderboard/ }));
  expect(screen.getAllByText("Mock · good").length).toBeGreaterThan(0);

  // Cost lives on its own tab now (the operator split it off the leaderboard tab so neither
  // panel needs a vertical scroll).
  fireEvent.click(screen.getByRole("tab", { name: /Cost/ }));
  expect(screen.getByRole("region", { name: /Run cost/i })).toBeInTheDocument();
});

const QUICK_REPORT: ProofReport = {
  ...SAMPLE_REPORT,
  run: { ...SAMPLE_REPORT.run, mode: "quick" },
  leaderboard: [],
};

test("a quick-compare run omits the analysis tabs (no scoring)", () => {
  render(<ReceiptDetailView report={QUICK_REPORT} onBack={() => {}} onExplore={() => {}} />);

  // The receipt artifact + run config still apply, but there's no leaderboard/cost/failures to
  // mine when the run wasn't scored.
  expect(screen.getByRole("tab", { name: /Receipt/ })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /Run config/ })).toBeInTheDocument();
  expect(screen.queryByRole("tab", { name: /Leaderboard/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("tab", { name: /^Cost/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("tab", { name: /Failure cases/ })).not.toBeInTheDocument();
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

test("the Failure cases tab reveals a selected case's input/expected/output detail", () => {
  render(<ReceiptDetailView report={REPORT_WITH_FAILURE} onBack={() => {}} onExplore={() => {}} />);

  fireEvent.click(screen.getByRole("tab", { name: /Failure cases/ }));
  // The failure-case browser is interactive — clicking a row shows its detail (the detail view
  // owns the selection locally; no App lift needed).
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

  fireEvent.click(screen.getByRole("tab", { name: /Run config/ }));
  expect(screen.getByText("Hardware")).toBeInTheDocument();
  expect(screen.getByText(/Apple M3 Max · Ollama/)).toBeInTheDocument();
  // No telemetry → no "CPU peak" line.
  expect(screen.queryByText(/CPU peak/)).not.toBeInTheDocument();
});
