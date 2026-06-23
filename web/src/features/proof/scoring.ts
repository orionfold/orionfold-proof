// Pure scoring-selection helpers. No React, no network — unit-tested in isolation.
import type { Dataset, SelectionPanel, Privacy } from "../../lib/api";
import { CLOUD_KEY_NAMES } from "./selectionMeta";

// Mirrors the backend `default_rubric_for`: keypoint when the dataset authored any keypoints,
// else similarity. Used to show what "Auto" resolves to for the selected dataset.
export function resolveAutoKind(dataset: Dataset | undefined): "keypoint" | "similarity" {
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
