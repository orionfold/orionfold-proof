import type { ReactNode } from "react";

// The collapsible shell shared by every "source card" surface — the bench example's retrieved-context
// sources (ExampleCard) and the governed-corpus browse view (CorpusView). It owns ONLY the genuinely
// shared structure: a <details> disclosure, the cited-accent frame, the cursor/hover affordance gated
// on whether there's a body, and the bordered body wrapper. Each caller keeps its own SEMANTICS — what
// data it shows, which "cited" marker it renders — by composing into the `summary` and `body` slots.
// This removes the duplicated frame/structure without forcing two different data models under one type.
export function SourceDisclosure({
  cited,
  density = "compact",
  summary,
  body,
}: {
  // Whether this source is tied to the bench's citation requirement — earns the one accent frame.
  cited: boolean;
  // compact = inside an example card (tighter); comfortable = the standalone corpus browse view.
  density?: "compact" | "comfortable";
  summary: ReactNode;
  // Omitted/empty body → the card is non-expandable (no excerpt/label to reveal).
  body?: ReactNode;
}) {
  const hasBody = body != null && body !== false;
  const frameCls = cited
    ? "border-(--color-accent)/50 bg-(--color-accent)/5"
    : "border-(--color-panel-line) bg-(--color-panel-card)";
  const radius = density === "comfortable" ? "rounded-lg" : "rounded";
  const summaryPad = density === "comfortable" ? "gap-2 px-3 py-2" : "gap-1.5 px-2 py-1.5";
  const bodyPad = density === "comfortable" ? "px-3 py-2" : "px-2 py-1.5";

  return (
    <details className={`group border ${radius} ${frameCls}`}>
      <summary
        className={`flex flex-wrap items-center ${summaryPad} ${
          hasBody ? "cursor-pointer hover:bg-(--color-ink)/5" : "cursor-default"
        }`}
      >
        {summary}
      </summary>
      {hasBody && (
        <div className={`border-t border-(--color-panel-line) ${bodyPad}`}>{body}</div>
      )}
    </details>
  );
}
