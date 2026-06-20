import { receiptUrl, type ProofReport } from "../../lib/api";

// The receipt is the product's takeaway artifact. Three formats: Markdown to paste, HTML to
// share with a client, JSON to archive or diff. Each download carries the config hash.
const FORMATS: { fmt: "md" | "html" | "json"; label: string }[] = [
  { fmt: "md", label: "Markdown" },
  { fmt: "html", label: "HTML" },
  { fmt: "json", label: "JSON" },
];

export function ReceiptExport({ report }: { report: ProofReport }) {
  return (
    <section aria-label="Proof Receipt export" className="w-full">
      <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-[--color-ink-muted]">
        Proof Receipt
      </h2>
      <p className="mb-3 text-sm text-[--color-ink-muted]">
        Config hash <code className="text-[--color-ink]">{report.run.config_hash}</code> ·{" "}
        {report.run.created_at}
      </p>
      <div className="flex flex-wrap gap-2">
        {FORMATS.map(({ fmt, label }) => (
          <a
            key={fmt}
            href={receiptUrl(report.run.id, fmt)}
            download
            className="rounded-lg border border-[--color-panel-line] bg-[--color-panel-card] px-4 py-2 text-sm text-[--color-ink] transition-colors hover:border-emerald-400"
          >
            Export {label}
          </a>
        ))}
      </div>
    </section>
  );
}
