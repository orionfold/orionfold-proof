import { describe, expect, it } from "vitest";
import { recipesPanelSchema } from "./api";

describe("recipesPanelSchema", () => {
  it("parses a resolved recipe with candidate ids and unmet selectors", () => {
    const panel = recipesPanelSchema.parse({
      recipes: [
        {
          id: "cost-vs-quality",
          title: "Cost vs quality",
          subtitle: "Economy vs frontier",
          decision_question: "Which model?",
          candidate_ids: ["anthropic:claude-haiku-4-5"],
          resolved: [
            {
              label: "Economy",
              candidate_id: "anthropic:claude-haiku-4-5",
              display_name: "Claude Haiku 4.5",
              provider_id: "anthropic",
              cost_class: "$",
            },
          ],
          unmet: [
            {
              label: "Frontier",
              needs_provider_id: "anthropic",
              needs_provider_label: "Anthropic",
              key_name: "ANTHROPIC_API_KEY",
            },
          ],
        },
      ],
    });
    expect(panel.recipes[0].candidate_ids).toEqual(["anthropic:claude-haiku-4-5"]);
    expect(panel.recipes[0].unmet[0].key_name).toBe("ANTHROPIC_API_KEY");
  });
});
