# Scoring Section Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat Scoring-method control with grouped method cards (guidance + cost) and a two-step Local/Hosted → Cheapest/Balanced/Best judge filter that feeds a model dropdown with an opinionated default.

**Architecture:** Pure frontend over data already in `/api/selection` and the existing `rubric` schema. Two new pure helpers (`resolveAutoKind`, `filterJudgeModels`) carry the logic; two new presentational components (`MethodCard`, `JudgeFilter`) carry the UI; `ScoringMethod` is slimmed to compose them; the control moves inside the `RunSetup` form, above the run button.

**Tech Stack:** React 18 + TypeScript, Vite, Tailwind v4, TanStack Query, Zod, Vitest + Testing Library, Playwright.

## Global Constraints

- **No backend / scoring / receipt change.** RECEIPT_VERSION stays **5**; `config_hash` unaffected for equivalent selections.
- **Keyless default preserved:** the judge default is the synthetic **Mock judge** (`judge_provider_id: "mock_judge"`, `judge_model: null`), reached as Local + Cheapest.
- **Exclude `mock_good` / `mock_bad`** from judge options (they are answer-generators, not graders).
- **No secrets** in UI/logs; cloud key entry reuses the existing `KeyEntry` + `CLOUD_KEY_NAMES`.
- **Judge cost stays separate** server-side (untouched here).
- **Tailwind v4 CSS vars use the parenthesis shorthand:** `bg-(--color-x)`, never `bg-[--color-x]`.
- **Tier → label mapping:** `economy`→"Cheapest", `balanced`→"Balanced", `frontier`→"Best".
- Run a single Vitest file with: `pnpm --dir web test --run <path>`.

## File Structure

| File | Responsibility |
| --- | --- |
| `web/src/lib/api.ts` | Add `keypoints` to `exampleSchema` (Modify). |
| `web/src/features/proof/scoring.ts` *(new)* | Pure helpers: `resolveAutoKind`, `filterJudgeModels` + their types. |
| `web/src/features/proof/selectionMeta.ts` | Add `METHOD_META` + `JUDGE_TIERS` (Modify; keep `CLOUD_KEY_NAMES`). |
| `web/src/features/proof/MethodCard.tsx` *(new)* | Presentational method card (title, guidance, cost, selected). |
| `web/src/features/proof/JudgeFilter.tsx` *(new)* | Two-step filter + model dropdown + KeyEntry gating. |
| `web/src/features/proof/ScoringMethod.tsx` | Slimmed: two grouped sections + JudgeFilter; new `dataset?` prop. |
| `web/src/features/proof/RunSetup.tsx` | Render `<ScoringMethod>` before the run button; new rubric props. |
| `web/src/features/proof/ProofCockpit.tsx` | Pass rubric props into RunSetup; drop the standalone ScoringMethod. |
| `web/tests/e2e/*` | Assert grouped cards + Mock-judge default; keyless run unchanged. |

---

### Task 1: Dataset keypoints in the schema + `resolveAutoKind`

**Files:**
- Modify: `web/src/lib/api.ts:44-47` (exampleSchema)
- Create: `web/src/features/proof/scoring.ts`
- Test: `web/src/features/proof/scoring.test.ts`

**Interfaces:**
- Consumes: `Dataset` from `../../lib/api`.
- Produces: `resolveAutoKind(dataset: Dataset | undefined): "keypoint" | "similarity"`.

- [ ] **Step 1: Add `keypoints` to the example schema**

In `web/src/lib/api.ts`, change `exampleSchema` to:

```ts
export const exampleSchema = z.object({
  input_text: z.string(),
  expected_text: z.string(),
  keypoints: z.array(z.string()).optional().default([]),
});
```

- [ ] **Step 2: Write the failing test**

