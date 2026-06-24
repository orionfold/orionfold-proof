// GENERATED — DO NOT EDIT. Run `uv run orionfold codegen` to regenerate.
// Canonical source: src/orionfold/scoring/rubric.py (DEFAULT_THRESHOLDS).
// Per-kind default passing threshold (0..1). Similarity is lenient (0.55 — paraphrased
// summaries score low on lexical overlap; 0.80 wrongly reads them as "no winner");
// keypoint/judge stay strict (0.80). A backend test freezes these values + asserts this
// file matches the Python map byte-for-byte.

export type TunableKind = "similarity" | "keypoint" | "judge";

export const DEFAULT_THRESHOLDS: Record<TunableKind, number> = {
  similarity: 0.55,
  keypoint: 0.8,
  judge: 0.8,
};
