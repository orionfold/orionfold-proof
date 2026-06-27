// ScoringMethod — grouped method cards (free checks vs paid LLM judge) plus a two-step judge filter.
// Auto (null) delegates to the backend default; the Auto card shows what that resolves to for the
// selected dataset. Keypoint/Similarity are heuristic; LLM judge delegates scoring to a model.
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { getSelection, getSettings, rubricSchema } from "../../lib/api";
import type { Dataset, SelectionPanel } from "../../lib/api";
import { MethodCard } from "./MethodCard";
import { JudgeFilter } from "./JudgeFilter";
import {
  defaultJudgeCell,
  isBenchDataset,
  prefersSampleJudge,
  resolveAutoKind,
  thresholdFor,
} from "./scoring";
import { METHOD_META } from "./selectionMeta";
import { checkHintLabel } from "./tags";

export type Rubric = z.infer<typeof rubricSchema>;

type Method = "auto" | "exact" | "keypoint" | "similarity" | "judge" | "bench";

function deriveMethod(value: Rubric | null): Method {
  if (value === null) return "auto";
  if (value.kind === "exact") return "exact";
  if (value.kind === "keypoint") return "keypoint";
  if (value.kind === "similarity") return "similarity";
  if (value.kind === "judge") return "judge";
  if (value.kind === "bench") return "bench";
  return "auto";
}

export interface ScoringMethodProps {
  value: Rubric | null;
  onChange: (next: Rubric | null) => void;
  dataset?: Dataset;
}

