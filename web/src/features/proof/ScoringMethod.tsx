// ScoringMethod — grouped method cards (free checks vs paid LLM judge) plus a two-step judge filter.
// Auto (null) delegates to the backend default; the Auto card shows what that resolves to for the
// selected dataset. Keypoint/Similarity are heuristic; LLM judge delegates scoring to a model.
import { useState } from "react";
import { z } from "zod";

import { rubricSchema } from "../../lib/api";
import type { Dataset } from "../../lib/api";
import { MethodCard } from "./MethodCard";
import { JudgeFilter } from "./JudgeFilter";
import { resolveAutoKind } from "./scoring";
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

  function selectMethod(m: Method) {
    setMethod(m);
    if (m === "auto") onChange(null);
    else if (m === "keypoint") onChange({ kind: "keypoint", threshold: 0.8, case_sensitive: false });
    else if (m === "similarity") onChange({ kind: "similarity", threshold: 0.8, case_sensitive: false });
    else onChange({ kind: "judge", threshold: 0.8, case_sensitive: false, judge_provider_id: "mock_judge", judge_model: null });
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
        <MethodCard title={METHOD_META.judge.label} guidance={METHOD_META.judge.guidance} cost={METHOD_META.judge.cost} selected={method === "judge"} onSelect={() => selectMethod("judge")} />
      </div>

      {method === "judge" ? (
        <JudgeFilter
          selectedProviderId={value?.kind === "judge" ? (value.judge_provider_id ?? null) : null}
          selectedModel={value?.kind === "judge" ? (value.judge_model ?? null) : null}
          onPick={(providerId, model) =>
            onChange({ kind: "judge", threshold: 0.8, case_sensitive: false, judge_provider_id: providerId, judge_model: model })
          }
        />
      ) : null}
    </fieldset>
  );
}
