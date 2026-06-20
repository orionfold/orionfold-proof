import { ArrowLeft, Download, ExternalLink } from "lucide-react";

import { receiptPreviewUrl, receiptUrl, type ProofReport } from "../../lib/api";

const FORMATS: { fmt: "md" | "html" | "json"; label: string }[] = [
  { fmt: "md", label: "Markdown" },
  { fmt: "html", label: "HTML" },
  { fmt: "json", label: "JSON" },
];

// The receipt artifact, rendered exactly as it exports. The cockpit shows the interactive run;
// this shows the deliverable a user would hand a client. The iframe is fully sandboxed (no
// scripts, opaque origin) — the HTML is already escaped server-side, so this is defense-in-depth.
export function ReceiptDetailView({
  report,
  onBack,
  onExplore,
}: {
  report: ProofReport;
  onBack: () => void;
  onExplore: (report: ProofReport) => void;
}) {
  const { run } = report;
  const heading = run.brief.decision_question || run.brief.task_name;

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
        src={receiptPreviewUrl(run.id)}
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
    </main>
  );
}
