// Shared metadata about cloud providers that require an API key to become available.
// Used by CandidatePicker and ScoringMethod to show inline KeyEntry prompts.
export const CLOUD_KEY_NAMES: Record<string, string> = {
  anthropic: "ANTHROPIC_API_KEY",
  openai: "OPENAI_API_KEY",
  openrouter: "OPENROUTER_API_KEY",
  gemini: "GEMINI_API_KEY",
};