Create `web/src/features/proof/scoring.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { resolveAutoKind } from "./scoring";
import type { Dataset } from "../../lib/api";

function ds(keypoints: string[][]): Dataset {
  return {
    id: "d",
    name: "D",
    description: "",
    examples: keypoints.map((kp) => ({ input_text: "i", expected_text: "e", keypoints: kp })),
  };
}

describe("resolveAutoKind", () => {
  it("returns keypoint when any example has keypoints", () => {
    expect(resolveAutoKind(ds([[], ["22%"]]))).toBe("keypoint");
  });
  it("returns similarity when no example has keypoints", () => {
    expect(resolveAutoKind(ds([[], []]))).toBe("similarity");
  });
  it("returns similarity for an undefined dataset", () => {
    expect(resolveAutoKind(undefined)).toBe("similarity");
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pnpm --dir web test --run src/features/proof/scoring.test.ts`
Expected: FAIL — `resolveAutoKind` is not exported / module not found.

- [ ] **Step 4: Write the helper**

Create `web/src/features/proof/scoring.ts`:

```ts
// Pure scoring-selection helpers. No React, no network — unit-tested in isolation.
import type { Dataset } from "../../lib/api";

// Mirrors the backend `default_rubric_for`: keypoint when the dataset authored any keypoints,
// else similarity. Used to show what "Auto" resolves to for the selected dataset.
export function resolveAutoKind(dataset: Dataset | undefined): "keypoint" | "similarity" {
  const hasKeypoints = Boolean(dataset?.examples.some((e) => (e.keypoints?.length ?? 0) > 0));
  return hasKeypoints ? "keypoint" : "similarity";
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pnpm --dir web test --run src/features/proof/scoring.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add web/src/lib/api.ts web/src/features/proof/scoring.ts web/src/features/proof/scoring.test.ts
git commit -m "feat(web): dataset keypoints in schema + resolveAutoKind helper"
```

---

### Task 2: `filterJudgeModels` helper + scoring metadata

**Files:**
- Modify: `web/src/features/proof/scoring.ts` (add filter logic + types)
- Modify: `web/src/features/proof/selectionMeta.ts` (add `METHOD_META`, `JUDGE_TIERS`)
- Test: `web/src/features/proof/scoring.test.ts` (extend)

**Interfaces:**
- Consumes: `SelectionPanel`, `Privacy` from `../../lib/api`; `CLOUD_KEY_NAMES` from `./selectionMeta`.
- Produces:
  - `type JudgeTier = "economy" | "balanced" | "frontier"`
  - `interface JudgeOption { providerId: string; label: string; model: string | null; displayName: string; recommended: boolean; latest: boolean }`
  - `interface GatedProvider { providerId: string; label: string; keyName: string }`
  - `interface JudgeFilterResult { options: JudgeOption[]; gated: GatedProvider[]; defaultProviderId: string | null; defaultModel: string | null }`
  - `filterJudgeModels(panel: SelectionPanel | undefined, privacy: Privacy, tier: JudgeTier): JudgeFilterResult`
  - `METHOD_META` (record keyed by method id) and `JUDGE_TIERS` (ordered `{id, label}` list) from `selectionMeta`.

- [ ] **Step 1: Add metadata constants**

In `web/src/features/proof/selectionMeta.ts`, append:

```ts
// Per-method copy for the grouped scoring cards. `group` drives the free-vs-paid section.
export const METHOD_META = {
  auto: { label: "Auto", group: "free", cost: "Free", guidance: "We pick the right free check for your dataset." },
  keypoint: { label: "Keypoint", group: "free", cost: "Free", guidance: "Checks your authored key facts appear in the answer." },
  similarity: { label: "Similarity", group: "free", cost: "Free", guidance: "Scores by semantic closeness to the expected answer." },
  judge: { label: "LLM judge", group: "paid", cost: "$ per run · slower", guidance: "A model grades each answer against the expected one." },
} as const;

// The "Optimize" axis of the judge filter, ordered cheapest → best. Maps UI labels to catalog tiers.
export const JUDGE_TIERS = [
  { id: "economy", label: "Cheapest" },
  { id: "balanced", label: "Balanced" },
  { id: "frontier", label: "Best" },
] as const;
```

