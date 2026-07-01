import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import { Leaderboard } from "./Leaderboard";
import type { LeaderboardEntry } from "../../lib/api";

function entry(over: Partial<LeaderboardEntry>): LeaderboardEntry {
  return {
    candidate_id: "c", label: "Cand", provider_id: "ollama", privacy: "local",
    total: 5, pass_count: 4, pass_rate: 0.8, avg_score: 0.8, avg_latency_ms: 100,
    total_estimated_cost_usd: 0.01, failure_count: 1, error_count: 0,
    recommended: false, cost_per_quality: 0.0125, ...over,
  };
}

test("medals decorate the top 3 only when a winner exists", () => {
  const entries = [
    entry({ candidate_id: "a", recommended: true, pass_rate: 1, pass_count: 5, failure_count: 0 }),
    entry({ candidate_id: "b" }),
    entry({ candidate_id: "c" }),
    entry({ candidate_id: "d" }),
  ];
  render(<Leaderboard entries={entries} />);
  expect(screen.getByText("🥇")).toBeInTheDocument();
  expect(screen.getByText("🥈")).toBeInTheDocument();
  expect(screen.getByText("🥉")).toBeInTheDocument();
});

test("no medals in the no-winner state — plain rank numbers", () => {
  const entries = [
    entry({ candidate_id: "a", recommended: false, pass_rate: 0.2, pass_count: 1, failure_count: 4 }),
    entry({ candidate_id: "b", recommended: false }),
  ];
  const { container } = render(<Leaderboard entries={entries} />);
  expect(container.textContent).not.toContain("🥇");
  // The rank cell is the first <td> of each row — plain sequential numbers, no medals.
  const rankCells = [...container.querySelectorAll("tbody tr")].map(
    (tr) => tr.querySelector("td")!.textContent,
  );
  expect(rankCells).toEqual(["1", "2"]);
});

test("score bar uses the traffic-light status token for the pass rate, never the accent", () => {
  const { container } = render(
    <Leaderboard entries={[entry({ pass_rate: 0.2, pass_count: 1, failure_count: 4 })]} />,
  );
  // A <0.5 pass rate paints the bar danger — a status token, never the accent. The accent does now
  // appear elsewhere on the table (the sortable header controls), so scope the check to the bar fill
  // itself: status ≠ action stays intact for the data viz.
  const bar = container.querySelector(".h-full.rounded-full")!;
  expect(bar.className).toContain("bg-(--color-danger)");
  expect(bar.className).not.toContain("--color-accent");
});

test("$/quality cell renders Free / em-dash / value", () => {
  // Give every row BOTH throughput values AND a sampling descriptor so the only em-dash on screen
  // is the null $/quality cell (the throughput + sampling columns otherwise also render "—").
  const tok = {
    tokens_per_second: 10,
    warm_tokens_per_second: 10,
    sampling: { temperature: 0, mode: "deterministic" as const },
  };
  render(
    <Leaderboard
      entries={[
        entry({ candidate_id: "free", cost_per_quality: 0, ...tok }),
        entry({ candidate_id: "none", cost_per_quality: null, ...tok }),
        entry({ candidate_id: "paid", cost_per_quality: 0.004, ...tok }),
      ]}
    />,
  );
  expect(screen.getByText("Free")).toBeInTheDocument();
  expect(screen.getByText("—")).toBeInTheDocument();
  expect(screen.getByText("$0.0040")).toBeInTheDocument();
});

test("throughput splits into warm + e2e columns; each cell is its value or an em-dash", () => {
  // Honesty fix (proof-tokps-diluted-not-warm-decode): a local row carries warm-decode AND
  // end-to-end; a cloud row has no decode timing → warm shows "—" while e2e still renders.
  render(
    <Leaderboard
      entries={[
        entry({
          candidate_id: "local",
          warm_tokens_per_second: 59.0,
          tokens_per_second: 19.7,
          sampling: { temperature: 0, mode: "deterministic" },
        }),
        entry({
          candidate_id: "cloud",
          privacy: "cloud",
          warm_tokens_per_second: null,
          tokens_per_second: 72.4,
          sampling: { temperature: null, mode: "provider_default" },
        }),
      ]}
    />,
  );
  // Both throughput columns are present with their distinct headers.
  expect(screen.getByText("warm tok/s")).toBeInTheDocument();
  expect(screen.getByText("e2e tok/s")).toBeInTheDocument();
  // The local row's warm + e2e values both render; the cloud row's e2e renders.
  expect(screen.getByText("59.0")).toBeInTheDocument();
  expect(screen.getByText("19.7")).toBeInTheDocument();
  expect(screen.getByText("72.4")).toBeInTheDocument();
  // The cloud row's warm cell is the only em-dash (no decode timing); sampling cells are filled.
  expect(screen.getByText("—")).toBeInTheDocument();
});

test("sampling column discloses Deterministic / Sampled / em-dash per candidate", () => {
  // Honesty (cloud-provider-determinism-audit): a pinned local model reads "Deterministic"; a
  // cloud model on provider defaults reads "Sampled"; a candidate with no descriptor shows "—".
  // Fill throughput on every row so the ONLY em-dash on screen is the mock row's sampling cell.
  const tok = { tokens_per_second: 10, warm_tokens_per_second: 10 };
  render(
    <Leaderboard
      entries={[
        entry({
          candidate_id: "local",
          ...tok,
          sampling: { temperature: 0, mode: "deterministic" },
        }),
        entry({
          candidate_id: "cloud",
          privacy: "cloud",
          provider_id: "anthropic",
          ...tok,
          sampling: { temperature: null, mode: "provider_default" },
        }),
        entry({ candidate_id: "mock", ...tok, sampling: null }),
      ]}
    />,
  );
  // The column header is present, and each mode renders its distinct label.
  expect(screen.getByText("Sampling")).toBeInTheDocument();
  expect(screen.getByText("Deterministic")).toBeInTheDocument();
  expect(screen.getByText("Sampled")).toBeInTheDocument();
  // The descriptor-less (mock) row shows an em-dash rather than a fabricated mode.
  expect(screen.getByText("—")).toBeInTheDocument();
});

