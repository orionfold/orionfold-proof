import { Plus, X } from "lucide-react";
import type { PromptVariant, SelectionPanel } from "../../lib/api";
import { SelectField } from "./SelectField";
import { inputCls } from "./formStyles";
import { flattenModels } from "./promptVariantsHelpers";

export interface PromptVariantsProps {
  variants: PromptVariant[];
  modelId: string;
  panel: SelectionPanel;
  onChangeVariants: (next: PromptVariant[]) => void;
  onChangeModel: (id: string) => void;
}

// "One model, N prompts": pick a single model, then author named system-prompt variants. The
// model is fixed so the leaderboard isolates which wording wins.
export function PromptVariants(props: PromptVariantsProps) {
  const { variants, modelId, panel, onChangeVariants, onChangeModel } = props;
  const models = flattenModels(panel);

  const update = (i: number, patch: Partial<PromptVariant>) =>
    onChangeVariants(variants.map((v, idx) => (idx === i ? { ...v, ...patch } : v)));
  const add = () => onChangeVariants([...variants, { name: "", system_prompt: "" }]);
  const remove = (i: number) => onChangeVariants(variants.filter((_, idx) => idx !== i));

  return (
    <fieldset className="grid gap-4 text-sm">
      <legend className="text-(--color-ink-muted)">Prompt variants</legend>
      <p className="text-xs text-(--color-ink-faint)">
        One model, several system prompts. Hold the model fixed and compare which wording wins on the
        same examples.
      </p>

      <label className="grid gap-1.5 text-sm">
        <span className="text-(--color-ink-muted)">Prompt model</span>
        <SelectField
          aria-label="Prompt model"
          value={modelId}
          onChange={(e) => onChangeModel(e.target.value)}
        >
          {models.map((m) => (
            <option key={m.candidateId} value={m.candidateId} disabled={!m.available}>
              {m.label}
              {m.available ? "" : " (add a key)"}
            </option>
          ))}
        </SelectField>
        <span className="text-xs text-(--color-ink-faint)">
          The single model every prompt variant is compared on.
        </span>
      </label>

      <div className="grid gap-3">
        {variants.map((v, i) => (
          <div key={i} className="grid gap-2 rounded-lg border border-(--color-panel-line) p-3">
            <div className="flex items-center gap-2">
              <input
                aria-label={`Variant name ${i + 1}`}
                value={v.name}
                placeholder="Name (e.g. Terse)"
                onChange={(e) => update(i, { name: e.target.value })}
                className={inputCls + " flex-1"}
              />
              <button
                type="button"
                aria-label={`Remove variant ${i + 1}`}
                onClick={() => remove(i)}
                disabled={variants.length <= 1}
                className="rounded-lg p-2 text-(--color-ink-muted) hover:text-(--color-ink) disabled:opacity-40"
              >
                <X aria-hidden className="h-4 w-4" />
              </button>
            </div>
            <textarea
              aria-label={`Variant prompt ${i + 1}`}
              value={v.system_prompt}
              placeholder="System prompt for this variant…"
              rows={3}
              onChange={(e) => update(i, { system_prompt: e.target.value })}
              className={inputCls}
            />
          </div>
        ))}
      </div>

      <div>
        <button
          type="button"
          onClick={add}
          className="flex items-center gap-1.5 rounded-lg border border-(--color-panel-line) px-3 py-2 text-sm text-(--color-ink-muted) hover:text-(--color-ink)"
        >
          <Plus aria-hidden className="h-4 w-4" /> Add prompt
        </button>
      </div>
    </fieldset>
  );
}
