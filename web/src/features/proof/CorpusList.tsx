import { useQuery } from "@tanstack/react-query";
import { BookText, ChevronRight } from "lucide-react";

import { getCorpora } from "../../lib/api";

// A compact, always-discoverable list of governed corpora at the top of the Datasets screen.
// Today a corpus is reachable only via a bench dataset's "corpus" badge — so an unbound or
// imported corpus would be invisible. This makes every corpus browsable directly, without adding
// a rail item for what is currently a single corpus. Each card opens the existing CorpusView.
// Renders nothing when there are no corpora, so the screen stays calm on a fresh install.
export function CorpusList({ onOpenCorpus }: { onOpenCorpus?: (id: string) => void }) {
  const corpora = useQuery({ queryKey: ["corpora"], queryFn: getCorpora });

  // Stay quiet on load/error or when there are none — this is a secondary surface, not a gate.
  if (!corpora.data || corpora.data.length === 0) return null;

  return (
    <section className="grid gap-2">
      <h2 className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-(--color-ink-faint)">
        <BookText aria-hidden className="h-3.5 w-3.5 shrink-0" />
        Corpora ({corpora.data.length})
      </h2>
      <ul className="grid gap-2 sm:grid-cols-2">
        {corpora.data.map((c) => {
          const count = c.source_ids.length;
          const meta = `${count} source${count === 1 ? "" : "s"}`;
          const card = (
            <div className="flex items-start gap-2">
              <div className="min-w-0 grow">
                <div className="truncate text-sm font-medium text-(--color-ink)">{c.name}</div>
                {c.description && (
                  <p className="mt-0.5 line-clamp-2 text-xs text-(--color-ink-muted)">
                    {c.description}
                  </p>
                )}
                <div className="mt-1 text-[11px] text-(--color-ink-faint)">{meta}</div>
              </div>
              {onOpenCorpus && (
                <ChevronRight
                  aria-hidden
                  className="mt-0.5 h-4 w-4 shrink-0 text-(--color-ink-faint)"
                />
              )}
            </div>
          );
          return (
            <li key={c.id}>
              {onOpenCorpus ? (
                <button
                  type="button"
                  onClick={() => onOpenCorpus(c.id)}
                  aria-label={`Browse the ${c.name} corpus`}
                  className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-3 text-left transition-colors hover:border-(--color-accent)/50 hover:bg-(--color-ink)/5"
                >
                  {card}
                </button>
              ) : (
                <div className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-3">
                  {card}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
