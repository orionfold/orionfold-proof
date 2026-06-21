// Two-step judge picker: choose Local/Hosted, then Cheapest/Balanced/Best; a dropdown lists the
// matching models with an opinionated default. The keyless Mock judge is the Local+Cheapest default,
// so a run stays keyless unless the operator deliberately picks a hosted judge.
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getSelection } from "../../lib/api";
import type { SelectionPanel, Privacy } from "../../lib/api";
import { filterJudgeModels, type JudgeTier } from "./scoring";
import { JUDGE_TIERS } from "./selectionMeta";
import { KeyEntry } from "./KeyEntry";

export interface JudgeFilterProps {
  selectedProviderId: string | null;
  selectedModel: string | null;
  onPick: (providerId: string, model: string | null) => void;
}

const toggleBase = "rounded-lg border px-3 py-1.5 text-sm transition-colors";
const toggleActive = "border-(--color-accent)/50 bg-(--color-accent)/10 text-(--color-ink)";
const toggleIdle = "border-(--color-panel-line) text-(--color-ink-muted) hover:border-(--color-panel-line-strong)";

const encode = (providerId: string, model: string | null) => `${providerId}::${model ?? ""}`;

export function JudgeFilter({ selectedProviderId, selectedModel, onPick }: JudgeFilterProps) {
  const { data: panel } = useQuery<SelectionPanel>({ queryKey: ["selection"], queryFn: getSelection });
  const [privacy, setPrivacy] = useState<Privacy>("local");
  const [tier, setTier] = useState<JudgeTier>("economy");

  const result = filterJudgeModels(panel, privacy, tier);

  // When the axes change, jump the selection to the new cell's opinionated default — but only if the
  // cell has options. An empty cell keeps the prior (still-valid) judge selection.
  function changeAxis(next: { privacy?: Privacy; tier?: JudgeTier }) {
    const p = next.privacy ?? privacy;
    const t = next.tier ?? tier;
    if (next.privacy) setPrivacy(next.privacy);
    if (next.tier) setTier(next.tier);
    const r = filterJudgeModels(panel, p, t);
    if (r.defaultProviderId) onPick(r.defaultProviderId, r.defaultModel);
  }

  const currentValue = selectedProviderId ? encode(selectedProviderId, selectedModel) : "";

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-(--color-ink-muted)">Run on</span>
        {(["local", "cloud"] as Privacy[]).map((p) => (
          <button key={p} type="button" aria-pressed={privacy === p} onClick={() => changeAxis({ privacy: p })}
            className={`${toggleBase} ${privacy === p ? toggleActive : toggleIdle}`}>
            {p === "local" ? "Local" : "Hosted"}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-(--color-ink-muted)">Optimize</span>
        {JUDGE_TIERS.map((t) => (
          <button key={t.id} type="button" aria-pressed={tier === t.id} onClick={() => changeAxis({ tier: t.id })}
            className={`${toggleBase} ${tier === t.id ? toggleActive : toggleIdle}`}>
            {t.label}
          </button>
        ))}
      </div>

      {result.options.length > 0 ? (
        <label className="grid gap-1.5 text-sm">
          <span className="text-(--color-ink-muted)">Judge model</span>
          <select
            value={currentValue}
            onChange={(e) => {
              const [pid, model] = e.target.value.split("::");
              onPick(pid, model === "" ? null : model);
            }}
            className="rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-3 py-2 text-(--color-ink)"
          >
            {result.options.map((o) => (
              <option key={encode(o.providerId, o.model)} value={encode(o.providerId, o.model)}>
                {o.displayName}
              </option>
            ))}
          </select>
        </label>
      ) : result.gated.length === 0 ? (
        <p className="text-xs text-(--color-ink-faint)">
          No {privacy === "local" ? "local" : "hosted"} judge for this option — try another.
        </p>
      ) : null}

      {result.gated.map((g) => (
        <div key={g.providerId} className="flex items-center gap-2">
          <span className="text-xs text-(--color-ink-faint)">{g.label} — add a key</span>
          <KeyEntry providerId={g.providerId} providerLabel={g.label} keyName={g.keyName} />
        </div>
      ))}
    </div>
  );
}
