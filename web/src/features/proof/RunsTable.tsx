import { useState } from "react";
import { ArrowRight, Download } from "lucide-react";

import { receiptUrl, type ProofReport } from "../../lib/api";
import { ProviderTag } from "./badges";
import { passRateTone, type PassRateTone } from "./leaderboardFormat";
import {
  ariaSortFor,
  DEFAULT_RUN_SORT,
  nextRunSort,
  sortRunRows,
  toRunRow,
  type RunRow,
  type RunSortColumn,
  type RunSortState,
} from "./runsTableRows";

// The Receipts Runs mode (Slice 4): a compact, sortable, scannable table — one row per proof,
// replacing the old tall ReceiptCard list (~10–12 rows fit above the fold vs ~3 cards). Each row
// distils a run to its verdict; `→` opens the receipt detail (Slice 5's L3), and a checkbox marks
// runs for compare. Newest-first by default (the server order); headers sort for exploration.

const TONE_TEXT: Record<PassRateTone, string> = {
  ok: "text-(--color-ok)",
  warn: "text-(--color-warn)",
  danger: "text-(--color-danger)",
};

const FORMATS: { fmt: "md" | "html" | "json"; label: string }[] = [
  { fmt: "md", label: "MD" },
  { fmt: "html", label: "HTML" },
  { fmt: "json", label: "JSON" },
];

export function RunsTable({
  reports,
  onOpenRun,
}: {
  reports: ProofReport[];
  onOpenRun: (runId: string) => void;
}) {
  const [sort, setSort] = useState<RunSortState>(DEFAULT_RUN_SORT);
  // Run ids checked for compare. A future "Compare selected" affordance reads this; for now the
  // checkboxes let the operator mark a working set (the count is surfaced in a small action bar).
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const rows = sortRunRows(reports.map(toRunRow), sort);
  const onSort = (column: RunSortColumn) => setSort((prev) => nextRunSort(prev, column));
  const toggle = (runId: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(runId)) next.delete(runId);
      else next.add(runId);
      return next;
    });

  return (
    <div className="flex flex-col gap-2">
      {selected.size > 0 && (
        <div className="flex items-center gap-3 text-sm text-(--color-ink-muted)">
          <span className="tabular-nums">{selected.size} selected</span>
          <button
            type="button"
            onClick={() => setSelected(new Set())}
            className="text-(--color-ink-faint) underline-offset-2 hover:text-(--color-ink) hover:underline"
          >
            Clear
          </button>
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border border-(--color-panel-line) bg-(--color-panel-card)">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-(--color-panel-line) text-left text-[0.62rem] text-(--color-ink-faint)">
              <th className="w-8 px-3 py-2" aria-label="Select" />
              <SortableHeader column="heading" label="Proof" sort={sort} onSort={onSort} />
              <th className="px-3 py-2 font-medium uppercase tracking-[0.06em]">Verdict</th>
              <SortableHeader column="passRate" label="Pass" sort={sort} onSort={onSort} align="right" />
              <th className="px-3 py-2 font-medium uppercase tracking-[0.06em]">Scored by</th>
              <SortableHeader column="costUsd" label="Cost" sort={sort} onSort={onSort} align="right" />
              <SortableHeader column="createdAt" label="When" sort={sort} onSort={onSort} />
              <th className="px-3 py-2 font-medium uppercase tracking-[0.06em]">Export</th>
              <th className="w-10 px-3 py-2" aria-label="Open" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <Row
                key={row.runId}
                row={row}
                checked={selected.has(row.runId)}
                onToggle={() => toggle(row.runId)}
                onOpen={() => onOpenRun(row.runId)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Row({
  row,
  checked,
  onToggle,
  onOpen,
}: {
  row: RunRow;
  checked: boolean;
  onToggle: () => void;
  onOpen: () => void;
}) {
  return (
    <tr className="border-b border-(--color-panel-line) last:border-0 transition-colors hover:bg-(--color-rail)/40">
      <td className="px-3 py-2.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          aria-label={`Select ${row.heading} for compare`}
          className="h-3.5 w-3.5 accent-(--color-accent)"
        />
      </td>
      <td className="max-w-[22rem] px-3 py-2.5">
        <span className="flex items-center gap-2">
          <span className="truncate text-(--color-ink)" title={row.heading}>
            {row.heading}
          </span>
          {row.isSample && (
            <span className="shrink-0 rounded border border-(--color-panel-line) px-1.5 py-0.5 text-[10px] font-medium text-(--color-ink-faint)">
              Sample
            </span>
          )}
        </span>
      </td>
      <td className="px-3 py-2.5">
        <span className="flex flex-wrap items-center gap-1.5">
          <span className="text-(--color-ink-faint)">{row.verb}</span>
          {row.winnerLabel && <span className="text-(--color-ink)">{row.winnerLabel}</span>}
          {row.winnerProviderId && row.winnerPrivacy && (
            <ProviderTag candidate={{ provider_id: row.winnerProviderId, privacy: row.winnerPrivacy }} />
          )}
        </span>
      </td>
      <td className="px-3 py-2.5 text-right font-mono tabular-nums">
        {row.passRate != null ? (
          <span className={TONE_TEXT[passRateTone(row.passRate)]}>{Math.round(row.passRate * 100)}%</span>
        ) : (
          <span className="text-(--color-ink-faint)">—</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-(--color-ink-muted)">{row.scoredBy}</td>
      <td className="px-3 py-2.5 text-right font-mono tabular-nums text-(--color-ink-muted)">
        {row.costUsd === 0 ? "$0.00" : row.costUsd < 10 ? `$${row.costUsd.toFixed(2)}` : `$${Math.round(row.costUsd)}`}
      </td>
      <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs text-(--color-ink-faint)">
        {row.createdAt}
      </td>
      <td className="px-3 py-2.5">
        <span className="flex items-center gap-1">
          <Download aria-hidden className="h-3 w-3 shrink-0 text-(--color-ink-faint)" />
          {FORMATS.map(({ fmt, label }) => (
            <a
              key={fmt}
              href={receiptUrl(row.runId, fmt)}
              download
              className="rounded border border-(--color-panel-line) px-1.5 py-0.5 text-[11px] text-(--color-ink-muted) transition-colors hover:border-(--color-accent)/50 hover:text-(--color-ink)"
            >
              {label}
            </a>
          ))}
        </span>
      </td>
      <td className="px-3 py-2.5">
        <button
          type="button"
          onClick={onOpen}
          aria-label={`Open ${row.heading}`}
          title="Open receipt"
          className="flex h-7 w-7 items-center justify-center rounded-md text-(--color-ink-faint) transition-colors hover:bg-(--color-rail) hover:text-(--color-accent)"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
      </td>
    </tr>
  );
}

// A sortable column header — a real <button> for keyboard/AT, `aria-sort` on the <th>, accent on
// the active column (the header IS a control, so cyan is correct here). Mirrors Leaderboard's.
function SortableHeader({
  column,
  label,
  sort,
  onSort,
  align,
}: {
  column: RunSortColumn;
  label: string;
  sort: RunSortState;
  onSort: (column: RunSortColumn) => void;
  align?: "right";
}) {
  const active = sort.column === column;
  return (
    <th
      className={"px-3 py-2 font-medium uppercase tracking-[0.06em] " + (align === "right" ? "text-right" : "")}
      aria-sort={ariaSortFor(column, sort)}
    >
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
          {active ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}
        </span>
      </button>
    </th>
  );
}
