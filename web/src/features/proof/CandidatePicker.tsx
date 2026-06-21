import { useState } from "react";

import type { SelectionGroup, SelectionModel, SelectionPanel } from "../../lib/api";
import { KeyEntry } from "./KeyEntry";
import { ProviderLogo } from "./ProviderLogo";
import { CLOUD_KEY_NAMES } from "./selectionMeta";

export interface CandidatePickerProps {
  panel: SelectionPanel;
  selected: string[];
  onToggle: (candidateId: string) => void;
}

// Provider-grouped chips: each curated model is a toggle; toggle several on one provider to
// compare them (the cost/latency-vs-quality proof). Unavailable providers are greyed; a
// "+ custom" field is the escape hatch for any model string the catalog doesn't list.
export function CandidatePicker({ panel, selected, onToggle }: CandidatePickerProps) {
  return (
    <fieldset className="grid gap-3 text-sm">
      <legend className="text-(--color-ink-muted)">Candidates</legend>
      <p className="text-xs text-(--color-ink-faint)">
        The models you're comparing. Toggle several models of one provider to weigh cost and
        latency against quality. Mock candidates run instantly, no API key.
      </p>
      <div className="grid gap-3">
        {panel.providers.map((g) => (
          <ProviderRow key={g.provider_id} group={g} selected={selected} onToggle={onToggle} />
        ))}
      </div>
    </fieldset>
  );
}

function ProviderRow({
  group,
  selected,
  onToggle,
}: {
  group: SelectionGroup;
  selected: string[];
  onToggle: (id: string) => void;
}) {
  // Custom-model chips the user added that aren't in the catalog list, so they still render.
  const customSelected = selected.filter(
    (id) => id.startsWith(`${group.provider_id}:`) && !group.models.some((m) => m.candidate_id === id),
  );
  return (
    <div className="grid gap-2 sm:grid-cols-[8rem_minmax(0,1fr)] sm:items-start">
      <div className="flex items-center gap-1.5 pt-1.5 text-(--color-ink-muted)">
        {/* The provider's logo doubles as the availability signal (full ink when available,
            dimmed when not); mocks have no brand and fall back to a status dot. */}
        <ProviderLogo
          providerId={group.provider_id}
          available={group.available}
          label={group.label}
        />
        {/* Mocks carry their full label on the chip, so the left column stays generic to avoid
            repeating the same text twice in one row. */}
        <span>{group.candidate_id != null ? "Mock" : group.label}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {group.candidate_id !== null && group.candidate_id !== undefined ? (
          <Chip
            label={group.label}
            value={group.candidate_id}
            checked={selected.includes(group.candidate_id)}
            disabled={!group.available}
            onToggle={onToggle}
          />
        ) : null}
        {group.models.map((m) => (
          <ModelChip
            key={m.candidate_id}
            model={m}
            checked={selected.includes(m.candidate_id)}
            disabled={!group.available}
            onToggle={onToggle}
          />
        ))}
        {customSelected.map((id) => (
          <Chip
            key={id}
            label={id.slice(group.provider_id.length + 1)}
            value={id}
            checked
            disabled={!group.available}
            onToggle={onToggle}
          />
        ))}
        {group.supports_custom && group.available ? (
          <CustomChip providerId={group.provider_id} providerLabel={group.label} onToggle={onToggle} />
        ) : null}
        {!group.available && CLOUD_KEY_NAMES[group.provider_id] ? (
          <div className="flex items-center gap-2">
            <span className="self-center text-xs text-(--color-ink-faint)">
              Unavailable — add a key
            </span>
            <KeyEntry
              providerId={group.provider_id}
              providerLabel={group.label}
              keyName={CLOUD_KEY_NAMES[group.provider_id]}
            />
          </div>
        ) : !group.available ? (
          <span className="self-center text-xs text-(--color-ink-faint)">
            Unavailable — start the local server
          </span>
        ) : null}
      </div>
    </div>
  );
}

const chipBase =
  "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 transition-colors disabled:cursor-not-allowed disabled:opacity-40";

function Chip({
  label,
  value,
  checked,
  disabled,
  onToggle,
}: {
  label: string;
  value: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <label
      className={
        chipBase +
        " " +
        (checked
          ? "border-(--color-accent)/50 bg-(--color-accent)/10"
          : "border-(--color-panel-line) hover:border-(--color-panel-line-strong)")
      }
    >
      <input
        type="checkbox"
        aria-label={label}
        checked={checked}
        disabled={disabled}
        onChange={() => onToggle(value)}
        className="accent-(--color-accent-strong)"
      />
      <span className="text-(--color-ink)">{label}</span>
    </label>
  );
}

function ModelChip({
  model,
  checked,
  disabled,
  onToggle,
}: {
  model: SelectionModel;
  checked: boolean;
  disabled?: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <label
      className={
        chipBase +
        " " +
        (checked
          ? "border-(--color-accent)/50 bg-(--color-accent)/10"
          : "border-(--color-panel-line) hover:border-(--color-panel-line-strong)")
      }
    >
      <input
        type="checkbox"
        aria-label={model.display_name}
        checked={checked}
        disabled={disabled}
        onChange={() => onToggle(model.candidate_id)}
        className="accent-(--color-accent-strong)"
      />
      <span className="text-(--color-ink)">{model.display_name}</span>
      {model.latest ? <span title="latest" className="text-(--color-accent)">★</span> : null}
      <span className="text-xs text-(--color-ink-faint)">{model.cost_class}</span>
    </label>
  );
}

function CustomChip({
  providerId,
  providerLabel,
  onToggle,
}: {
  providerId: string;
  providerLabel: string;
  onToggle: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  if (!open) {
    return (
      <button
        type="button"
        aria-label={`custom model for ${providerLabel}`}
        onClick={() => setOpen(true)}
        className="rounded-lg border border-dashed border-(--color-panel-line) px-3 py-2 text-(--color-ink-muted) hover:border-(--color-panel-line-strong)"
      >
        + custom
      </button>
    );
  }
  function submit() {
    const value = text.trim();
    if (value) onToggle(`${providerId}:${value}`);
    setText("");
    setOpen(false);
  }
  return (
    <div className="flex items-center gap-1">
      <input
        autoFocus
        aria-label={`custom ${providerLabel} model`}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            submit();
          } else if (e.key === "Escape") {
            setText("");
            setOpen(false);
          }
        }}
        placeholder="model id"
        className="w-40 rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-2 py-1.5 text-(--color-ink)"
      />
      <button
        type="button"
        onClick={submit}
        className="rounded-lg bg-(--color-accent-strong) px-2 py-1.5 text-(--color-accent-ink)"
      >
        Add
      </button>
    </div>
  );
}
