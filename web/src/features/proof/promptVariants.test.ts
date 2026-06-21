import { describe, expect, it } from "vitest";
import type { SelectionPanel } from "../../lib/api";
import {
  STARTER_VARIANTS, validPromptVariants, cleanVariants, flattenModels, defaultPromptModel,
} from "./promptVariants";

const panel: SelectionPanel = {
  providers: [
    { provider_id: "mock_good", label: "Mock · good", privacy: "local", available: true,
      supports_custom: false, candidate_id: "mock_good", models: [] },
    { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false,
      supports_custom: true, candidate_id: null, models: [
        { candidate_id: "anthropic:claude-haiku-4-5", model: "claude-haiku-4-5",
          display_name: "Claude Haiku 4.5", tier: "balanced", cost_class: "$",
          context_window: null, latest: false, recommended: true } ] },
  ],
};

describe("promptVariants helpers", () => {
  it("ships two starter variants", () => {
    expect(STARTER_VARIANTS).toHaveLength(2);
    expect(STARTER_VARIANTS[0].name).toBe("Baseline");
  });

  it("requires two non-empty variants to be valid", () => {
    expect(validPromptVariants([{ name: "A", system_prompt: "x" }])).toBe(false);
    expect(validPromptVariants([{ name: "A", system_prompt: "x" }, { name: "B", system_prompt: " " }])).toBe(false);
    expect(validPromptVariants([{ name: "A", system_prompt: "x" }, { name: "B", system_prompt: "y" }])).toBe(true);
  });

  it("cleans out blank rows and trims", () => {
    expect(cleanVariants([{ name: " A ", system_prompt: " x " }, { name: "", system_prompt: "y" }]))
      .toEqual([{ name: "A", system_prompt: "x" }]);
  });

  it("flattens mocks + catalog models, carrying availability", () => {
    const opts = flattenModels(panel);
    expect(opts).toEqual([
      { candidateId: "mock_good", label: "Mock · good", available: true },
      { candidateId: "anthropic:claude-haiku-4-5", label: "Anthropic · Claude Haiku 4.5", available: false },
    ]);
  });

  it("defaults the prompt model to the first available option", () => {
    expect(defaultPromptModel(panel)).toBe("mock_good");
  });
});
