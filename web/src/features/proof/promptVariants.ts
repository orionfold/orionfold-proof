// Pure helpers for the "one model, N prompts" compare mode. No React, no network.
import type { PromptVariant, SelectionPanel } from "../../lib/api";

// Starter prompts the editor seeds so the first run is an edit, not a blank page. "Baseline"
// mirrors the server's TASK_SYSTEM_PROMPT so a variant run can include the current default.
export const STARTER_VARIANTS: PromptVariant[] = [
  {
    name: "Baseline",
    system_prompt:
      "Complete the task implied by the input. Respond with only the result — no preamble, labels, or explanation.",
  },
  {
    name: "Concise",
    system_prompt: "Answer in as few words as possible. Output only the essential result.",
  },
];

// A comparison needs at least two complete (name + prompt) variants.
export function validPromptVariants(vs: PromptVariant[]): boolean {
  return cleanVariants(vs).length >= 2;
}

// Trim and drop rows missing a name or prompt — the exact list the run request should carry.
export function cleanVariants(vs: PromptVariant[]): PromptVariant[] {
  return vs
    .map((v) => ({ name: v.name.trim(), system_prompt: v.system_prompt.trim() }))
    .filter((v) => v.name && v.system_prompt);
}

export interface ModelOption {
  candidateId: string;
  label: string;
  available: boolean;
}

// One selectable model per row: mocks (group candidate_id) + each catalog model.
export function flattenModels(panel: SelectionPanel | undefined): ModelOption[] {
  const out: ModelOption[] = [];
  for (const g of panel?.providers ?? []) {
    if (g.candidate_id) out.push({ candidateId: g.candidate_id, label: g.label, available: g.available });
    for (const m of g.models) {
      out.push({
        candidateId: m.candidate_id,
        label: `${g.label} · ${m.display_name}`,
        available: g.available,
      });
    }
  }
  return out;
}

// Prefer the first AVAILABLE option (keyless mocks come first) so prompt-compare runs keyless.
export function defaultPromptModel(panel: SelectionPanel | undefined): string {
  const opts = flattenModels(panel);
  return (opts.find((o) => o.available) ?? opts[0])?.candidateId ?? "";
}
