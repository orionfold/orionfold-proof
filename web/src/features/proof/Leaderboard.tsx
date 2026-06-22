import { BadgeCheck } from "lucide-react";

import type { LeaderboardEntry } from "../../lib/api";
import { ProviderTag } from "./badges";
import { formatCostPerQuality, medalFor, passRateTone, type PassRateTone } from "./leaderboardFormat";

// Bar fill per traffic-light tone — STATUS tokens only (never the cyan accent).
const TONE_BAR: Record<PassRateTone, string> = {
  ok: "bg-(--color-ok)",
  warn: "bg-(--color-warn)",
  danger: "bg-(--color-danger)",
};

// The leaderboard is the verdict: who to trust, ranked. The recommended row is highlighted
// so the decision reads at a glance — a calm instrument panel, not a wall of metrics.
export function Leaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  const hasWinner = entries.some((e) => e.recommended);
  return (
    <section aria-label="Leaderboard" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
        Leaderboard
      </h2>
      <div className="overflow-x-auto rounded-xl border border-(--color-panel-line)">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left text-(--color-ink-faint)">
              <th className="p-3 font-medium">#</th>
              <th className="p-3 font-medium">Candidate</th>
              <th className="p-3 font-medium">Provider</th>
              <th className="p-3 font-medium">Pass rate</th>
              <th className="p-3 font-medium">$ / quality</th>
              <th className="p-3 font-medium">Avg score</th>
              <th className="p-3 font-medium">Avg latency</th>
              <th className="p-3 font-medium">Est. cost</th>
              <th className="p-3 font-medium">Failures</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e, i) => (
              <tr
                key={e.candidate_id}
                className={
                  "border-t border-(--color-panel-line) " +
                  (e.recommended ? "bg-(--color-accent)/[0.08]" : "")
                }
              >
                <td className="p-3 tabular-nums text-(--color-ink-muted)">
                  {medalFor(i, hasWinner) ?? i + 1}
                </td>
                <td className="p-3">
                  {e.label}
                  {e.recommended && (
                    <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-(--color-accent)/20 px-2 py-0.5 text-xs text-(--color-accent)">
                      <BadgeCheck aria-hidden className="h-3 w-3 shrink-0" />
                      Recommended
                    </span>
                  )}
                </td>
                <td className="p-3">
                  <ProviderTag candidate={e} />
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-(--color-panel-line)">
                      <div
                        className={"h-full rounded-full " + TONE_BAR[passRateTone(e.pass_rate)]}
                        style={{ width: `${Math.round(e.pass_rate * 100)}%` }}
                      />
                    </div>
                    <span className="tabular-nums">
                      {Math.round(e.pass_rate * 100)}% ({e.pass_count}/{e.total})
                    </span>
                  </div>
                </td>
                <td className="p-3 tabular-nums">{formatCostPerQuality(e.cost_per_quality)}</td>
                <td className="p-3">{e.avg_score.toFixed(2)}</td>
                <td className="p-3">{e.avg_latency_ms}ms</td>
                <td className="p-3">${e.total_estimated_cost_usd.toFixed(2)}</td>
                <td className="p-3">
                  {e.failure_count}
                  {e.total > 0 && e.error_count === e.total && (
                    <span className="ml-1 text-(--color-ink-faint)">(errored, no output)</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
