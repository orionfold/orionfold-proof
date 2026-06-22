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
import { Step, StepLine } from "./WorkflowStep";

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
      <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
        <Step n={1} label="Run on">
          <div className="flex gap-2">
            {(["local", "cloud"] as Privacy[]).map((p) => (
              <button key={p} type="button" aria-pressed={privacy === p} onClick={() => changeAxis({ privacy: p })}
                className={`${toggleBase} ${privacy === p ? toggleActive : toggleIdle}`}>
                {p === "local" ? "Local" : "Hosted"}
              </button>
            ))}
          </div>
        </Step>

        <StepLine />

        <Step n={2} label="Optimize">
          <div className="flex gap-2">
            {JUDGE_TIERS.map((t) => (
              <button key={t.id} type="button" aria-pressed={tier === t.id} onClick={() => changeAxis({ tier: t.id })}
                className={`${toggleBase} ${tier === t.id ? toggleActive : toggleIdle}`}>
                {t.label}
              </button>
            ))}
          </div>
        </Step>

        <StepLine />

        <Step n={3} label="Judge model">
          {result.options.length > 0 ? (
            <select
              aria-label="Judge model"
              value={currentValue}
              onChange={(e) => {
                const [pid, model] = e.target.value.split("::");
                onPick(pid, model === "" ? null : model);
              }}
              className="rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-3 py-2 text-sm text-(--color-ink)"
            >
              {result.options.map((o) => (
                <option key={encode(o.providerId, o.model)} value={encode(o.providerId, o.model)}>
                  {o.displayName}
                </option>
              ))}
            </select>
          ) : (
            <p className="py-2 text-xs text-(--color-ink-faint)">
              {result.gated.length > 0
                ? "Pick one once its key is set below."
                : `No ${privacy === "local" ? "local" : "hosted"} judge for this option — try another.`}
            </p>
          )}
        </Step>
      </div>

      {result.gated.map((g) => (
        <div key={g.providerId} className="flex items-center gap-2">
          <span className="text-xs text-(--color-ink-faint)">{g.label} — add a key</span>
          <KeyEntry providerId={g.providerId} providerLabel={g.label} keyName={g.keyName} />
        </div>
      ))}
    </div>
  );
}
