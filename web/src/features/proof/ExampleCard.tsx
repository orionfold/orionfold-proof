import {
  Check,
  MessageSquare,
  Quote,
  ShieldX,
  Signpost,
  type LucideIcon,
} from "lucide-react";

import type { Example } from "../../lib/api";
import type { DatasetKind } from "./scoring";
import { behaviorMeta, citationIds, requirementChips } from "./exampleShape";
import {
  parseRetrievedContext,
  type RetrievedSource,
} from "./retrievedContext";

// The adaptive example renderer — the golden feature. The Datasets screen exists so the operator can
// trust the evidence a receipt is built on; that trust starts with SEEING what each example asks for.
// One component, branching on the dataset's eval kind (computed once per card, passed in), so every
// example reads in the shape of its own contract instead of a flat Input/Expected wall of text:
//   bench      → a governance contract (behavior pill · required gates · expected citations)
//   keypoint   → the expected facts as a checklist
//   exact      → input, then "= must equal <value>" (the match rule made obvious)
//   contains   → input, then "⊃ must contain <value>"
//   similarity → input, then a labeled reference answer
// Anything without the signal degrades to the plain input/expected pair (arbitrary imported sets).
export function ExampleCard({ kind, example }: { kind: DatasetKind; example: Example }) {
  switch (kind) {
    case "bench":
      return <BenchExample ex={example} />;
    case "keypoint":
      return <KeypointExample ex={example} />;
    case "exact":
    case "contains":
      return <MatchExample ex={example} kind={kind} />;
    case "similarity":
      return <SimilarityExample ex={example} />;
  }
}

// --- shared sub-parts -------------------------------------------------------------------------

// A labeled block of source text (input / context / reference answer). pre-wrap preserves authoring.
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-0.5">
      <span className="text-xs text-(--color-ink-faint)">{label}</span>
      <span className="whitespace-pre-wrap text-(--color-ink)">{value || "—"}</span>
    </div>
  );
}

// A mono chip for a source id / expected value — the receipt-stub `of-tag`, already mono + squared.
function IdChip({ children }: { children: React.ReactNode }) {
  return <span className="of-tag">{children}</span>;
}

const BEHAVIOR_ICON: Record<string, LucideIcon> = {
  MessageSquare,
  Signpost,
  ShieldX,
};

// --- per-kind renderers ------------------------------------------------------------------------