- [ ] **Step 2: Write the failing tests**

Append to `web/src/features/proof/scoring.test.ts`:

```ts
import { filterJudgeModels } from "./scoring";
import type { SelectionPanel } from "../../lib/api";

function model(over: Partial<import("../../lib/api").SelectionModel> = {}) {
  return {
    candidate_id: "c", model: "m", display_name: "M", tier: "economy" as const,
    cost_class: "$" as const, context_window: null, latest: false, recommended: false, ...over,
  };
}
const panel: SelectionPanel = {
  providers: [
    { provider_id: "mock_good", label: "Mock", privacy: "local", available: true, supports_custom: false, candidate_id: null, models: [] },
    { provider_id: "ollama", label: "Ollama", privacy: "local", available: true, supports_custom: false, candidate_id: null,
      models: [model({ model: "llama-eco", display_name: "Llama eco", tier: "economy", recommended: true })] },
    { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: true, supports_custom: false, candidate_id: null,
      models: [
        model({ model: "haiku", display_name: "Haiku", tier: "economy", recommended: true }),
        model({ model: "opus", display_name: "Opus", tier: "frontier", latest: true }),
      ] },
    { provider_id: "openai", label: "OpenAI", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
  ],
};

describe("filterJudgeModels", () => {
  it("defaults Local+Cheapest to keyless Mock judge", () => {
    const r = filterJudgeModels(panel, "local", "economy");
    expect(r.options[0]).toMatchObject({ providerId: "mock_judge", model: null });
    expect(r.defaultProviderId).toBe("mock_judge");
    expect(r.defaultModel).toBeNull();
  });
  it("excludes mock_good / mock_bad from options", () => {
    const r = filterJudgeModels(panel, "local", "economy");
    expect(r.options.some((o) => o.providerId === "mock_good")).toBe(false);
  });
  it("filters Hosted+Cheapest to economy cloud models and prefers a recommended default", () => {
    const r = filterJudgeModels(panel, "cloud", "economy");
    expect(r.options.map((o) => o.model)).toEqual(["haiku"]);
    expect(r.defaultProviderId).toBe("anthropic");
    expect(r.defaultModel).toBe("haiku");
  });
  it("falls back to latest when no recommended survives the tier filter", () => {
    const r = filterJudgeModels(panel, "cloud", "frontier");
    expect(r.defaultModel).toBe("opus");
  });
  it("lists unavailable cloud providers as gated (key needed)", () => {
    const r = filterJudgeModels(panel, "cloud", "economy");
    expect(r.gated).toEqual([{ providerId: "openai", label: "OpenAI", keyName: "OPENAI_API_KEY" }]);
  });
  it("returns no options for an empty local Best combo", () => {
    const r = filterJudgeModels(panel, "local", "frontier");
    expect(r.options).toEqual([]);
    expect(r.defaultProviderId).toBeNull();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pnpm --dir web test --run src/features/proof/scoring.test.ts`
Expected: FAIL — `filterJudgeModels` not exported.

- [ ] **Step 4: Implement the helper**

Append to `web/src/features/proof/scoring.ts`:

