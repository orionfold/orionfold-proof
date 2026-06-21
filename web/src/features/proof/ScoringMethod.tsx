// ScoringMethod — lets the operator choose how a run is scored.
// Auto (null) delegates to the backend default; Keypoint/Similarity are heuristic;
// LLM judge delegates scoring to a model. When judge is active, the operator picks
// a judge from the selection panel. A keyless "Mock judge" option always appears first.
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";

import { getSelection, rubricSchema } from "../../lib/api";
import type { SelectionGroup, SelectionPanel } from "../../lib/api";
import { KeyEntry } from "./KeyEntry";
import { CLOUD_KEY_NAMES } from "./selectionMeta";

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
}

const METHODS: { id: Method; label: string }[] = [
  { id: "auto", label: "Auto" },
  { id: "keypoint", label: "Keypoint" },
  { id: "similarity", label: "Similarity" },
  { id: "judge", label: "LLM judge" },
];

// The active method button style mirrors the accent selection pattern from CandidatePicker chips.
const btnBase =
  "rounded-lg border px-3 py-2 text-sm transition-colors";
const btnActive =
  "border-(--color-accent)/50 bg-(--color-accent)/10 text-(--color-ink)";
const btnIdle =
  "border-(--color-panel-line) text-(--color-ink-muted) hover:border-(--color-panel-line-strong)";

