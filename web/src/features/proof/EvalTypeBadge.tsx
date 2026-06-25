import { Equal, GitCompareArrows, ListChecks, Search, ShieldCheck, type LucideIcon } from "lucide-react";

import type { Dataset } from "../../lib/api";
import { RUBRIC_KIND_LABEL, resolveDatasetKind, type DatasetKind } from "./scoring";

// The eval-type badge — a dataset's intrinsic scoring nature, made legible at a glance. Mirrors the
// ProviderTag pattern (badges.tsx): each kind reads apart via its own ICON as well as its label, so
// it never relies on hue alone. These are CATEGORICAL IDENTITY (what kind of evidence this is), not
// a status or an action, so they wear the neutral receipt-stub surface — never the green PASS token,
// never the cyan accent. The same component renders on the Datasets cards and the Proof Run summary,
// so the eval type reads identically wherever a dataset appears.
const NEUTRAL_SURFACE = "border-(--color-panel-line) bg-(--color-panel-card)";

// A short descriptor shown after bench's label — the three gates it grades — so "Governance bench"
// reads as a contract, not jargon. Other kinds are self-explanatory from the label.
const EVAL_STYLE: Record<DatasetKind, { Icon: LucideIcon; descriptor?: string }> = {
  bench: { Icon: ShieldCheck, descriptor: "citation · refusal · route" },
  keypoint: { Icon: ListChecks },
  exact: { Icon: Equal },
  contains: { Icon: Search },
  similarity: { Icon: GitCompareArrows },
};

export function EvalTypeBadge({ dataset }: { dataset: Dataset | undefined }) {
  const kind = resolveDatasetKind(dataset);
  const { Icon, descriptor } = EVAL_STYLE[kind];
  return (
    <span
      // `rounded` (not a pill): an identity tag takes the receipt-stub shape so it never reads as
      // pressable. Neutral surface + muted ink keep it quiet next to the value-token domain chips.
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium text-(--color-ink-muted) ${NEUTRAL_SURFACE}`}
      title={descriptor ? `${RUBRIC_KIND_LABEL[kind]} — ${descriptor}` : RUBRIC_KIND_LABEL[kind]}
    >
      <Icon aria-hidden className="h-3 w-3 shrink-0" />
      {RUBRIC_KIND_LABEL[kind]}
    </span>
  );
}