export function ScoringMethod({ value, onChange, dataset }: ScoringMethodProps) {
  const [method, setMethod] = useState<Method>(() => deriveMethod(value));
  // Shared `["settings"]` cache (populated by SettingsView): the persisted per-kind threshold
  // overrides prefill the cards. Undefined on first paint → thresholdFor falls back to the map.
  const settings = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const thresholds = settings.data?.thresholds;
  const sandbox = settings.data?.sandbox_enabled ?? false;

  // The selection panel + sandbox decide where the LLM judge opens. With Sandbox OFF and a real
  // judge configured we default to a real one (Hosted cloud, else Local Ollama) — never silently
  // Mock. When no real judge exists and Sandbox is off, `judgeCell` is null and the LLM-judge card
  // is disabled with a hint (add a key / start Ollama) rather than mocking a "real" evaluation.
  const { data: panel } = useQuery<SelectionPanel>({ queryKey: ["selection"], queryFn: getSelection });
  // The judge default can only be resolved once we have a definite answer. That needs `settings`
  // (is Sandbox on?) always, plus the `panel` (which real judges exist) UNLESS Sandbox is on — the
  // Sandbox case resolves to the keyless Mock judge without consulting the panel. Until ready we must
  // NOT emit a guessed judge: a stale `mock_judge` would diverge from the dropdown once the panel
  // loads (it shows the first real option) and the run would silently grade with Mock.
  const judgeReady = settings.data !== undefined && (sandbox || panel !== undefined);
  const judgeCell = judgeReady ? defaultJudgeCell(panel, sandbox) : undefined;
  // Disable once ready with no real judge. The enabled/commit predicates share `judgeReady` so the
  // card is never enabled-but-dead: if it's clickable, a click commits (or it's disabled).
  const judgeDisabled = judgeReady && judgeCell === null;

  function selectMethod(m: Method) {
    if (m === "auto") { setMethod(m); onChange(null); }
    else if (m === "exact") { setMethod(m); onChange({ kind: "exact", threshold: 1, case_sensitive: false }); }
    else if (m === "keypoint") { setMethod(m); onChange({ kind: "keypoint", threshold: thresholdFor("keypoint", thresholds), case_sensitive: false }); }
    else if (m === "similarity") { setMethod(m); onChange({ kind: "similarity", threshold: thresholdFor("similarity", thresholds), case_sensitive: false }); }
    else if (m === "bench") { setMethod(m); onChange({ kind: "bench", threshold: 0, case_sensitive: false }); }
    else if (judgeCell) {
      // Only commit the judge method once we have a real judge to emit — never a guessed Mock.
      setMethod(m);
      onChange({ kind: "judge", threshold: thresholdFor("judge", thresholds), case_sensitive: false, judge_provider_id: judgeCell.providerId, judge_model: judgeCell.model });
    }
  }

  // Keep the local `method` honest with the controlled `value`. `value` is owned by the parent, which
  // can change it without going through `selectMethod` — e.g. resetting the rubric to null on a
  // dataset switch (a fresh setup). Without this sync the highlighted card + the bench helper line
  // would stay on the prior method (the "Scored by the Governance bench" line lingering after the
  // dataset is no longer a bench). Deriving from `value` is idempotent for `selectMethod`'s own calls.
  useEffect(() => {
    setMethod(deriveMethod(value));
  }, [value]);

  // The bundled summarization demo grades free-form paraphrase, which lexical Similarity/Keypoint
  // reads as "no winner" at any threshold. So when the sample dataset loads and a real judge has
  // resolved, default the Configure step to the LLM judge instead of Auto — once per dataset arrival,
  // and only while the user hasn't already chosen a method (`value === null`, i.e. still Auto). The
  // latch (keyed on dataset id) keeps the effect from clobbering a later deliberate switch back to
  // Auto. When no real judge exists (`judgeCell` null/undefined) `prefersSampleJudge` is false, so the
  // demo stays on the keyless Auto path — never a silent Mock.
  const autoDefaultedFor = useRef<string | null>(null);
  useEffect(() => {
    if (autoDefaultedFor.current === dataset?.id) return;
    if (value === null && prefersSampleJudge(dataset, judgeCell)) {
      autoDefaultedFor.current = dataset?.id ?? null;
      selectMethod("judge");
    }
    // selectMethod is stable for this purpose (re-derived each render but only invoked under the
    // guards above); deps cover every input that flips the decision.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset?.id, dataset?.is_sample, value, judgeCell]);

  // A bench dataset has a deterministic governance contract, not a free-form rubric — default the
  // Configure step to the Governance bench once it arrives (once per dataset, while still Auto), so
  // the operator doesn't have to know to pick it. Mirrors the sample-judge latch above.
  const bench = isBenchDataset(dataset);
  const benchDefaultedFor = useRef<string | null>(null);
  useEffect(() => {
    if (benchDefaultedFor.current === dataset?.id) return;
    if (value === null && bench) {
      benchDefaultedFor.current = dataset?.id ?? null;
      selectMethod("bench");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset?.id, bench, value]);

  const autoKind = resolveAutoKind(dataset);
  const AUTO_LABEL: Record<typeof autoKind, string> = {
    keypoint: "Keypoint coverage",
    similarity: "Similarity",
    exact: "Exact match",
    contains: "Contains",
  };
  const autoGuidance = `Picks the best free check — here, ${AUTO_LABEL[autoKind]}.`;
  // When the dataset's check hint drove the resolution, name it so the link is visible.
  const hintLabel = checkHintLabel(dataset?.check_hint);
  const hintDroveAuto = hintLabel && (autoKind === "exact" || autoKind === "contains");

  return (
    <fieldset className="grid gap-3 text-sm">
      <legend className="text-(--color-ink-muted)">Scoring method</legend>

      <p className="text-xs text-(--color-ink-faint)">
        The first three are free, instant, and repeatable. The LLM judge costs money and adds latency.
      </p>
      <div className="grid items-stretch gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <MethodCard title="Auto" guidance={autoGuidance} cost="Free" selected={method === "auto"} onSelect={() => selectMethod("auto")} />
        <MethodCard title={METHOD_META.exact.label} guidance={METHOD_META.exact.guidance} cost={METHOD_META.exact.cost} selected={method === "exact"} onSelect={() => selectMethod("exact")} />
        <MethodCard title={METHOD_META.keypoint.label} guidance={METHOD_META.keypoint.guidance} cost={METHOD_META.keypoint.cost} selected={method === "keypoint"} onSelect={() => selectMethod("keypoint")} />
        <MethodCard title={METHOD_META.similarity.label} guidance={METHOD_META.similarity.guidance} cost={METHOD_META.similarity.cost} selected={method === "similarity"} onSelect={() => selectMethod("similarity")} />
        <MethodCard
          title={METHOD_META.judge.label}
          guidance={judgeDisabled ? "Needs a real judge — add a provider key or start Ollama." : METHOD_META.judge.guidance}
          cost={METHOD_META.judge.cost}
          selected={method === "judge"}
          disabled={judgeDisabled}
          onSelect={() => selectMethod("judge")}
        />
      </div>

      {bench ? (
        <MethodCard
          title="Governance bench"
          guidance="Deterministic citation · refusal · route · no-leak grading for a corpus advisor. No threshold."
          cost="Free"
          selected={method === "bench"}
          onSelect={() => selectMethod("bench")}
        />
      ) : null}

      {method === "bench" ? (
        <p className="text-xs text-(--color-ink-faint)">
          Scored by the{" "}
          <span className="font-medium text-(--color-ink-muted)">Governance bench</span> — each row
          is graded against its declared contract (cite the right sources, refuse when unsupported,
          route correctly, never leak private state). Pass/fail is deterministic; there is no
          threshold to tune.
        </p>
      ) : null}

      {method === "auto" && hintDroveAuto ? (
        <p className="text-xs text-(--color-ink-faint)">
          From your dataset hint:{" "}
          <span className="font-medium text-(--color-ink-muted)">{hintLabel}</span> →{" "}
          <span className="font-medium text-(--color-ink-muted)">{AUTO_LABEL[autoKind]}</span>.
        </p>
      ) : null}

      {method === "similarity" ? (
        <p className="text-xs text-(--color-ink-faint)">
          Passing at{" "}
          <span className="font-medium text-(--color-ink-muted)">
            {thresholdFor("similarity", thresholds).toFixed(2)}
          </span>
          . 0.80 is strict; ~0.55 is typical for a good paraphrased summary. Tune the default in
          Settings → Default scoring thresholds.
        </p>
      ) : null}

      {method === "judge" ? (
        <JudgeFilter
          initialCell={judgeCell}
          selectedProviderId={value?.kind === "judge" ? (value.judge_provider_id ?? null) : null}
          selectedModel={value?.kind === "judge" ? (value.judge_model ?? null) : null}
          onPick={(providerId, model) =>
            onChange({ kind: "judge", threshold: thresholdFor("judge", thresholds), case_sensitive: false, judge_provider_id: providerId, judge_model: model })
          }
        />
      ) : null}
    </fieldset>
  );
}