// A governance contract: what behavior is expected, which gates must hold, what must be cited.
function BenchExample({ ex }: { ex: Example }) {
  const meta = behaviorMeta(ex.expected_behavior);
  const Icon = BEHAVIOR_ICON[meta.icon] ?? MessageSquare;
  const reqs = requirementChips(ex);
  const { expected, accepted } = citationIds(ex);
  // refuse is a caution-class expectation (the model is supposed to decline) — the one place a status
  // hue is meaningful here; answer/route stay on the neutral receipt-stub surface.
  const pillCls =
    meta.tone === "warn"
      ? "border-(--color-warn)/40 bg-(--color-warn)/10 text-(--color-warn)"
      : "border-(--color-panel-line) bg-(--color-panel-card) text-(--color-ink-muted)";

  // Smart-parse the flattened "retrieved public context" into question + source records when present;
  // otherwise fall back to the plain input field (an arbitrary imported bench set has free-form text).
  const parsed = parseRetrievedContext(ex.input_text);
  // The ids this row must / may cite — used both for the chip row below AND to cross-link the parsed
  // source cards ("this is the source you must cite").
  const citedIds = new Set([...expected, ...accepted]);

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[11px] font-medium ${pillCls}`}
        >
          <Icon aria-hidden className="h-3 w-3 shrink-0" />
          {meta.label}
        </span>
        {reqs.length > 0 && (
          <span className="text-xs text-(--color-ink-faint)">
            needs: <span className="text-(--color-ink-muted)">{reqs.join(" · ")}</span>
          </span>
        )}
      </div>
      {parsed ? (
        <>
          <Field label="Question" value={parsed.question} />
          <RetrievedSources sources={parsed.sources} citedIds={citedIds} />
        </>
      ) : (
        <Field label="Question / context" value={ex.input_text} />
      )}
      {expected.length + accepted.length > 0 && (
        <div className="grid gap-0.5">
          <span className="text-xs text-(--color-ink-faint)">
            {expected.length > 0 ? "Must cite" : "Defensible citations"}
          </span>
          <div className="flex flex-wrap gap-1.5">
            {expected.map((id) => (
              <IdChip key={`e-${id}`}>{id}</IdChip>
            ))}
            {accepted.map((id) => (
              <IdChip key={`a-${id}`}>{id}</IdChip>
            ))}
          </div>
        </div>
      )}
      {ex.expected_behavior !== "refuse" && ex.expected_text && (
        <Field label="Reference answer" value={ex.expected_text} />
      )}
    </div>
  );
}

// The retrieved context as progressive disclosure: one collapsed card per source (title + class/label
// chips + mono id), expanding to the excerpt. A source the row must cite is cross-linked — accent
// border + a "must cite" marker — so "here's the source" lines up with the "Must cite" chips above.
function RetrievedSources({
  sources,
  citedIds,
}: {
  sources: RetrievedSource[];
  citedIds: Set<string>;
}) {
  return (
    <div className="grid gap-1">
      <span className="text-xs text-(--color-ink-faint)">
        Retrieved context · {sources.length} source{sources.length === 1 ? "" : "s"}
      </span>
      <ol className="grid gap-1.5">
        {sources.map((s, i) => (
          <li key={`${s.id}-${i}`}>
            <SourceCard source={s} cited={citedIds.has(s.id)} />
          </li>
        ))}
      </ol>
    </div>
  );
}

function SourceCard({ source, cited }: { source: RetrievedSource; cited: boolean }) {
  const hasBody = Boolean(source.excerpt);
  // A cited source earns the one accent border here — it answers "which of these must I cite?".
  const frameCls = cited
    ? "border-(--color-accent)/50 bg-(--color-accent)/5"
    : "border-(--color-panel-line) bg-(--color-panel-card)";
  return (
    <details className={`group rounded border ${frameCls}`}>
      <summary
        className={`flex cursor-pointer flex-wrap items-center gap-1.5 px-2 py-1.5 ${
          hasBody ? "hover:bg-(--color-ink)/5" : "cursor-default"
        }`}
      >
        {cited && (
          <span
            className="inline-flex items-center gap-1 text-[11px] font-medium text-(--color-accent)"
            title="This is a source the answer must cite."
          >
            <Quote aria-hidden className="h-3 w-3 shrink-0" />
            Must cite
          </span>
        )}
        {source.title && (
          <span className="text-(--color-ink)">{source.title}</span>
        )}
        <IdChip>{source.id}</IdChip>
        {source.class && (
          <span className="font-mono text-[11px] text-(--color-ink-faint)">{source.class}</span>
        )}
      </summary>
      {hasBody && (
        <div className="border-t border-(--color-panel-line) px-2 py-1.5">
          {source.label && (
            <p className="mb-1 text-xs text-(--color-ink-muted)">{source.label}</p>
          )}
          <p className="whitespace-pre-wrap text-xs text-(--color-ink-muted)">{source.excerpt}</p>
        </div>
      )}
    </details>
  );
}

// The expected answer broken into the required facts a model must cover, as a checklist.
function KeypointExample({ ex }: { ex: Example }) {
  const keypoints = ex.keypoints ?? [];
  return (
    <div className="grid gap-2">
      <Field label="Input" value={ex.input_text} />
      {keypoints.length > 0 ? (
        <div className="grid gap-0.5">
          <span className="text-xs text-(--color-ink-faint)">Expected covers</span>
          <ul className="grid gap-1">
            {keypoints.map((kp, i) => (
              <li key={i} className="flex items-start gap-1.5 text-(--color-ink)">
                <Check aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0 text-(--color-ink-muted)" />
                <span>{kp}</span>
              </li>
            ))}
          </ul>
          {ex.expected_text && (
            <p className="mt-1 whitespace-pre-wrap text-xs text-(--color-ink-faint)">
              Reference: {ex.expected_text}
            </p>
          )}
        </div>
      ) : (
        <Field label="Expected" value={ex.expected_text} />
      )}
    </div>
  );
}

// A classification / extraction pair where the match rule itself is the story.
function MatchExample({ ex, kind }: { ex: Example; kind: "exact" | "contains" }) {
  const rule = kind === "exact" ? "= must equal" : "⊃ must contain";
  return (
    <div className="grid gap-2">
      <Field label="Input" value={ex.input_text} />
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-(--color-ink-faint)">{rule}</span>
        <IdChip>{ex.expected_text || "—"}</IdChip>
      </div>
    </div>
  );
}

// Free-form generation graded by closeness — "Expected" would overstate it, so it's a reference.
function SimilarityExample({ ex }: { ex: Example }) {
  return (
    <div className="grid gap-2">
      <Field label="Input" value={ex.input_text} />
      <div className="grid gap-0.5">
        <span className="text-xs text-(--color-ink-faint)">≈ reference answer</span>
        <span className="whitespace-pre-wrap text-(--color-ink)">{ex.expected_text || "—"}</span>
      </div>
    </div>
  );
}
