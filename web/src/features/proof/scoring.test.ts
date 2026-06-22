import { describe, it, expect } from "vitest";
import { resolveAutoKind, filterJudgeModels } from "./scoring";
import type { Dataset, SelectionPanel } from "../../lib/api";

function ds(keypoints: string[][]): Dataset {
  return {
    id: "d",
    name: "D",
    description: "",
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
