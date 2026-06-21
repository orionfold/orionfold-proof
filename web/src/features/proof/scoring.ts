// Pure scoring-selection helpers. No React, no network — unit-tested in isolation.
import type { Dataset } from "../../lib/api";

// Mirrors the backend `default_rubric_for`: keypoint when the dataset authored any keypoints,
// else similarity. Used to show what "Auto" resolves to for the selected dataset.
export function resolveAutoKind(dataset: Dataset | undefined): "keypoint" | "similarity" {
  const hasKeypoints = Boolean(dataset?.examples.some((e) => (e.keypoints?.length ?? 0) > 0));
  return hasKeypoints ? "keypoint" : "similarity";
}
