import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScoringMethod } from "./ScoringMethod";
import type { Dataset, SelectionPanel, Settings } from "../../lib/api";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ providers: [] })),
  getSettings: vi.fn(async () => ({ sandbox_enabled: false, powermetrics_gpu_optin: false, thresholds: { similarity: 0.55, keypoint: 0.8, judge: 0.8 } }) as Settings),
}));

import { getSelection, getSettings } from "../../lib/api";

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

const cloudPanel: SelectionPanel = {
  providers: [
    { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: true, supports_custom: true, candidate_id: null,
      models: [{ candidate_id: "anthropic:haiku", model: "haiku", display_name: "Haiku", tier: "economy", cost_class: "$", context_window: null, latest: false, recommended: true }] },
  ],
};
const kpDataset: Dataset = {
  id: "d", name: "D", description: "",
  examples: [{ input_text: "i", expected_text: "e", keypoints: ["22%"] }],
};
// The bundled summarization demo: keypoints present (Auto would pick Keypoint) but free-form
// paraphrase — so with a real judge it should default to the LLM judge instead.
const sampleDataset: Dataset = {
  id: "sample-investment-memo", name: "Sample · investment memo summarization", description: "",
  is_sample: true,
  examples: [{ input_text: "i", expected_text: "e", keypoints: ["22%"] }],
};