```ts
import type { SelectionPanel, Privacy } from "../../lib/api";
import { CLOUD_KEY_NAMES } from "./selectionMeta";

export type JudgeTier = "economy" | "balanced" | "frontier";

export interface JudgeOption {
  providerId: string;
  label: string;
  model: string | null;
  displayName: string;
  recommended: boolean;
  latest: boolean;
}
export interface GatedProvider {
  providerId: string;
  label: string;
  keyName: string;
}
export interface JudgeFilterResult {
  options: JudgeOption[];
  gated: GatedProvider[];
  defaultProviderId: string | null;
  defaultModel: string | null;
}

// mock_good / mock_bad are answer-generators, never judges.
const EXCLUDED = new Set(["mock_good", "mock_bad"]);

// Build the judge options for one (privacy, tier) cell. The synthetic keyless Mock judge is the
// single Local+Cheapest option. Unavailable cloud providers (models: []) become `gated` rows that
// surface a KeyEntry. The default follows: recommended → latest → first option (all from available
// providers, since unavailable providers contribute no options).
export function filterJudgeModels(
  panel: SelectionPanel | undefined,
  privacy: Privacy,
  tier: JudgeTier,
): JudgeFilterResult {
  const options: JudgeOption[] = [];
  const gated: GatedProvider[] = [];

  if (privacy === "local" && tier === "economy") {
    options.push({
      providerId: "mock_judge",
      label: "Mock judge",
      model: null,
      displayName: "Mock judge — keyless, deterministic",
      recommended: false,
      latest: false,
    });
  }

  for (const g of panel?.providers ?? []) {
    if (EXCLUDED.has(g.provider_id) || g.privacy !== privacy) continue;
    if (!g.available) {
      const keyName = CLOUD_KEY_NAMES[g.provider_id];
      if (keyName) gated.push({ providerId: g.provider_id, label: g.label, keyName });
      continue;
    }
    for (const m of g.models) {
      if (m.tier !== tier) continue;
      options.push({
        providerId: g.provider_id,
        label: g.label,
        model: m.model,
        displayName: `${m.display_name} · ${g.label}`,
        recommended: m.recommended,
        latest: m.latest,
      });
    }
  }

  const def =
    options.find((o) => o.recommended) ?? options.find((o) => o.latest) ?? options[0] ?? null;

  return {
    options,
    gated,
    defaultProviderId: def?.providerId ?? null,
    defaultModel: def?.model ?? null,
  };
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pnpm --dir web test --run src/features/proof/scoring.test.ts`
Expected: PASS (9 tests total).

- [ ] **Step 6: Commit**

```bash
git add web/src/features/proof/scoring.ts web/src/features/proof/scoring.test.ts web/src/features/proof/selectionMeta.ts
git commit -m "feat(web): filterJudgeModels helper + scoring card/tier metadata"
```

---

### Task 3: `MethodCard` presentational component

**Files:**
- Create: `web/src/features/proof/MethodCard.tsx`
- Test: `web/src/features/proof/MethodCard.test.tsx`

**Interfaces:**
- Produces: `MethodCard(props: { title: string; guidance: string; cost: string; selected: boolean; onSelect: () => void })`.

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/MethodCard.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MethodCard } from "./MethodCard";

