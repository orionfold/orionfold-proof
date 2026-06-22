const TOKENS = ["t1", "t2", "t3", "t5", "t7"] as const;
export type TagToken = (typeof TOKENS)[number];

/** Stable per-label token from the categorical value palette. Presentation only — the value
 *  hues are never interactive (brand contract); tags stay squared. */
export function tagToken(label: string): TagToken {
  const key = label.trim().toLowerCase();
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  return TOKENS[hash % TOKENS.length];
}

/** Display-only check hints — suggest a rubric at run-setup; the engine never reads these. */
export const CHECK_HINTS: { value: string; label: string }[] = [
  { value: "", label: "No hint" },
  { value: "substring", label: "Contains text" },
  { value: "numeric", label: "Numeric match" },
  { value: "exact", label: "Exact match" },
  { value: "eyeball", label: "Eyeball / judgment" },
];

export function checkHintLabel(value: string | null | undefined): string {
  return CHECK_HINTS.find((h) => h.value === (value ?? ""))?.label ?? "";
}
