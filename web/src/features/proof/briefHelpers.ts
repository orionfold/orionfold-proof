// Pure logic for keeping the Proof Brief's decision question honest (WS-C).
//
// The decision question headlines the receipt, so it must never silently contradict the
// dataset (Models/Prompts modes) or the ad-hoc prompt (Quick mode). Two surfaces, one rule:
// don't carry a question that no longer matches what's under test.

const MAX_HEADLINE = 120;

// Models/Prompts mode: the question follows the dataset until the user takes ownership of it,
// symmetric to task-name auto-sync. An untouched question CLEARS on dataset change (we have no
// dataset→question mapping to re-derive from), so the field falls back to its placeholder rather
// than showing a question authored for a different dataset.
export function effectiveDecisionQuestion(
  decisionQuestion: string,
  touched: boolean,
): string {
  return touched ? decisionQuestion : "";
}

// Quick mode has no dataset to anchor a title, so the only honest headline is the prompt the user
// actually typed. Collapse whitespace and trim to a sensible headline length; empty stays empty so
// QuickCompare falls back to the task name.
export function quickDecisionHeadline(quickPrompt: string): string {
  const collapsed = quickPrompt.replace(/\s+/g, " ").trim();
  if (collapsed.length <= MAX_HEADLINE) return collapsed;
  return collapsed.slice(0, MAX_HEADLINE - 1).trimEnd() + "…";
}
