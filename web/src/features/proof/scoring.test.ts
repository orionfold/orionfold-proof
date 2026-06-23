import { describe, it, expect } from "vitest";
import { resolveAutoKind, filterJudgeModels, defaultJudgeCell, prefersSampleJudge, cheapCloudCandidates, DEFAULT_THRESHOLDS, thresholdFor } from "./scoring";
import type { JudgeCell } from "./scoring";
import type { Dataset, SelectionPanel } from "../../lib/api";

describe("DEFAULT_THRESHOLDS / thresholdFor", () => {
  it("mirrors the backend map (similarity lenient, keypoint/judge strict)", () => {
    // MUST agree with src/orionfold/scoring/rubric.py DEFAULT_THRESHOLDS (backend test freezes it).
    expect(DEFAULT_THRESHOLDS).toEqual({ similarity: 0.55, keypoint: 0.8, judge: 0.8 });
  });
  it("falls back to the map when no override is set", () => {
    expect(thresholdFor("similarity")).toBe(0.55);
    expect(thresholdFor("keypoint", {})).toBe(0.8);
  });
  it("prefers a persisted override over the map", () => {
    expect(thresholdFor("similarity", { similarity: 0.7 })).toBe(0.7);
  });
});

function ds(keypoints: string[][], check_hint?: string): Dataset {
  return {
    id: "d",
    name: "D",
    description: "",
    check_hint,
    examples: keypoints.map((kp) => ({ input_text: "i", expected_text: "e", keypoints: kp })),
  };
}

describe("resolveAutoKind", () => {
  it("returns keypoint when any example has keypoints", () => {
    expect(resolveAutoKind(ds([[], ["22%"]]))).toBe("keypoint");
  });
  it("returns similarity when no example has keypoints", () => {
    expect(resolveAutoKind(ds([[], []]))).toBe("similarity");
  });
  it("returns similarity for an undefined dataset", () => {
    expect(resolveAutoKind(undefined)).toBe("similarity");
  });
  // B: check-hint → scoring kind (mirrors backend _HINT_KIND).
  it("maps an exact hint to exact", () => {
    expect(resolveAutoKind(ds([[], []], "exact"))).toBe("exact");
  });
  it("maps a numeric hint to exact (normalized equality)", () => {
    expect(resolveAutoKind(ds([[], []], "numeric"))).toBe("exact");
  });
  it("maps a substring hint to contains", () => {
    expect(resolveAutoKind(ds([[], []], "substring"))).toBe("contains");
  });
  it("leaves eyeball and empty hints on the heuristic", () => {
    expect(resolveAutoKind(ds([[], []], "eyeball"))).toBe("similarity");
    expect(resolveAutoKind(ds([[], []], ""))).toBe("similarity");
  });
  it("lets an explicit hint win over the keypoint heuristic", () => {
    expect(resolveAutoKind(ds([["x"]], "exact"))).toBe("exact");
  });
});

