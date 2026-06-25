import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Library, Quote } from "lucide-react";

import {
  getCorpora,
  getCorpusSources,
  type CorpusSource,
} from "../../lib/api";
import { ViewNotice, ViewShell } from "./ViewShell";

// A first-class browse surface for a governed corpus — the source set a bench dataset grades its
// citations against. The corpus manifest stores only ids; the title/class/excerpt shown here is
// DERIVED server-side from the bound bench examples (where those sources are flattened into the
// prompt). Each source is a progressive-disclosure card; the ones the bench requires cited carry a
// "cited by N" marker, tying the trust manifest to the questions that depend on it.
export function CorpusView({
  corpusId,
  onBack,
}: {
  corpusId: string;
  onBack: () => void;
}) {
  const corpora = useQuery({ queryKey: ["corpora"], queryFn: getCorpora });
  const sources = useQuery({
    queryKey: ["corpus-sources", corpusId],
    queryFn: () => getCorpusSources(corpusId),
  });

  const corpus = corpora.data?.find((c) => c.id === corpusId);
  const back = (
    <button
      type="button"
      onClick={onBack}
      className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-(--color-ink-muted) hover:bg-(--color-panel-card) hover:text-(--color-ink)"
    >
      <ArrowLeft aria-hidden className="h-4 w-4 shrink-0" />
      Back to datasets
    </button>
  );

  const title = corpus?.name ?? corpusId;
  const subtitle =
    corpus?.description ||
    "The governed source set a bench dataset grades its citations against.";

  return (
    <ViewShell title={title} subtitle={subtitle} action={back}>
      {sources.isPending ? (
        <ViewNotice>Loading corpus sources…</ViewNotice>
      ) : sources.isError ? (
        <ViewNotice tone="error">Couldn't load this corpus.</ViewNotice>
      ) : sources.data.length === 0 ? (
        <ViewNotice>This corpus has no sources yet.</ViewNotice>
      ) : (
        <section className="grid gap-3">
          <div className="flex items-center gap-2 text-sm text-(--color-ink-muted)">
            <Library aria-hidden className="h-4 w-4 shrink-0 text-(--color-ink-faint)" />
            <span>
              {sources.data.length} source{sources.data.length === 1 ? "" : "s"} ·{" "}
              {sources.data.filter((s) => s.cited_by > 0).length} cited by the bench
            </span>
          </div>
          <ol className="grid gap-2">
            {sources.data.map((s, i) => (
              <li key={`${s.id}-${i}`}>
                <CorpusSourceCard source={s} />
              </li>
            ))}
          </ol>
        </section>
      )}
    </ViewShell>
  );
}

function CorpusSourceCard({ source }: { source: CorpusSource }) {
  const hasBody = Boolean(source.excerpt || source.label);
  const cited = source.cited_by > 0;
  const frameCls = cited
    ? "border-(--color-accent)/50 bg-(--color-accent)/5"
    : "border-(--color-panel-line) bg-(--color-panel-card)";
  return (
    <details className={`group rounded-lg border ${frameCls}`}>
      <summary
        className={`flex cursor-pointer flex-wrap items-center gap-2 px-3 py-2 ${
          hasBody ? "hover:bg-(--color-ink)/5" : "cursor-default"
        }`}
      >
        {source.title && <span className="text-sm text-(--color-ink)">{source.title}</span>}
        <span className="of-tag">{source.id}</span>
        {source.class && (
          <span className="font-mono text-[11px] text-(--color-ink-faint)">{source.class}</span>
        )}
        {cited && (
          <span
            className="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-(--color-accent)"
            title="Bench examples require citing this source."
          >
            <Quote aria-hidden className="h-3 w-3 shrink-0" />
            cited by {source.cited_by}
          </span>
        )}
      </summary>
      {hasBody && (
        <div className="border-t border-(--color-panel-line) px-3 py-2">
          {source.label && (
            <p className="mb-1 text-xs text-(--color-ink-muted)">{source.label}</p>
          )}
          {source.excerpt && (
            <p className="whitespace-pre-wrap text-xs text-(--color-ink-muted)">{source.excerpt}</p>
          )}
        </div>
      )}
    </details>
  );
}
