// Pure presentation helpers for the leaderboard — unit-tested without rendering, so the
// thresholds and the $/quality display rule live in exactly one place.

// Traffic-light tone for a pass rate (0–1), mapped to STATUS tokens (never the cyan accent).
export type PassRateTone = "ok" | "warn" | "danger";

export function passRateTone(passRate: number): PassRateTone {
  if (passRate >= 0.8) return "ok";
  if (passRate >= 0.5) return "warn";
  return "danger";
}

// $/quality cell text: null/undefined → "—" (no quality to price), 0 → "Free" (local/mock),
// else "$0.0012" to 4 decimals. Mirrors the receipt's _cost_per_quality_label exactly.
export function formatCostPerQuality(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (v === 0) return "Free";
  return `$${v.toFixed(4)}`;
}

// Podium medal for a 0-based row index, only when a real winner exists; otherwise null.
export function medalFor(index: number, hasWinner: boolean): string | null {
  if (!hasWinner) return null;
  return ["🥇", "🥈", "🥉"][index] ?? null;
}
