// Pure coverage computation for the Datasets screen's overview strip. No React — unit-tested.
// Answers "what is the shape of my whole dataset library?" at a glance: how many sets, how many
// examples, which eval types are represented and in what proportion, which domains, and how many
// carry a governance contract. All FE-derived from fields the API already returns.
import type { Dataset } from "../../lib/api";
import { isBenchDataset, resolveDatasetKind, type DatasetKind } from "./scoring";

export interface KindSlice {
  kind: DatasetKind;
  count: number; // datasets of this kind
  examples: number; // total examples across them
}

export interface CoverageSummary {
  datasetCount: number;
  totalExamples: number;
  evalTypeCount: number; // distinct eval kinds present
  benchCount: number; // governance-bench datasets
  contractCount: number; // datasets shipping a system prompt (a governance contract)
  corpusCount: number; // datasets bound to a corpus
  distribution: KindSlice[]; // non-empty kinds, sorted by count desc then examples desc
  domains: string[]; // union of tags, sorted
}

// A stable display order so the distribution bar reads the same regardless of input order; ties in
// count fall back to this (bench first — it's the flagship), then to example volume.
const KIND_ORDER: DatasetKind[] = ["bench", "keypoint", "similarity", "exact", "contains"];

export function computeCoverage(datasets: Dataset[]): CoverageSummary {
  const slices = new Map<DatasetKind, KindSlice>();
  const domains = new Set<string>();
  let benchCount = 0;
  let contractCount = 0;
  let corpusCount = 0;
  let totalExamples = 0;

  for (const d of datasets) {
    const kind = resolveDatasetKind(d);
    const slot = slices.get(kind) ?? { kind, count: 0, examples: 0 };
    slot.count += 1;
    slot.examples += d.examples.length;
    slices.set(kind, slot);

    totalExamples += d.examples.length;
    if (isBenchDataset(d)) benchCount += 1;
    if (d.system_prompt?.trim()) contractCount += 1;
    if (d.corpus_id) corpusCount += 1;
    for (const t of d.tags ?? []) domains.add(t);
  }

  const distribution = [...slices.values()].sort(
    (a, b) =>
      b.count - a.count ||
      b.examples - a.examples ||
      KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind),
  );

  return {
    datasetCount: datasets.length,
    totalExamples,
    evalTypeCount: distribution.length,
    benchCount,
    contractCount,
    corpusCount,
    distribution,
    domains: [...domains].sort(),
  };
}
