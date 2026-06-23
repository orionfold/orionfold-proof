// Deterministic, rule-based plain-English explainer for the Decide step — pure,
// unit-tested, NO LLM call. Free + reproducible, so the receipt's repeatability
// promise holds even though this is a cockpit aid, not part of the proof artifact.
//
// It reads the finished leaderboard and names what the data shows: why everything
// failed, who actually leads on raw score, and what to try next. The point is to
// rescue the insight when the scorer is mismatched (pass rate collapses to 0 for
// everyone, but avg score still ranks the field — the 2026-06-23 3-tier case).

import type { LeaderboardEntry } from "../../lib/api";

// Tones map to STATUS / ink tokens only — never the cyan accent (DS split:
// accent is reserved for the recommended point on the scatter).
export type InsightTone = "ok" | "warn" | "info";

export interface DecideInsight {
  headline: string;
  detail: string;
  tone: InsightTone;
}

// Rule thresholds — all named here so the branches read as policy, not magic.
const REAL_SCORE_FLOOR = 0.03; // avg score above this counts as "real signal", not noise
const CLEAR_WINNER_GAP = 0.2; // pass-rate lead over the runner-up that reads as decisive
const PCT = (v: number) => `${Math.round(v * 100)}%`;

// Cost label matching the scatter tooltip: 0 → "free", else "$0.0123".
const costLabel = (v: number) => (v === 0 ? "free" : `$${v.toFixed(4)}`);

const byPassRate = (a: LeaderboardEntry, b: LeaderboardEntry) => b.pass_rate - a.pass_rate;
const byAvgScore = (a: LeaderboardEntry, b: LeaderboardEntry) => b.avg_score - a.avg_score;

export function deriveDecideInsight(entries: ReadonlyArray<LeaderboardEntry>): DecideInsight | null {
  if (entries.length === 0) return null;

  const total = entries.length;
  const maxPass = Math.max(...entries.map((e) => e.pass_rate));
  const minPass = Math.min(...entries.map((e) => e.pass_rate));
  const avgScores = entries.map((e) => e.avg_score);
  const maxAvg = Math.max(...avgScores);
  const minAvg = Math.min(...avgScores);
  const recommended = entries.find((e) => e.recommended) ?? null;

  // 1. Everything errored — no output to score at all. Surface the operational
  //    problem before anyone reads a (meaningless) score.
  const allErrored = entries.every((e) => e.total > 0 && e.error_count === e.total);
  if (allErrored) {
    return {
      headline: "No candidate produced output",
      detail:
        "Every call errored, so there are no scores to compare. Check your API keys or local host before reading this run.",
      tone: "warn",
    };
  }

  // 2. All-fail but real scores — the scorer is stricter than the task. Pass rate
  //    is flat at 0, but avg score still ranks the field. THE case we hit.
  if (!recommended && maxPass === 0 && maxAvg >= REAL_SCORE_FLOOR) {
    const leader = [...entries].sort(byAvgScore)[0];
    const range = minAvg === maxAvg ? PCT(maxAvg) : `${PCT(minAvg)}–${PCT(maxAvg)}`;
    return {
      headline: "0% pass, but the scores still rank the field",
      detail:
        `No candidate cleared the bar, yet avg scores cluster at ${range} — the scorer looks stricter ` +
        `than the task. Flip the Y axis to Avg score: ${leader.label} leads. For paraphrased or free-form ` +
        `answers, try the LLM judge or lower the threshold in Settings.`,
      tone: "warn",
    };
  }

  // 3. Clear winner, well separated — the recommendation is decisive on pass rate.
  if (recommended) {
    const runnerUp = entries.filter((e) => e !== recommended).sort(byPassRate)[0];
    const gap = runnerUp ? recommended.pass_rate - runnerUp.pass_rate : recommended.pass_rate;
    if (gap >= CLEAR_WINNER_GAP) {
      return {
        headline: `${recommended.label} is the clear pick`,
        detail:
          `It passes ${PCT(recommended.pass_rate)} at ${costLabel(recommended.total_estimated_cost_usd)} — ` +
          `well ahead of the field. The frontier confirms it's earning the spot, not just the cheapest dot.`,
        tone: "ok",
      };
    }
    // 4. Winner but tight cluster — decide on cost / latency, not pass rate.
    return {
      headline: `${recommended.label} edges it, but the field is close`,
      detail:
        `Pass rates run ${PCT(minPass)}–${PCT(maxPass)} — too tight to separate on quality alone. ` +
        `Decide on cost or latency: the frontier shows which candidates buy their pass rate cheaply.`,
      tone: "info",
    };
  }

  // 5. Fallback — no recommendation and no clean story (e.g. a single candidate,
  //    or a partial-pass field with no winner gated). Name the leader + metric.
  const leader = [...entries].sort(byPassRate)[0];
  const metric = maxPass > 0 ? `${PCT(leader.pass_rate)} pass` : `${PCT(leader.avg_score)} avg score`;
  return {
    headline: total === 1 ? `${leader.label}, on its own` : `${leader.label} leads on this run`,
    detail:
      total === 1
        ? `Only one candidate ran — ${metric}. Add a second to compare and let the frontier do its work.`
        : `No candidate was recommended. ${leader.label} is highest at ${metric}; weigh it against cost on the frontier.`,
    tone: "info",
  };
}
