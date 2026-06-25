import { Equal, GitCompareArrows, ListChecks, Search, ShieldCheck, type LucideIcon } from "lucide-react";

import type { Dataset } from "../../lib/api";
import { RUBRIC_KIND_LABEL, type DatasetKind } from "./scoring";
import { computeCoverage } from "./datasetCoverageMath";
import { TagChips } from "./TagChips";

// The coverage strip — a calm instrument readout of the whole dataset library, above the cards.
// Not a dashboard: a row of quiet stat tiles, one thin eval-type distribution bar, and a domain
// line. Categorical separation only (value-token fills + per-kind icons), never the accent or a
// status hue — coverage is identity, not a control or a verdict.

// Each eval kind gets a categorical value token (the same t1..t7 palette the domain chips use) and
// its own icon, so the bar reads by icon+legend, never hue alone.
const KIND_VIS: Record<DatasetKind, { token: string; Icon: LucideIcon }> = {
  bench: { token: "var(--t5fg)", Icon: ShieldCheck },
  keypoint: { token: "var(--t2fg)", Icon: ListChecks },
  similarity: { token: "var(--t1fg)", Icon: GitCompareArrows },
  exact: { token: "var(--t7fg)", Icon: Equal },
  contains: { token: "var(--t3fg)", Icon: Search },
};

function StatTile({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-lg border border-(--color-panel-line) bg-(--color-panel)/40 px-3 py-2">
      <div className="font-mono text-lg leading-none text-(--color-ink)">{value}</div>
      <div className="mt-1 text-[11px] text-(--color-ink-muted)">{label}</div>
    </div>
  );
}

export function DatasetCoverage({ datasets }: { datasets: Dataset[] }) {
  const c = computeCoverage(datasets);
  if (c.datasetCount === 0) return null;

  return (
    <section
      aria-label="Dataset library coverage"
      className="grid gap-3 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-4"
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatTile value={c.datasetCount} label={c.datasetCount === 1 ? "dataset" : "datasets"} />
        <StatTile value={c.totalExamples} label="examples" />
        <StatTile value={c.evalTypeCount} label={c.evalTypeCount === 1 ? "eval type" : "eval types"} />
        <StatTile value={c.benchCount} label="governance bench" />
      </div>

      {/* One thin distribution bar, segmented by eval-type dataset count. */}
      <div>
        <div
          className="flex h-2 overflow-hidden rounded-full"
          role="img"
          aria-label={`Eval-type spread: ${c.distribution.map((s) => `${s.count} ${RUBRIC_KIND_LABEL[s.kind]}`).join(", ")}`}
        >
          {c.distribution.map((s) => (
            <div
              key={s.kind}
              title={`${RUBRIC_KIND_LABEL[s.kind]}: ${s.count}`}
              style={{
                flexGrow: s.count,
                backgroundColor: KIND_VIS[s.kind].token,
              }}
            />
          ))}
        </div>
        {/* Legend: icon + label + count, so the bar reads without relying on color. */}
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {c.distribution.map((s) => {
            const { Icon, token } = KIND_VIS[s.kind];
            return (
              <span key={s.kind} className="inline-flex items-center gap-1.5 text-[11px] text-(--color-ink-muted)">
                <Icon aria-hidden className="h-3 w-3 shrink-0" style={{ color: token }} />
                {RUBRIC_KIND_LABEL[s.kind]}
                <span className="font-mono text-(--color-ink-faint)">{s.count}</span>
              </span>
            );
          })}
        </div>
      </div>

      {c.domains.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-(--color-ink-faint)">Domains</span>
          <TagChips tags={c.domains} />
        </div>
      )}
    </section>
  );
}
