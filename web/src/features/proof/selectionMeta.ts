// Shared metadata about cloud providers that require an API key to become available.
// Used by CandidatePicker and ScoringMethod to show inline KeyEntry prompts.
export const CLOUD_KEY_NAMES: Record<string, string> = {
  anthropic: "ANTHROPIC_API_KEY",
  openai: "OPENAI_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
  gemini: "GEMINI_API_KEY",
};

// Per-method copy for the grouped scoring cards. `group` drives the free-vs-paid section.
export const METHOD_META = {
  auto: { label: "Auto", group: "free", cost: "Free", guidance: "We pick the right free check for your dataset." },
  exact: { label: "Exact", group: "free", cost: "Free", guidance: "Passes only on an exact match (whitespace/case-normalized). Best for labels and IDs." },
  keypoint: { label: "Keypoint", group: "free", cost: "Free", guidance: "Checks your authored key facts appear in the answer." },
  similarity: { label: "Similarity", group: "free", cost: "Free", guidance: "Scores by semantic closeness to the expected answer." },
  judge: { label: "LLM judge", group: "paid", cost: "$ per run · slower", guidance: "A model grades each answer against the expected one." },
} as const;

// The "Optimize" axis of the judge filter, ordered cheapest → best. Maps UI labels to catalog tiers.
export const JUDGE_TIERS = [
  { id: "economy", label: "Cheapest" },
  { id: "balanced", label: "Balanced" },
  { id: "frontier", label: "Best" },
] as const;