test("sampling chip never uses the accent or ok token (disclosure ≠ control/PASS)", () => {
  const { container } = render(
    <Leaderboard
      entries={[entry({ sampling: { temperature: 0, mode: "deterministic" } })]}
    />,
  );
  const chip = screen.getByText("Deterministic").closest("span")!;
  expect(chip.className).not.toContain("--color-accent");
  expect(chip.className).not.toContain("--color-ok");
  // It wears the neutral identity surface, matching the Cloud/Local tags.
  expect(chip.className).toContain("--color-panel-line");
  expect(container).toBeTruthy();
});

// ── WS-F F2/F3: sortable + mono-microcap headers ───────────────────────────────────────────────

function rankLabels(container: HTMLElement): string[] {
  // The Candidate label is the second <td> of each row; return them in render order.
  return [...container.querySelectorAll("tbody tr")].map(
    (tr) => tr.querySelectorAll("td")[1].textContent!.replace("Recommended", "").trim(),
  );
}

test("headers wear the reference mono micro-caps voice (F3)", () => {
  render(<Leaderboard entries={[entry({})]} />);
  // Every column header carries the mono / 10px / uppercase / wide-tracking treatment.
  const passRate = screen.getByText("Pass rate").closest("th")!;
  expect(passRate.className).toContain("font-mono");
  expect(passRate.className).toContain("text-[10px]");
  expect(passRate.className).toContain("uppercase");
  expect(passRate.className).toContain("tracking-[0.06em]");
  // The non-sortable identity/rank headers share the voice too.
  const provider = screen.getByText("Provider").closest("th")!;
  expect(provider.className).toContain("font-mono");
});

test("defaults to the server ranking on load — aria-sort none, no transient sort (F2)", () => {
  const entries = [
    entry({ candidate_id: "a", label: "alpha", recommended: true, pass_rate: 1, pass_count: 5 }),
    entry({ candidate_id: "b", label: "bravo", pass_rate: 0.6, pass_count: 3 }),
    entry({ candidate_id: "c", label: "charlie", pass_rate: 0.4, pass_count: 2 }),
  ];
  const { container } = render(<Leaderboard entries={entries} />);
  // No column is active → all headers report aria-sort="none".
  for (const th of container.querySelectorAll("th[aria-sort]")) {
    expect(th.getAttribute("aria-sort")).toBe("none");
  }
  // Rows render in the given (ranking) order, untouched.
  expect(rankLabels(container)).toEqual(["alpha", "bravo", "charlie"]);
});

test("clicking a header sorts the rows and sets aria-sort; clicking again flips it (F2)", () => {
  const entries = [
    entry({ candidate_id: "a", label: "alpha", pass_rate: 0.4, pass_count: 2 }),
    entry({ candidate_id: "b", label: "bravo", pass_rate: 0.8, pass_count: 4 }),
    entry({ candidate_id: "c", label: "charlie", pass_rate: 0.6, pass_count: 3 }),
  ];
  const { container } = render(<Leaderboard entries={entries} />);
  const passHeaderBtn = screen.getByRole("button", { name: /Pass rate/ });

  // First click → desc (highest first), aria-sort descending.
  fireEvent.click(passHeaderBtn);
  expect(passHeaderBtn.closest("th")!.getAttribute("aria-sort")).toBe("descending");
  expect(rankLabels(container)).toEqual(["bravo", "charlie", "alpha"]);

  // Second click → asc (lowest first).
  fireEvent.click(passHeaderBtn);
  expect(passHeaderBtn.closest("th")!.getAttribute("aria-sort")).toBe("ascending");
  expect(rankLabels(container)).toEqual(["alpha", "charlie", "bravo"]);
});

test("medals are suppressed once the user sorts a column (the verdict order is left behind)", () => {
  const entries = [
    entry({ candidate_id: "a", label: "alpha", recommended: true, pass_rate: 1, pass_count: 5, failure_count: 0 }),
    entry({ candidate_id: "b", label: "bravo", pass_rate: 0.6, pass_count: 3 }),
    entry({ candidate_id: "c", label: "charlie", pass_rate: 0.4, pass_count: 2 }),
  ];
  const { container } = render(<Leaderboard entries={entries} />);
  // Default ranking shows the gold medal.
  expect(within(container).getByText("🥇")).toBeInTheDocument();
  // Sort by est. cost → medals gone, plain rank numbers.
  fireEvent.click(screen.getByRole("button", { name: /Est\. cost/ }));
  expect(container.textContent).not.toContain("🥇");
  const rankCells = [...container.querySelectorAll("tbody tr")].map(
    (tr) => tr.querySelector("td")!.textContent,
  );
  expect(rankCells).toEqual(["1", "2", "3"]);
});

test("the active sort header uses the accent (it is a control, not a status)", () => {
  render(<Leaderboard entries={[entry({}), entry({ candidate_id: "b" })]} />);
  const btn = screen.getByRole("button", { name: /Avg score/ });
  fireEvent.click(btn);
  expect(btn.className).toContain("text-(--color-accent)");
});