describe("ScoringMethod", () => {
  beforeEach(() => {
    // Reset to the file defaults so a per-test mockResolvedValue can't leak across tests.
    vi.mocked(getSelection).mockResolvedValue({ providers: [] });
    vi.mocked(getSettings).mockResolvedValue({ sandbox_enabled: false, powermetrics_gpu_optin: false, thresholds: { similarity: 0.55, keypoint: 0.8, judge: 0.8 } } as Settings);
  });

  it("renders the free group with Auto/Keypoint/Similarity and the paid LLM judge", () => {
    render(wrap(<ScoringMethod value={null} onChange={() => {}} dataset={kpDataset} />));
    expect(screen.getByRole("button", { name: /Auto/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Keypoint/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Similarity/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /LLM judge/i })).toBeInTheDocument();
  });

  it("shows what Auto resolves to for the dataset", () => {
    render(wrap(<ScoringMethod value={null} onChange={() => {}} dataset={kpDataset} />));
    expect(screen.getByText(/Keypoint coverage/i)).toBeInTheDocument();
  });

  it("emits a keypoint rubric when Keypoint is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    fireEvent.click(screen.getByRole("button", { name: /Keypoint/i }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "keypoint" }));
  });

  it("emits the lenient similarity default (0.55) from the built-in map", () => {
    // No settings fetch is mocked → the query stays pending and thresholdFor falls back to the map.
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    fireEvent.click(screen.getByRole("button", { name: /Similarity/i }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "similarity", threshold: 0.55 }),
    );
  });

  it("Sandbox OFF + no real judge: disables the LLM judge card with a hint (never silently Mock)", async () => {
    // Default mocks: sandbox off + empty panel → no real judge exists.
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    // Wait for the disabling hint to appear (queries resolved).
    expect(await screen.findByText(/add a provider key or start Ollama/i)).toBeInTheDocument();
    const judge = screen.getByRole("button", { name: /LLM judge/i });
    expect(judge).toBeDisabled();
    fireEvent.click(judge);
    expect(onChange).not.toHaveBeenCalled(); // disabled → no rubric emitted, no Mock fallback
  });

  it("clicking LLM judge before the panel loads never emits a stale Mock judge", async () => {
    // Cold load: a slow selection panel. Clicking judge immediately must NOT emit a guessed
    // mock_judge (which would diverge from the dropdown once the real panel commits).
    let resolvePanel: (p: SelectionPanel) => void = () => {};
    vi.mocked(getSelection).mockImplementationOnce(
      () => new Promise<SelectionPanel>((res) => { resolvePanel = res; }),
    );
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    const judge = screen.getByRole("button", { name: /LLM judge/i });
    fireEvent.click(judge); // panel still pending → no-op, no emission
    expect(onChange).not.toHaveBeenCalled();
    // Once the real panel arrives, a click emits the real judge (and never mock_judge).
    resolvePanel(cloudPanel);
    await vi.waitFor(() => {
      onChange.mockClear();
      fireEvent.click(judge);
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ judge_provider_id: "anthropic" }));
    });
    expect(onChange).not.toHaveBeenCalledWith(expect.objectContaining({ judge_provider_id: "mock_judge" }));
  });

  it("Sandbox OFF + cloud key: LLM judge defaults to a real cloud judge, not Mock", async () => {
    vi.mocked(getSelection).mockResolvedValue(cloudPanel);
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    const judge = await screen.findByRole("button", { name: /LLM judge/i });
    // Wait until the cloud panel has committed (a click emits the real cell). We click ONCE inside the
    // poll's success check but never clear onChange — so the post-assertion inspects the FULL call
    // history and proves mock_judge was never emitted at any point (the spec invariant), not just the
    // last iteration. Before ready the click is a no-op (judgeCell undefined), so no stale call lands.
    await vi.waitFor(() => {
      fireEvent.click(judge);
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ kind: "judge", judge_provider_id: "anthropic", judge_model: "haiku" }),
      );
    });
    expect(onChange).not.toHaveBeenCalledWith(expect.objectContaining({ judge_provider_id: "mock_judge" }));
  });

  it("sample dataset + real judge: auto-defaults to the LLM judge (not Auto/Keypoint)", async () => {
    // The bundled demo grades free-form paraphrase; lexical Similarity/Keypoint reads "no winner."
    // With a cloud key + Sandbox OFF, the Configure step should pre-select the LLM judge.
    vi.mocked(getSelection).mockResolvedValue(cloudPanel);
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={sampleDataset} />));
    await vi.waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ kind: "judge", judge_provider_id: "anthropic", judge_model: "haiku" }),
      );
    });
    // Never a guessed Mock, and never the keypoint fallback once a real judge resolved.
    expect(onChange).not.toHaveBeenCalledWith(expect.objectContaining({ judge_provider_id: "mock_judge" }));
    expect(onChange).not.toHaveBeenCalledWith(expect.objectContaining({ kind: "keypoint" }));
  });

  it("sample dataset but no real judge (Sandbox OFF, no key): stays on Auto, never auto-Mock", async () => {
    // Default mocks: empty panel → defaultJudgeCell is null. The sample must NOT silently switch to
    // a Mock judge; it stays Auto (which resolves to the keyless keypoint heuristic).
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={sampleDataset} />));
    expect(await screen.findByText(/add a provider key or start Ollama/i)).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("non-sample dataset: does NOT auto-default to the LLM judge", async () => {
    vi.mocked(getSelection).mockResolvedValue(cloudPanel);
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    // Let the panel + settings resolve; the auto-default effect would have fired by now if it applied.
    await screen.findByRole("button", { name: /LLM judge/i });
    await vi.waitFor(() => expect(vi.mocked(getSelection)).toHaveBeenCalled());
    expect(onChange).not.toHaveBeenCalledWith(expect.objectContaining({ kind: "judge" }));
  });

  it("sample dataset: a deliberate switch back to Auto is not clobbered by the auto-default", async () => {
    vi.mocked(getSelection).mockResolvedValue(cloudPanel);
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={sampleDataset} />));
    // First the auto-default lands on judge.
    await vi.waitFor(() => expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "judge" })));
    onChange.mockClear();
    // User deliberately picks Auto; the effect must not re-fire judge.
    fireEvent.click(screen.getByRole("button", { name: /Auto/i }));
    expect(onChange).toHaveBeenCalledWith(null);
    // Give any stray effect a chance to fire, then assert judge was never re-emitted.
    await Promise.resolve();
    expect(onChange).not.toHaveBeenCalledWith(expect.objectContaining({ kind: "judge" }));
  });

  it("Sandbox ON + sample dataset: does NOT auto-select the Mock judge (stays on the keyless demo)", async () => {
    vi.mocked(getSettings).mockResolvedValue({ sandbox_enabled: true, powermetrics_gpu_optin: false, thresholds: { similarity: 0.55, keypoint: 0.8, judge: 0.8 } } as Settings);
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={sampleDataset} />));
    const judge = await screen.findByRole("button", { name: /LLM judge/i });
    // Settings has resolved (judge button enabled in Sandbox); the auto-default must not have fired.
    await vi.waitFor(() => expect(judge).not.toBeDisabled());
    expect(onChange).not.toHaveBeenCalledWith(expect.objectContaining({ kind: "judge" }));
  });

  it("Sandbox ON: LLM judge offers the keyless Mock judge", async () => {
    vi.mocked(getSettings).mockResolvedValue({ sandbox_enabled: true, powermetrics_gpu_optin: false, thresholds: { similarity: 0.55, keypoint: 0.8, judge: 0.8 } } as Settings);
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    const judge = await screen.findByRole("button", { name: /LLM judge/i });
    // Poll until settings has committed (sandbox-on resolves judgeCell without the panel).
    await vi.waitFor(() => {
      fireEvent.click(judge);
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "judge", judge_provider_id: "mock_judge" }));
    });
    expect(await screen.findByText(/Mock judge/i)).toBeInTheDocument();
  });

  // ── v9: Governance bench card (deterministic, no threshold) ──────────────────────────
  const benchDataset: Dataset = {
    id: "advisor-curveball", name: "Advisor curveball", description: "", corpus_id: "ainative-field-notes",
    examples: [{ input_text: "q", expected_text: "", keypoints: [], expected_behavior: "refuse" }],
  };

  it("offers the Governance bench card for a bench dataset and auto-defaults to it", async () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={benchDataset} />));
    expect(await screen.findByRole("button", { name: /Governance bench/i })).toBeInTheDocument();
    // The bench latch fires once the dataset arrives → commits a bench rubric (threshold ignored).
    await vi.waitFor(() => {
      expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "bench" }));
    });
  });

  it("does NOT offer the Governance bench card for a non-bench dataset", () => {
    render(wrap(<ScoringMethod value={null} onChange={() => {}} dataset={kpDataset} />));
    expect(screen.queryByRole("button", { name: /Governance bench/i })).not.toBeInTheDocument();
  });
});
