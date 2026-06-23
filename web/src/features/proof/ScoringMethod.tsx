// ScoringMethod — grouped method cards (free checks vs paid LLM judge) plus a two-step judge filter.
// Auto (null) delegates to the backend default; the Auto card shows what that resolves to for the
// selected dataset. Keypoint/Similarity are heuristic; LLM judge delegates scoring to a model.
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { getSelection, getSettings, rubricSchema } from "../../lib/api";
import type { Dataset, SelectionPanel } from "../../lib/api";
import { MethodCard } from "./MethodCard";
import { JudgeFilter } from "./JudgeFilter";
import { defaultJudgeCell, resolveAutoKind, thresholdFor } from "./scoring";
import { METHOD_META } from "./selectionMeta";

export type Rubric = z.infer<typeof rubricSchema>;

type Method = "auto" | "keypoint" | "similarity" | "judge";

function deriveMethod(value: Rubric | null): Method {
  if (value === null) return "auto";
  if (value.kind === "keypoint") return "keypoint";
  if (value.kind === "similarity") return "similarity";
  if (value.kind === "judge") return "judge";
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
    else if (m === "keypoint") { setMethod(m); onChange({ kind: "keypoint", threshold: thresholdFor("keypoint", thresholds), case_sensitive: false }); }
    else if (m === "similarity") { setMethod(m); onChange({ kind: "similarity", threshold: thresholdFor("similarity", thresholds), case_sensitive: false }); }
    else if (judgeCell) {
      // Only commit the judge method once we have a real judge to emit — never a guessed Mock.
      setMethod(m);
      onChange({ kind: "judge", threshold: thresholdFor("judge", thresholds), case_sensitive: false, judge_provider_id: judgeCell.providerId, judge_model: judgeCell.model });
    }
  }

  const autoResolved = resolveAutoKind(dataset) === "keypoint" ? "Keypoint coverage" : "Similarity";
  const autoGuidance = `Picks the best free check — here, ${autoResolved}.`;

  return (
    <fieldset className="grid gap-3 text-sm">
      <legend className="text-(--color-ink-muted)">Scoring method</legend>

      <p className="text-xs text-(--color-ink-faint)">
        The first three are free, instant, and repeatable. The LLM judge costs money and adds latency.
      </p>
      <div className="grid items-stretch gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <MethodCard title="Auto" guidance={autoGuidance} cost="Free" selected={method === "auto"} onSelect={() => selectMethod("auto")} />
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