describe("MethodCard", () => {
  it("renders title, guidance and cost", () => {
    render(<MethodCard title="Keypoint" guidance="Checks facts" cost="Free" selected={false} onSelect={() => {}} />);
    expect(screen.getByText("Keypoint")).toBeInTheDocument();
    expect(screen.getByText("Checks facts")).toBeInTheDocument();
    expect(screen.getByText("Free")).toBeInTheDocument();
  });
  it("reflects selected state via aria-pressed and fires onSelect", () => {
    const onSelect = vi.fn();
    render(<MethodCard title="Auto" guidance="g" cost="Free" selected onSelect={onSelect} />);
    const btn = screen.getByRole("button", { name: /Auto/i });
    expect(btn).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(btn);
    expect(onSelect).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run src/features/proof/MethodCard.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

Create `web/src/features/proof/MethodCard.tsx`:

```tsx
// A single scoring-method card: title, one-line guidance, and a cost chip. Selection mirrors the
// accent pattern used by CandidatePicker chips.
export interface MethodCardProps {
  title: string;
  guidance: string;
  cost: string;
  selected: boolean;
  onSelect: () => void;
}

const base = "grid gap-1 rounded-lg border p-3 text-left text-sm transition-colors";
const active = "border-(--color-accent)/50 bg-(--color-accent)/10";
const idle = "border-(--color-panel-line) hover:border-(--color-panel-line-strong)";

export function MethodCard({ title, guidance, cost, selected, onSelect }: MethodCardProps) {
  return (
    <button type="button" aria-pressed={selected} onClick={onSelect} className={`${base} ${selected ? active : idle}`}>
      <span className="font-medium text-(--color-ink)">{title}</span>
      <span className="text-xs text-(--color-ink-muted)">{guidance}</span>
      <span className="text-xs text-(--color-ink-faint)">{cost}</span>
    </button>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test --run src/features/proof/MethodCard.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/MethodCard.tsx web/src/features/proof/MethodCard.test.tsx
git commit -m "feat(web): MethodCard presentational component"
```

---

### Task 4: `JudgeFilter` component (two-step filter + dropdown + KeyEntry)

**Files:**
- Create: `web/src/features/proof/JudgeFilter.tsx`
- Test: `web/src/features/proof/JudgeFilter.test.tsx`

**Interfaces:**
- Consumes: `getSelection`, `SelectionPanel`, `Privacy` from `../../lib/api`; `filterJudgeModels`, `JudgeTier` from `./scoring`; `JUDGE_TIERS`, `CLOUD_KEY_NAMES` from `./selectionMeta`; `KeyEntry` from `./KeyEntry`.
- Produces: `JudgeFilter(props: { selectedProviderId: string | null; selectedModel: string | null; onPick: (providerId: string, model: string | null) => void })`.

**Notes:** Local state holds the two axes (default `local` / `economy`). On axis change, if the new cell has options, emit `onPick(default…)`; otherwise keep the prior judge so a keyless run stays valid. The model dropdown encodes each option value as `` `${providerId}::${model ?? ""}` ``.

- [ ] **Step 1: Write the failing tests**

Create `web/src/features/proof/JudgeFilter.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JudgeFilter } from "./JudgeFilter";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({
    providers: [
      { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false, supports_custom: false, candidate_id: null, models: [] },
    ],
  })),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("JudgeFilter", () => {
  it("defaults to Local + Cheapest with Mock judge selected", () => {
    render(wrap(<JudgeFilter selectedProviderId="mock_judge" selectedModel={null} onPick={() => {}} />));
    expect(screen.getByRole("button", { name: /Local/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Cheapest/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(/Mock judge/i)).toBeInTheDocument();
  });

  it("shows KeyEntry for an unavailable cloud provider after switching to Hosted", async () => {
    render(wrap(<JudgeFilter selectedProviderId="mock_judge" selectedModel={null} onPick={() => {}} />));
    fireEvent.click(screen.getByRole("button", { name: /Hosted/i }));
    expect(await screen.findByText(/add a key/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm --dir web test --run src/features/proof/JudgeFilter.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

Create `web/src/features/proof/JudgeFilter.tsx`:

```tsx
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test --run src/features/proof/JudgeFilter.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/JudgeFilter.tsx web/src/features/proof/JudgeFilter.test.tsx
git commit -m "feat(web): JudgeFilter two-step picker with KeyEntry gating"
```

---

### Task 5: Recompose `ScoringMethod` into grouped cards + JudgeFilter

**Files:**
- Modify: `web/src/features/proof/ScoringMethod.tsx` (full rewrite of the body)
- Modify: `web/src/features/proof/ScoringMethod.test.tsx` (rewrite for new structure)

**Interfaces:**
- Consumes: `MethodCard`, `JudgeFilter`, `resolveAutoKind`, `METHOD_META` from siblings; `Dataset`, `rubricSchema` from api.
- Produces: `ScoringMethod(props: { value: Rubric | null; onChange: (next: Rubric | null) => void; dataset?: Dataset })` — `Rubric` re-exported as today.

- [ ] **Step 1: Rewrite the test**

Replace `web/src/features/proof/ScoringMethod.test.tsx` with:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScoringMethod } from "./ScoringMethod";
import type { Dataset } from "../../lib/api";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ providers: [] })),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}
const kpDataset: Dataset = {
  id: "d", name: "D", description: "",
  examples: [{ input_text: "i", expected_text: "e", keypoints: ["22%"] }],
};

describe("ScoringMethod", () => {
  it("renders the free group with Auto/Keypoint/Similarity and the paid LLM judge", () => {
    render(wrap(<ScoringMethod value={null} onChange={() => {}} dataset={kpDataset} />));
    expect(screen.getByRole("button", { name: /Auto/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Keypoint/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Similarity/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /LLM judge/i })).toBeInTheDocument();
  });

  it("shows what Auto resolves to for the dataset", () => {
    render(wrap(<ScoringMethod value={null} onChange={() => {}} dataset={kpDataset} />));
    expect(screen.getByText(/Keypoint coverage/i)).toBeInTheDocument();
  });

  it("emits a keypoint rubric when Keypoint is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    fireEvent.click(screen.getByRole("button", { name: /Keypoint/i }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "keypoint" }));
  });

  it("offers the keyless Mock judge when LLM judge is chosen", () => {
    const onChange = vi.fn();
    render(wrap(<ScoringMethod value={null} onChange={onChange} dataset={kpDataset} />));
    fireEvent.click(screen.getByRole("button", { name: /LLM judge/i }));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ kind: "judge", judge_provider_id: "mock_judge" }));
    expect(screen.getByText(/Mock judge/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run src/features/proof/ScoringMethod.test.tsx`
Expected: FAIL — Auto resolution text / new structure not present.

- [ ] **Step 3: Rewrite the component**

Replace the body of `web/src/features/proof/ScoringMethod.tsx` with:

```tsx
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
  const autoGuidance = `We pick the right free check — ${autoResolved} for this dataset.`;

  return (
    <fieldset className="grid gap-3 text-sm">
      <legend className="text-(--color-ink-muted)">Scoring method</legend>

      <span className="text-xs uppercase tracking-wide text-(--color-ink-faint)">
        Free · instant · repeatable
      </span>
      <div className="grid gap-2 sm:grid-cols-3">
        <MethodCard title="Auto" guidance={autoGuidance} cost="Free" selected={method === "auto"} onSelect={() => selectMethod("auto")} />
        <MethodCard title={METHOD_META.keypoint.label} guidance={METHOD_META.keypoint.guidance} cost={METHOD_META.keypoint.cost} selected={method === "keypoint"} onSelect={() => selectMethod("keypoint")} />
        <MethodCard title={METHOD_META.similarity.label} guidance={METHOD_META.similarity.guidance} cost={METHOD_META.similarity.cost} selected={method === "similarity"} onSelect={() => selectMethod("similarity")} />
      </div>

      <span className="text-xs uppercase tracking-wide text-(--color-ink-faint)">
        Costs money · adds latency
      </span>
      <MethodCard title={METHOD_META.judge.label} guidance={METHOD_META.judge.guidance} cost={METHOD_META.judge.cost} selected={method === "judge"} onSelect={() => selectMethod("judge")} />

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm --dir web test --run src/features/proof/ScoringMethod.test.tsx`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/ScoringMethod.tsx web/src/features/proof/ScoringMethod.test.tsx
git commit -m "feat(web): grouped scoring cards + two-step judge filter in ScoringMethod"
```

---

### Task 6: Move ScoringMethod into RunSetup (placement fix)

**Files:**
- Modify: `web/src/features/proof/RunSetup.tsx` (new rubric props + render ScoringMethod before button)
- Modify: `web/src/features/proof/ProofCockpit.tsx:163-185` (pass rubric props; drop standalone ScoringMethod)
- Test: `web/src/features/proof/RunSetup.test.tsx` (create if absent, or extend)

**Interfaces:**
- Consumes: `ScoringMethod`, `Rubric` from `./ScoringMethod`.
- Produces: `RunSetupProps` gains `rubric: Rubric | null` and `onRubricChange: (next: Rubric | null) => void`.

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/RunSetup.test.tsx` (mock selection so JudgeFilter's query is satisfied):

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RunSetup } from "./RunSetup";
import type { Dataset, SelectionPanel } from "../../lib/api";

vi.mock("../../lib/api", async (orig) => ({
  ...(await orig<typeof import("../../lib/api")>()),
  getSelection: vi.fn(async () => ({ providers: [] })),
}));

const datasets: Dataset[] = [{ id: "d", name: "D", description: "", examples: [{ input_text: "i", expected_text: "e", keypoints: ["x"] }] }];
const panel: SelectionPanel = { providers: [] };

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("RunSetup", () => {
  it("renders the scoring method above the run button", () => {
    render(wrap(
      <RunSetup
        datasets={datasets} panel={panel} datasetId="d" onDatasetChange={() => {}}
        selectedCandidates={["mock_good"]} onToggleCandidate={() => {}}
        brief={{ task_name: "T", decision_question: "Q", success_criteria: "" }} onBriefChange={() => {}}
        onRun={() => {}} isRunning={false} hasRun={false} error={null}
        rubric={null} onRubricChange={() => {}}
      />,
    ));
    const scoring = screen.getByText(/Scoring method/i);
    const runBtn = screen.getByRole("button", { name: /Run proof/i });
    // Scoring method appears before the run button in document order.
    expect(scoring.compareDocumentPosition(runBtn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run src/features/proof/RunSetup.test.tsx`
Expected: FAIL — `rubric`/`onRubricChange` not in props; scoring method not rendered.

- [ ] **Step 3: Add rubric props + render ScoringMethod in RunSetup**

In `web/src/features/proof/RunSetup.tsx`:

Add to imports:
```ts
import { ScoringMethod, type Rubric } from "./ScoringMethod";
```

Add to `RunSetupProps`:
```ts
  rubric: Rubric | null;
  onRubricChange: (next: Rubric | null) => void;
```

Destructure them in the component (`const { …, rubric, onRubricChange } = props;`) and, inside the form, insert the scoring control between the decision-question label (ends line ~97) and the `{error && …}` block:

```tsx
        <ScoringMethod
          value={rubric}
          onChange={onRubricChange}
          dataset={datasets.find((d) => d.id === datasetId)}
        />
```

- [ ] **Step 4: Wire ProofCockpit and remove the standalone ScoringMethod**

In `web/src/features/proof/ProofCockpit.tsx`, add to the `<RunSetup … />` props (near line 174):

```tsx
          rubric={rubric}
          onRubricChange={setRubric}
```

Then delete the standalone line (currently `web/src/features/proof/ProofCockpit.tsx:185`):

```tsx
        <ScoringMethod value={rubric} onChange={setRubric} />
```

Remove the now-unused `ScoringMethod` import at the top of `ProofCockpit.tsx` **only if** it is no longer referenced (keep the `type Rubric` import if still used by `rubric` state).

- [ ] **Step 5: Run tests to verify they pass**

Run: `pnpm --dir web test --run src/features/proof/RunSetup.test.tsx`
Expected: PASS (1 test).

- [ ] **Step 6: Full unit suite + typecheck/build**

Run: `pnpm --dir web test --run`
Expected: PASS (all suites green).

Run: `pnpm --dir web build`
Expected: `tsc --noEmit` clean + Vite build succeeds (no unused-import or type errors).

- [ ] **Step 7: Commit**

```bash
git add web/src/features/proof/RunSetup.tsx web/src/features/proof/RunSetup.test.tsx web/src/features/proof/ProofCockpit.tsx
git commit -m "feat(web): scoring method is the last configure step, above Run proof"
```

---

### Task 7: e2e + visual verification

**Files:**
- Modify: the scoring-related Playwright spec under `web/tests/e2e/` (find with grep below)

**Interfaces:** none (integration).

- [ ] **Step 1: Locate the e2e spec(s) touching scoring**

Run: `grep -rln "Scored by\|Scoring method\|Mock judge\|LLM judge" web/tests`
Expected: lists the keyless-scoring spec(s) to update.

- [ ] **Step 2: Update/confirm the keyless assertion**

Ensure a spec still asserts the keyless default path renders the grouped cards and that a default Auto run produces "Scored by Keypoint coverage". If the prior spec clicked a flat "Auto" button, it still works (Auto is now a card with role button name /Auto/i). Add an assertion that the LLM-judge card reveals the "Run on" / "Optimize" toggles and a "Mock judge" option:

```ts
await page.getByRole("button", { name: /LLM judge/i }).click();
await expect(page.getByRole("button", { name: /Local/i })).toBeVisible();
await expect(page.getByText(/Mock judge/i)).toBeVisible();
```

- [ ] **Step 3: Rebuild the embed (required before e2e)**

Run:
```bash
pnpm --dir web build && rm -rf src/orionfold/server/static && cp -r web/dist src/orionfold/server/static
```
Expected: `EMBED OK` (index.html present).

- [ ] **Step 4: Run the e2e suite**

Run: `pnpm --dir web e2e`
Expected: all specs PASS, including the keyless "Scored by Keypoint coverage" proof.

- [ ] **Step 5: Browser visual verification**

Use the `browser-visual-verification` skill against a fresh server on a provably-free port:
- Configure view shows the two groups (free trio + paid judge card) with cost chips.
- Auto card reads "…Keypoint coverage for this dataset".
- LLM judge card expands the Run-on / Optimize toggles + model dropdown; default = Mock judge.
- Switching to Hosted with no key shows the inline KeyEntry ("add a key").
- No console errors; no secrets on screen.

- [ ] **Step 6: Commit**

```bash
git add web/tests
git commit -m "test(e2e): grouped scoring cards + keyless Mock-judge default"
```

---

## Self-Review

**Spec coverage:**
- Grouped free-vs-paid cards → Task 5 (structure) + Task 3 (card). ✓
- Guidance + cost indicators → `METHOD_META` Task 2, rendered Task 5. ✓
- Live Auto resolution → `resolveAutoKind` Task 1, rendered Task 5; needs `keypoints` in schema (Task 1). ✓
- Two-step judge filter (privacy → tier → dropdown, opinionated default) → `filterJudgeModels` Task 2, `JudgeFilter` Task 4. ✓
- Keyless Mock judge = Local+Cheapest default → Task 2 logic + Task 4/5 wiring + tests. ✓
- Exclude mock_good/mock_bad → Task 2 (`EXCLUDED`) + test. ✓
- Per-provider `recommended` fallback (recommended→latest→first) → Task 2 default rule + tests. ✓
- Key-gating reuse of KeyEntry → Task 4. ✓
- Empty-combo calm state → Task 4 + Task 2 test. ✓
- Placement fix (scoring above Run proof) → Task 6 + ordering test. ✓
- Invariants (RECEIPT_VERSION 5, config_hash, no secrets, Tailwind paren vars) → Global Constraints; no backend touched. ✓
- Testing (unit/e2e/visual) → Tasks 1–7. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code. ✓

**Type consistency:** `filterJudgeModels(panel, privacy, tier) → JudgeFilterResult` used identically in Task 4; `JudgeOption.providerId/model/displayName/recommended/latest` consistent; `onPick(providerId, model)` consistent across JudgeFilter/ScoringMethod; `ScoringMethodProps` adds `dataset?`; `RunSetupProps` adds `rubric`/`onRubricChange`. ✓