export function ScoringMethod({ value, onChange }: ScoringMethodProps) {
  // Track the active tab in local state so clicking "LLM judge" immediately shows the picker
  // even before the parent has re-rendered with the new rubric value (controlled-component tests
  // pass a static value so we must not rely solely on `value` for the visible tab).
  const [method, setMethod] = useState<Method>(() => deriveMethod(value));

  function selectMethod(m: Method) {
    setMethod(m);
    if (m === "auto") {
      onChange(null);
    } else if (m === "keypoint") {
      onChange({ kind: "keypoint", threshold: 0.8, case_sensitive: false });
    } else if (m === "similarity") {
      onChange({ kind: "similarity", threshold: 0.8, case_sensitive: false });
    } else {
      // judge — emit a default judge rubric; the user refines the model below
      onChange({ kind: "judge", threshold: 0.8, case_sensitive: false, judge_provider_id: "mock_judge", judge_model: null });
    }
  }

  return (
    <fieldset className="grid gap-3 text-sm">
      <legend className="text-(--color-ink-muted)">Scoring method</legend>
      <p className="text-xs text-(--color-ink-faint)">
        Default uses the backend heuristic. Keypoint checks that expected key facts appear.
        Similarity scores by semantic closeness. LLM judge routes each comparison to a model.
      </p>
      {/* Method selector row */}
      <div className="flex flex-wrap gap-2">
        {METHODS.map((m) => (
          <button
            key={m.id}
            type="button"
            aria-pressed={method === m.id}
            onClick={() => selectMethod(m.id)}
            className={`${btnBase} ${method === m.id ? btnActive : btnIdle}`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Judge model picker — only shown when LLM judge is active */}
      {method === "judge" ? (
        <JudgePicker
          selectedProviderId={value?.kind === "judge" ? (value.judge_provider_id ?? null) : null}
          selectedModel={value?.kind === "judge" ? (value.judge_model ?? null) : null}
          onPick={(providerId, model) =>
            onChange({
              kind: "judge",
              threshold: 0.8,
              case_sensitive: false,
              judge_provider_id: providerId,
              judge_model: model,
            })
          }
        />
      ) : null}
    </fieldset>
  );
}

// ---------------------------------------------------------------------------
// JudgePicker — renders "Mock judge" plus all selection groups as judge options.
// ---------------------------------------------------------------------------

interface JudgePickerProps {
  selectedProviderId: string | null;
  selectedModel: string | null;
  onPick: (providerId: string, model: string | null) => void;
}

function JudgePicker({ selectedProviderId, selectedModel, onPick }: JudgePickerProps) {
  const { data: panel } = useQuery<SelectionPanel>({ queryKey: ["selection"], queryFn: getSelection });

  const groups: SelectionGroup[] = panel?.providers ?? [];

  return (
    <div className="grid gap-3">
      <p className="text-xs text-(--color-ink-faint)">
        Choose a judge model. The first option runs locally without an API key.
      </p>

      {/* Keyless "Mock judge" is always available and listed first */}
      <JudgeProviderRow
        providerId="mock_judge"
        label="Mock judge"
        available
        models={[]}
        isCloudWithKey={false}
        selectedProviderId={selectedProviderId}
        selectedModel={selectedModel}
        onPick={onPick}
      />

      {/* Real provider groups from the selection panel */}
      {groups.map((g) => (
        <JudgeProviderRow
          key={g.provider_id}
          providerId={g.provider_id}
          label={g.label}
          available={g.available}
          models={g.models}
          isCloudWithKey={!g.available && Boolean(CLOUD_KEY_NAMES[g.provider_id])}
          keyName={CLOUD_KEY_NAMES[g.provider_id]}
          selectedProviderId={selectedProviderId}
          selectedModel={selectedModel}
          onPick={onPick}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// JudgeProviderRow — mirrors CandidatePicker's ProviderRow pattern.
// For available providers: clickable model chips.
// For unavailable cloud providers: greyed out with inline KeyEntry.
// ---------------------------------------------------------------------------

interface JudgeProviderRowProps {
  providerId: string;
  label: string;
  available: boolean;
  models: SelectionGroup["models"];
  isCloudWithKey: boolean;
  keyName?: string;
  selectedProviderId: string | null;
  selectedModel: string | null;
  onPick: (providerId: string, model: string | null) => void;
}

function JudgeProviderRow({
  providerId,
  label,
  available,
  models,
  isCloudWithKey,
  keyName,
  selectedProviderId,
  selectedModel,
  onPick,
}: JudgeProviderRowProps) {
  // "Mock judge" is identified by provider id, not by empty models list.
  const isMock = providerId === "mock_judge";
  const isMockSelected = selectedProviderId === providerId && selectedModel === null;

  return (
    <div className="grid gap-2 sm:grid-cols-[8rem_minmax(0,1fr)] sm:items-start">
      {/* Provider label column — hidden for mock_judge since the chip is self-labelled */}
      {providerId !== "mock_judge" ? (
        <div className="flex items-center gap-1.5 pt-1.5 text-(--color-ink-muted)">
          <span>{label}</span>
        </div>
      ) : (
        <div />
      )}

      {/* Chips / key-entry column */}
      <div className="flex flex-wrap gap-2">
        {isMock ? (
          /* Mock judge — single selection chip for the provider itself */
          <button
            type="button"
            aria-pressed={isMockSelected}
            onClick={() => onPick(providerId, null)}
            className={`${btnBase} ${isMockSelected ? btnActive : btnIdle}`}
          >
            {label}
          </button>
        ) : available ? (
          /* Available real provider — one chip per model */
          models.map((m) => {
            const isSelected =
              selectedProviderId === providerId && selectedModel === m.model;
            return (
              <button
                key={m.candidate_id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => onPick(providerId, m.model)}
                className={`${btnBase} ${isSelected ? btnActive : btnIdle}`}
              >
                {m.display_name}
                {m.latest ? (
                  <span title="latest" className="ml-1 text-(--color-accent)">
                    ★
                  </span>
                ) : null}
                <span className="ml-1 text-xs text-(--color-ink-faint)">{m.cost_class}</span>
              </button>
            );
          })
        ) : isCloudWithKey && keyName ? (
          /* Unavailable cloud provider — KeyEntry prompt, mirrors CandidatePicker lines 100–109 */
          <div className="flex items-center gap-2">
            <span className="self-center text-xs text-(--color-ink-faint)">
              Unavailable — add a key
            </span>
            <KeyEntry
              providerId={providerId}
              providerLabel={label}
              keyName={keyName}
            />
          </div>
        ) : (
          /* Unavailable non-cloud (e.g. Ollama not running) */
          <span className="self-center text-xs text-(--color-ink-faint)">
            Unavailable — start the local server
          </span>
        )}
      </div>
    </div>
  );
}
