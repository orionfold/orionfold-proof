import { useState } from "react";
import { BadgeCheck } from "lucide-react";

import type { LeaderboardEntry } from "../../lib/api";
import { ProviderTag } from "./badges";
import { formatCostPerQuality, medalFor, passRateTone, type PassRateTone } from "./leaderboardFormat";
import {
  ariaSortFor,
  DEFAULT_SORT,
  nextSort,
  sortEntries,
  type SortColumn,
  type SortState,
} from "./leaderboardSort";

// Bar fill per traffic-light tone — STATUS tokens only (never the cyan accent).
const TONE_BAR: Record<PassRateTone, string> = {
  ok: "bg-(--color-ok)",
  warn: "bg-(--color-warn)",
  danger: "bg-(--color-danger)",
};

// Mono micro-caps header voice from the reference `.tbl` kit (WS-F F3): the "receipt voice" for
// data tables — small uppercase monospace with wide tracking, quiet ink. Shared by every header so
// the row reads as one ledger.
const HEADER_CLS =
  "p-3 font-mono text-[10px] font-medium uppercase tracking-[0.06em] whitespace-nowrap text-(--color-ink-muted)";

// Arrow glyph per sort state, matching the reference `.sort-ar` (↕ inactive, ↑/↓ active).
function sortArrow(active: boolean, direction: "asc" | "desc"): string {
  if (!active) return "↕";
  return direction === "asc" ? "↑" : "↓";
}

// A sortable column header — a real <button> for keyboard/AT, `aria-sort` on the <th>, and the
// accent reserved for the *active* sort column (cyan = the one interactive color; this header IS a
// control, so the accent is correct here — not a status use).
function SortableHeader({
  column,
  label,
  sort,
  onSort,
}: {
  column: SortColumn;
  label: string;
  sort: SortState;
  onSort: (column: SortColumn) => void;
}) {
  const active = sort.column === column;
  return (
    <th className={HEADER_CLS} aria-sort={ariaSortFor(column, sort)}>
      <button
        type="button"
        onClick={() => onSort(column)}
        className={
          "inline-flex items-center gap-1 uppercase tracking-[0.06em] hover:text-(--color-accent) " +
          (active ? "text-(--color-accent)" : "")
        }
      >
        {label}
        <span aria-hidden className={active ? "opacity-100" : "opacity-40"}>
          {sortArrow(active, sort.direction)}
        </span>
      </button>
    </th>
  );
}

// The leaderboard is the verdict: who to trust, ranked. The recommended row is highlighted
// so the decision reads at a glance — a calm instrument panel, not a wall of metrics. Columns are
// sortable for exploration (WS-F F2); the server's ranking is the default on load, and the podium
// medals show only in that default order (a transient explore-sort is no longer the verdict).
export function Leaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const onSort = (column: SortColumn) => setSort((prev) => nextSort(prev, column));

  const hasWinner = entries.some((e) => e.recommended);
  const ranked = sort.column === null;
  const rows = sortEntries(entries, sort);

  return (
    <section aria-label="Leaderboard" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-(--color-ink-muted)">
        Leaderboard
      </h2>
      <div className="overflow-x-auto rounded-xl border border-(--color-panel-line)">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="text-left">
              <th className={HEADER_CLS}>#</th>
              <SortableHeader column="label" label="Candidate" sort={sort} onSort={onSort} />
              <th className={HEADER_CLS}>Provider</th>
              <SortableHeader column="pass_rate" label="Pass rate" sort={sort} onSort={onSort} />
              <SortableHeader column="cost_per_quality" label="$ / quality" sort={sort} onSort={onSort} />
              <SortableHeader column="avg_score" label="Avg score" sort={sort} onSort={onSort} />
              <SortableHeader column="avg_latency_ms" label="Avg latency" sort={sort} onSort={onSort} />
              {/* Throughput is informational, never a ranking key (spec §4a) → a plain, non-sortable header. */}
              <th className={HEADER_CLS}>tok/s</th>
              <SortableHeader column="total_estimated_cost_usd" label="Est. cost" sort={sort} onSort={onSort} />
              <SortableHeader column="failure_count" label="Failures" sort={sort} onSort={onSort} />
            </tr>
          </thead>
          <tbody>
            {rows.map((e, i) => (
              <tr
                key={e.candidate_id}
                className={
                  "border-t border-(--color-panel-line) " +
                  (e.recommended ? "bg-(--color-accent)/[0.08]" : "")
                }
              >
                <td className="p-3 tabular-nums text-(--color-ink-muted)">
                  {(ranked ? medalFor(i, hasWinner) : null) ?? i + 1}
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
                <td className="p-3 tabular-nums">
                  {e.tokens_per_second != null ? e.tokens_per_second.toFixed(1) : "—"}
                </td>
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
