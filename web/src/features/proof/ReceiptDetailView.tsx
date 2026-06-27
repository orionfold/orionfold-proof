import { useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  DollarSign,
  Download,
  ExternalLink,
  FileCheck,
  Settings2,
  Trophy,
} from "lucide-react";

import { receiptPreviewUrl, receiptUrl, type ProofReport, type ResultRow } from "../../lib/api";
import { useTheme } from "../../lib/theme";
import { StatusBadge } from "./badges";
import { CostLedger } from "./CostLedger";
import { FailureCases } from "./FailureCases";
import { FrontierScatter } from "./FrontierScatter";
import { Leaderboard } from "./Leaderboard";
import { RunConfig } from "./RunConfig";

const FORMATS: { fmt: "md" | "html" | "json"; label: string }[] = [
  { fmt: "md", label: "Markdown" },
  { fmt: "html", label: "HTML" },
  { fmt: "json", label: "JSON" },
];

type DetailTab = "receipt" | "config" | "leaderboard" | "cost" | "failures";

const TABS: { id: DetailTab; label: string; icon: typeof FileCheck; scoredOnly?: boolean }[] = [
  { id: "receipt", label: "Receipt", icon: FileCheck },
  { id: "config", label: "Run config", icon: Settings2 },
  { id: "leaderboard", label: "Leaderboard", icon: Trophy, scoredOnly: true },
  { id: "cost", label: "Cost", icon: DollarSign, scoredOnly: true },
  { id: "failures", label: "Failure cases", icon: AlertTriangle, scoredOnly: true },
];

