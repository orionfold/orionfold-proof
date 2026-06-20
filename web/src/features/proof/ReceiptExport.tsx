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
    <section aria-label="Proof Receipt export" className="grid gap-3">
      <h3 className="text-sm font-medium text-(--color-ink)">Proof Receipt</h3>
      <p className="text-xs text-(--color-ink-muted)">
        Private, repeatable, secret-free. Each export carries the config hash and timestamp.
      </p>
      <div className="flex flex-wrap gap-2">
        {FORMATS.map(({ fmt, label }) => (
          <a
            key={fmt}
            href={receiptUrl(report.run.id, fmt)}
            download
            className="rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) px-3 py-1.5 text-sm text-(--color-ink) transition-colors hover:border-(--color-accent)/50"
          >
            Export {label}
          </a>
        ))}
      </div>
    </section>
  );
}
