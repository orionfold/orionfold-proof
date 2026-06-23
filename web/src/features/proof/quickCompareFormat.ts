// Pure presentation helpers for the quick-compare head-to-head. No score logic — a quick
// check is unscored; these only normalize objective metrics (latency / cost / tokens) and
// describe the recorded human pick.

/** Width fraction (0..1) of an objective bar; zero-safe so a 0 max never divides. */
export function objectiveBar(value: number, max: number): number {
  if (max <= 0) return 0;
  return Math.min(1, Math.max(0, value / max));
}

/** Total tokens for a result row — input + output. */
export function totalTokens(row: { input_tokens: number; output_tokens: number }): number {
  return row.input_tokens + row.output_tokens;
}
