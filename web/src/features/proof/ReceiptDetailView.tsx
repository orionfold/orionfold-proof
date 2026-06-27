import { useState } from "react";
import { ArrowLeft, Download, ExternalLink } from "lucide-react";

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

// The deepest IA level (L3): one run's full record. It leads with the receipt artifact rendered
// exactly as it exports (the deliverable a user hands a client), then carries the interactive
// record the old right Inspector used to show — config + hardware provenance, the leaderboard /
// frontier / cost ledger, and a browsable failure-case detail. With this complete, the Prove
// canvas no longer needs a side panel (Slice 5).
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
  // A quick-compare run has no scored leaderboard, so the standings/frontier/failure blocks don't
  // apply — the artifact + config still tell the story.
  const isScored = run.mode !== "quick" && report.leaderboard.length > 0;

  return (
    <main aria-label="Proof Receipt" className="flex flex-col gap-6 px-6 py-8 lg:px-10">
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
          The receipt you'd share — rendered exactly as it exports. Config hash{" "}
          <code className="text-(--color-ink)">{run.config_hash}</code>.
        </p>
      </header>

      <iframe
        title="Proof Receipt preview"
        src={receiptPreviewUrl(run.id, resolved)}
        sandbox=""
        className="min-h-[60vh] w-full rounded-xl border border-(--color-panel-line) bg-(--color-panel-card)"
      />

      <section className="flex flex-wrap items-center gap-2">
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
      </section>

      {/* The interactive record below the artifact — the full detail the old right Inspector and
          the Prove-canvas results tree carried, now rehomed to the run's own page. */}
      <div className="grid gap-8 border-t border-(--color-panel-line) pt-8">
        <RunConfig report={report} />
        {isScored && (
          <>
            <Leaderboard entries={report.leaderboard} />
            <FrontierScatter entries={report.leaderboard} />
            <CostLedger report={report} />
            <FailureCases
              report={report}
              selected={selectedFailure}
              onSelect={setSelectedFailure}
            />
            <SelectedFailure selected={selectedFailure} />
          </>
        )}
      </div>
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
