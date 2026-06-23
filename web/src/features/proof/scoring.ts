// Pure scoring-selection helpers. No React, no network — unit-tested in isolation.
import type { Dataset, SelectionPanel, Privacy } from "../../lib/api";
import { CLOUD_KEY_NAMES } from "./selectionMeta";

export type AutoKind = "keypoint" | "similarity" | "exact" | "contains";

// Maps a dataset's display **check hint** to a scoring kind — mirrors the backend `_HINT_KIND`
// (src/orionfold/scoring/rubric.py). exact/numeric → exact equality; substring → contains; "" and
// eyeball stay on the keyless heuristic (Auto must not require a configured judge).
const HINT_KIND: Record<string, AutoKind> = {
  exact: "exact",
  numeric: "exact",
  substring: "contains",
};

// Mirrors the backend `default_rubric_for`: an explicit `check_hint` wins; otherwise keypoint when
// the dataset authored any keypoints, else similarity. Used to show what "Auto" resolves to.
export function resolveAutoKind(dataset: Dataset | undefined): AutoKind {
  const hinted = HINT_KIND[(dataset?.check_hint ?? "").trim()];
  if (hinted) return hinted;
  const hasKeypoints = Boolean(dataset?.examples.some((e) => (e.keypoints?.length ?? 0) > 0));
  return hasKeypoints ? "keypoint" : "similarity";
}

// Per-kind default passing threshold — MUST mirror the backend `DEFAULT_THRESHOLDS`
// (src/orionfold/scoring/rubric.py). Similarity is lenient (0.55 — paraphrased summaries score low
// on lexical overlap; 0.80 wrongly reads them as "no winner"); Keypoint/Judge stay strict (0.80).
// A backend test freezes the same values; a frontend unit asserts this map agrees.
export type TunableKind = "similarity" | "keypoint" | "judge";
export const DEFAULT_THRESHOLDS: Record<TunableKind, number> = {
  similarity: 0.55,
  keypoint: 0.8,
  judge: 0.8,
};

// The prefilled default threshold for a method card: a persisted Settings override wins, else the
// built-in map. `overrides` is the `thresholds` blob from GET /api/settings (already merged on the
// server, so any partial is fine here).
export function thresholdFor(
  kind: TunableKind,
  overrides?: Partial<Record<TunableKind, number>>,
): number {
  return overrides?.[kind] ?? DEFAULT_THRESHOLDS[kind];
}

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

  const mockJudge: JudgeOption | null = privacy === "local" && tier === "economy" ? {
    providerId: "mock_judge",
    label: "Mock judge",
    model: null,
    displayName: "Mock judge — keyless, deterministic",
    recommended: false,
    latest: false,
  } : null;

  if (mockJudge) {
    options.push(mockJudge);
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

  // Mock judge is the keyless, deterministic default for the Local+Cheapest cell (spec invariant),
  // even when a recommended local model exists. Other cells fall back to recommended → latest → first.
  const def =
    mockJudge ?? options.find((o) => o.recommended) ?? options.find((o) => o.latest) ?? options[0] ?? null;

  return {
    options,
    gated,
    defaultProviderId: def?.providerId ?? null,
    defaultModel: def?.model ?? null,
  };
}

export interface JudgeCell {
  privacy: Privacy;
  tier: JudgeTier;
  providerId: string;
  model: string | null;
}

// Where the LLM-judge step opens, given the panel and whether Sandbox is on. The keyless Mock judge
// is the right default ONLY in Sandbox (it's a simulation). With Sandbox OFF a real run must grade
// with a real model: prefer a Hosted cloud judge (any available cloud key), else a real Local judge
// (e.g. Ollama). Returns null when NO real judge is configured and Sandbox is off — the caller then
// disables the LLM-judge method with an "add a key / start Ollama" hint instead of silently mocking.
export function defaultJudgeCell(
  panel: SelectionPanel | undefined,
  sandbox: boolean,
): JudgeCell | null {
  if (!panel) return null;
  if (sandbox) {
    // Sandbox: the keyless, deterministic Mock judge (Local + Cheapest) — its spec-invariant home.
    return { privacy: "local", tier: "economy", providerId: "mock_judge", model: null };
  }
  // Sandbox OFF: walk privacy×tier for the first cell offering a REAL (non-mock) judge. Cloud first
  // (a hosted key means the user opted into paid evaluation), then local; cheapest tier first. We
  // scan the cell's OPTIONS for a real judge rather than its `defaultProviderId` — the Local+Cheapest
  // cell always pins Mock as its UI default, but a real Ollama model still sits in its options.
  const tiers: JudgeTier[] = ["economy", "balanced", "frontier"];
  for (const privacy of ["cloud", "local"] as Privacy[]) {
    for (const tier of tiers) {
      const { options } = filterJudgeModels(panel, privacy, tier);
      const real =
        options.find((o) => o.providerId !== "mock_judge" && o.recommended) ??
        options.find((o) => o.providerId !== "mock_judge" && o.latest) ??
        options.find((o) => o.providerId !== "mock_judge");
      if (real) return { privacy, tier, providerId: real.providerId, model: real.model };
    }
  }
  return null;
}