// The deepest IA level (L3): one run's full record, as a TABBED detail view (R1b). The receipt
// artifact leads on its own tab — rendered exactly as it exports (the deliverable a user hands a
// client), maximized to fill the fold. The interactive record the old right Inspector carried —
// config + hardware provenance, the leaderboard / frontier, the cost ledger, and the failure-case
// browser — splits across the remaining tabs so no single panel needs the long vertical scroll the
// one-page version had. Analysis tabs (Leaderboard/Cost/Failures) apply only to a scored run.
export function ReceiptDetailView({
  report,
  onBack,
  onExplore,
}: {
  report: ProofReport;
  onBack: () => void;
  onExplore: (report: ProofReport) => void;
}) {
  const { resolved } = useTheme();
  const { run } = report;
  const heading = run.brief.decision_question || run.brief.task_name;
  // The detail view owns its own failure selection — it's a standalone screen, so there's no App
  // lift to coordinate the way the side panel needed (the side panel sat beside the cockpit's list).
  const [selectedFailure, setSelectedFailure] = useState<ResultRow | null>(null);
  const [tab, setTab] = useState<DetailTab>("receipt");
  // A quick-compare run has no scored leaderboard, so the standings/frontier/cost/failure tabs
  // don't apply — the artifact + config still tell the story.
  const isScored = run.mode !== "quick" && report.leaderboard.length > 0;
  const tabs = TABS.filter((t) => isScored || !t.scoredOnly);
  // Guard against a stale active tab if the report ever flips scored→quick (e.g. a different run
  // loads). The receipt tab always exists, so it's the safe fallback.
  const active = tabs.some((t) => t.id === tab) ? tab : "receipt";

  return (
    <main
      aria-label="Proof Receipt"
      className="mx-auto flex w-full max-w-[96rem] flex-col gap-6 px-6 py-8 lg:px-10"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-sm text-(--color-ink-muted) transition-colors hover:text-(--color-ink)"
        >
          <ArrowLeft aria-hidden className="h-4 w-4 shrink-0" />
          Receipts
        </button>
        <button
          type="button"
          onClick={() => onExplore(report)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink) transition-colors hover:border-(--color-accent)/50"
        >
          Explore in cockpit
          <ExternalLink aria-hidden className="h-3.5 w-3.5 shrink-0" />
        </button>
      </div>

      <header className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold tracking-tight text-(--color-ink)">{heading}</h2>
        <p className="max-w-prose text-sm text-(--color-ink-muted)">
          One run's full record. Config hash{" "}
          <code className="text-(--color-ink)">{run.config_hash}</code>.
        </p>
      </header>

      {/* Tab strip + downloads share one row — tabs left (a control, so the active tab takes the
          cyan accent), the receipt export links right (they download the whole receipt regardless
          of the active tab, so they stay reachable from every section). */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          role="tablist"
          aria-label="Receipt detail sections"
          className="inline-flex w-fit flex-wrap items-center gap-1 rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-1"
        >
          {tabs.map((t) => {
            const isActive = t.id === active;
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setTab(t.id)}
                className={
                  "inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors " +
                  (isActive
                    ? "bg-(--color-accent) text-(--color-accent-ink)"
                    : "text-(--color-ink-muted) hover:bg-(--color-rail) hover:text-(--color-ink)")
                }
              >
                <Icon aria-hidden className="h-4 w-4 shrink-0" />
                {t.label}
              </button>
            );
          })}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="flex items-center gap-1 text-xs text-(--color-ink-faint)">
            <Download aria-hidden className="h-3 w-3 shrink-0" />
            Download
          </span>
          {FORMATS.map(({ fmt, label }) => (
            <a
              key={fmt}
              href={receiptUrl(run.id, fmt)}
              download
              className="rounded-md border border-(--color-panel-line) px-2.5 py-1 text-sm text-(--color-ink) transition-colors hover:border-(--color-accent)/50"
            >
              {label}
            </a>
          ))}
        </div>
      </div>

      {active === "receipt" && (
        <section className="flex flex-col gap-3">
          {/* Maximized so the receipt fills the fold — the doc is a sandboxed standalone HTML
              artifact (no scripts, opaque origin: a deliberate security boundary), so it can't
              report its own height; we size it to the viewport instead of a short fixed box.
              Splitting the heavy analysis out to other tabs keeps this the only tall panel. */}
          <iframe
            title="Proof Receipt preview"
            src={receiptPreviewUrl(run.id, resolved)}
            sandbox=""
            className="h-[calc(100vh-15rem)] min-h-[40rem] w-full rounded-xl border border-(--color-panel-line) bg-(--color-panel-card)"
          />
        </section>
      )}

      {active === "config" && <RunConfig report={report} />}

      {active === "leaderboard" && isScored && (
        <section className="grid gap-8">
          <Leaderboard entries={report.leaderboard} />
          <FrontierScatter entries={report.leaderboard} />
        </section>
      )}

      {active === "cost" && isScored && <CostLedger report={report} />}

      {active === "failures" && isScored && (
        // min-w-0 so the failure rows clip to the container instead of expanding the column to fit
        // their long input text (grid/flex children default to min-width:auto, which defeats the
        // rows' own `truncate`).
        <section className="grid min-w-0 gap-6">
          <FailureCases report={report} selected={selectedFailure} onSelect={setSelectedFailure} />
          <SelectedFailure selected={selectedFailure} />
        </section>
      )}
    </main>
  );
}

// The expanded detail for the chosen failure row — input, expected, output, error. Rehomed from
// the old right Inspector's SelectedFailure pane: the FailureCases list lifts a selection but only
// renders a truncated row, so the full text needs a home here in the standalone detail view.
function SelectedFailure({ selected }: { selected: ResultRow | null }) {
  if (!selected) return null;
  return (
    <section className="grid gap-3">
      <h3 className="text-sm font-medium text-(--color-ink)">Failure detail</h3>
      <dl className="grid gap-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-(--color-ink-faint)">Example {selected.example_index + 1}</span>
          {selected.error ? (
            <StatusBadge kind="error">error</StatusBadge>
          ) : (
            <StatusBadge kind="fail">score {(selected.score ?? 0).toFixed(2)}</StatusBadge>
          )}
        </div>
        <Detail label="Input" value={selected.input_text} />
        <Detail label="Expected" value={selected.expected_text} />
        <Detail label="Output" value={selected.output_text || "—"} />
        {selected.error && <Detail label="Error" value={selected.error} tone="error" />}
      </dl>
    </section>
  );
}

function Detail({ label, value, tone }: { label: string; value: string; tone?: "error" }) {
  return (
    <div className="grid gap-0.5">
      <span className="text-xs text-(--color-ink-faint)">{label}</span>
      <span className={tone === "error" ? "text-(--color-danger)" : "text-(--color-ink)"}>
        {value}
      </span>
    </div>
  );
}