function model(over: Partial<import("../../lib/api").SelectionModel> = {}) {
  return {
    candidate_id: "c", model: "m", display_name: "M", tier: "economy" as const,
    cost_class: "$" as const, context_window: null, latest: false, recommended: false, ...over,
  };
}
const panel: SelectionPanel = {
  providers: [
    { provider_id: "mock_good", label: "Mock", privacy: "local", available: true, supports_custom: false, candidate_id: null, models: [] },
    { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
      models: [model({ model: "llama-eco", display_name: "Llama eco", tier: "economy", recommended: true })] },
    { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
      models: [
        model({ model: "haiku", display_name: "Haiku", tier: "economy", recommended: true }),
        model({ model: "opus", display_name: "Opus", tier: "frontier", latest: true }),
      ] },
    { provider_id: "openai", label: "OpenAI", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
  ],
};

describe("filterJudgeModels", () => {
  it("defaults Local+Cheapest to keyless Mock judge", () => {
    const r = filterJudgeModels(panel, "local", "economy");
    expect(r.options[0]).toMatchObject({ providerId: "mock_judge", model: null });
    // Mock judge is the keyless default for Local+Cheapest even when a recommended local model exists.
    expect(r.defaultProviderId).toBe("mock_judge");
    expect(r.defaultModel).toBeNull();
  });
  it("excludes mock_good / mock_bad from options", () => {
    const r = filterJudgeModels(panel, "local", "economy");
    expect(r.options.some((o) => o.providerId === "mock_good")).toBe(false);
  });
  it("filters Hosted+Cheapest to economy cloud models and prefers a recommended default", () => {
    const r = filterJudgeModels(panel, "cloud", "economy");
    expect(r.options.map((o) => o.model)).toEqual(["haiku"]);
    expect(r.defaultProviderId).toBe("anthropic");
    expect(r.defaultModel).toBe("haiku");
  });
  it("falls back to latest when no recommended survives the tier filter", () => {
    const r = filterJudgeModels(panel, "cloud", "frontier");
    expect(r.defaultModel).toBe("opus");
  });
  it("lists unavailable cloud providers as gated (key needed)", () => {
    const r = filterJudgeModels(panel, "cloud", "economy");
    expect(r.gated).toEqual([{ providerId: "openai", label: "OpenAI", keyName: "OPENAI_API_KEY" }]);
  });
  it("returns no options for an empty local Best combo", () => {
    const r = filterJudgeModels(panel, "local", "frontier");
    expect(r.options).toEqual([]);
    expect(r.defaultProviderId).toBeNull();
  });
  // Issue-2 guard: when the first-listed recommended cloud provider (Anthropic) has NO key, it must
  // become a gated hint-row, never the selected default — the Hosted default must land on a keyed
  // provider, so the judge step can't auto-pick a model that will error for a missing key.
  it("never defaults Hosted to an unavailable provider; picks the keyed one instead", () => {
    const noAnthropicKey: SelectionPanel = {
      providers: [
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
        { provider_id: "openai", label: "OpenAI", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
          models: [model({ model: "gpt-eco", display_name: "GPT eco", tier: "economy", recommended: true })] },
      ],
    };
    const r = filterJudgeModels(noAnthropicKey, "cloud", "economy");
    expect(r.defaultProviderId).toBe("openai");
    expect(r.defaultModel).toBe("gpt-eco");
    expect(r.options.some((o) => o.providerId === "anthropic")).toBe(false);
    expect(r.gated).toEqual([{ providerId: "anthropic", label: "Anthropic", keyName: "ANTHROPIC_API_KEY" }]);
  });
});

// A3: where the LLM-judge step opens. Sandbox OFF must NOT silently land on Mock when a real judge
// exists — it picks Hosted + a real cloud judge (or Local + Ollama). Sandbox ON keeps the keyless
// Mock judge. No real judge + Sandbox OFF → null (the judge method is disabled with a hint).
describe("defaultJudgeCell", () => {
  it("Sandbox ON: keeps the keyless Local+Cheapest Mock judge even with a cloud key", () => {
    const cell = defaultJudgeCell(panel, true);
    expect(cell).toEqual({ privacy: "local", tier: "economy", providerId: "mock_judge", model: null });
  });

  it("Sandbox OFF + cloud key: defaults to Hosted + a real cloud judge (never Mock)", () => {
    const cell = defaultJudgeCell(panel, false);
    expect(cell?.privacy).toBe("cloud");
    expect(cell?.providerId).toBe("anthropic");
    expect(cell?.model).toBe("haiku");
    expect(cell?.providerId).not.toBe("mock_judge");
  });

  it("Sandbox OFF, no cloud key but a real local judge: defaults Local to the real model (not Mock)", () => {
    const localOnly: SelectionPanel = {
      providers: [
        { provider_id: "mock_good", label: "Mock", privacy: "local", available: true, supports_custom: false, candidate_id: null, models: [] },
        { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
          models: [model({ model: "llama-eco", display_name: "Llama eco", tier: "economy", recommended: true })] },
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
      ],
    };
    const cell = defaultJudgeCell(localOnly, false);
    expect(cell).toEqual({ privacy: "local", tier: "economy", providerId: "ollama", model: "llama-eco" });
  });

  it("Sandbox OFF, no real judge at all: returns null (LLM judge disabled)", () => {
    const noJudge: SelectionPanel = {
      providers: [
        { provider_id: "mock_good", label: "Mock", privacy: "local", available: true, supports_custom: false, candidate_id: null, models: [] },
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
      ],
    };
    expect(defaultJudgeCell(noJudge, false)).toBeNull();
  });

  it("undefined panel: returns null (nothing selectable yet)", () => {
    expect(defaultJudgeCell(undefined, false)).toBeNull();
  });
});

// The bundled summarization demo grades free-form paraphrase, which lexical Similarity/Keypoint
// scores ~0 ("no winner") at any threshold — so the demo should default to the LLM judge when one
// is actually available. `prefersSampleJudge` is the pure gate: only the sample dataset, only when a
// real judge cell resolved (never undefined/null — that would mean no judge is configured).
describe("prefersSampleJudge", () => {
  const realCell: JudgeCell = { privacy: "cloud", tier: "economy", providerId: "anthropic", model: "haiku" };
  function sample(is_sample: boolean | undefined): Dataset {
    return { id: "sample-investment-memo", name: "Sample", description: "", is_sample, examples: [] };
  }

  it("prefers the judge for the sample dataset when a real judge cell resolved", () => {
    expect(prefersSampleJudge(sample(true), realCell)).toBe(true);
  });
  it("does not prefer the judge for a non-sample dataset", () => {
    expect(prefersSampleJudge(sample(false), realCell)).toBe(false);
  });
  it("does not prefer the judge when is_sample is absent", () => {
    expect(prefersSampleJudge(sample(undefined), realCell)).toBe(false);
  });
  it("does not prefer the judge for an undefined dataset", () => {
    expect(prefersSampleJudge(undefined, realCell)).toBe(false);
  });
  it("does not prefer the judge before the judge cell resolves (undefined)", () => {
    expect(prefersSampleJudge(sample(true), undefined)).toBe(false);
  });
  it("does not prefer the judge when no real judge is configured (null)", () => {
    // Sandbox OFF + no key/host → defaultJudgeCell returns null; the sample must NOT silently use Mock.
    expect(prefersSampleJudge(sample(true), null)).toBe(false);
  });
  it("does not prefer the judge when the resolved cell is the Mock judge (Sandbox ON)", () => {
    // In Sandbox the existing keyless demo already shows a clear winner; the real-judge default is
    // strictly for real-model runs. A mock_judge cell (Sandbox ON) must leave the sample on Auto.
    const mockCell: JudgeCell = { privacy: "local", tier: "economy", providerId: "mock_judge", model: null };
    expect(prefersSampleJudge(sample(true), mockCell)).toBe(false);
  });
});

// The guided first-run CTA (WS-E2) needs two cheap, available CLOUD candidates. cheapCloudCandidates
// scans available cloud providers cheapest-first and returns the first N distinct candidate ids.
describe("cheapCloudCandidates", () => {
  it("returns the two cheapest available cloud candidates, cheapest cost class first", () => {
    const p: SelectionPanel = {
      providers: [
        { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
          models: [model({ candidate_id: "local-1", cost_class: "free" })] },
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
          models: [
            model({ candidate_id: "a-cheap", cost_class: "$" }),
            model({ candidate_id: "a-dear", cost_class: "$$$" }),
          ] },
        { provider_id: "openai", label: "OpenAI", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
          models: [model({ candidate_id: "o-mid", cost_class: "$$" })] },
      ],
    };
    // Cheapest two cloud by cost class: a-cheap ($) then o-mid ($$); the $$$ and the local one are skipped.
    expect(cheapCloudCandidates(p)).toEqual(["a-cheap", "o-mid"]);
  });
  it("excludes local providers entirely (cloud-only — the CTA promises real cloud models)", () => {
    const p: SelectionPanel = {
      providers: [
        { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
          models: [model({ candidate_id: "local-free", cost_class: "free" })] },
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
          models: [model({ candidate_id: "a-only", cost_class: "$" })] },
      ],
    };
    // Only one cloud candidate exists, so we return just it — the caller requires exactly 2 to show the CTA.
    expect(cheapCloudCandidates(p)).toEqual(["a-only"]);
  });
  it("skips unavailable cloud providers (no key configured)", () => {
    const p: SelectionPanel = {
      providers: [
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
        { provider_id: "openai", label: "OpenAI", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
          models: [model({ candidate_id: "o-1", cost_class: "$" }), model({ candidate_id: "o-2", cost_class: "$$" })] },
      ],
    };
    expect(cheapCloudCandidates(p)).toEqual(["o-1", "o-2"]);
  });
  it("prefers recommended then latest within the same cost class", () => {
    const p: SelectionPanel = {
      providers: [
        { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
          models: [
            model({ candidate_id: "plain", cost_class: "$" }),
            model({ candidate_id: "rec", cost_class: "$", recommended: true }),
            model({ candidate_id: "new", cost_class: "$", latest: true }),
          ] },
      ],
    };
    expect(cheapCloudCandidates(p)).toEqual(["rec", "new"]);
  });
  it("returns [] for an undefined panel", () => {
    expect(cheapCloudCandidates(undefined)).toEqual([]);
  });
});
