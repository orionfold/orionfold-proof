// Typed client for the local proof API. Zod validates every response at the boundary so a
// drift between the Python models and the cockpit fails loudly instead of rendering garbage.
import { z } from "zod";

export const Privacy = z.enum(["local", "cloud"]);
export type Privacy = z.infer<typeof Privacy>;

export const candidateSchema = z.object({
  id: z.string(),
  label: z.string(),
  provider_id: z.string(),
  privacy: Privacy,
  model: z.string().nullable().optional(),
  system_prompt: z.string().nullable().optional(),
});
export type Candidate = z.infer<typeof candidateSchema>;

export const selectionModelSchema = z.object({
  candidate_id: z.string(),
  model: z.string(),
  display_name: z.string(),
  tier: z.enum(["frontier", "balanced", "economy"]),
  cost_class: z.enum(["free", "$", "$$", "$$$"]),
  context_window: z.number().nullable().optional(),
  latest: z.boolean(),
  recommended: z.boolean(),
  // hf-own-models: curated HF/GGUF models carry family "orionfold" + a repo_id, and gate
  // availability per model (pulled vs. "Pull to enable"). Optional for back-compat.
  family: z.string().nullable().optional(),
  repo_id: z.string().nullable().optional(),
  // Omitted ⇒ available (cloud/standard models never gate per-model); the backend always sends
  // an explicit boolean. Optional keeps existing fixtures and back-compat valid.
  available: z.boolean().optional(),
  reason: z.string().nullable().optional(),
});
export type SelectionModel = z.infer<typeof selectionModelSchema>;

export const selectionGroupSchema = z.object({
  provider_id: z.string(),
  label: z.string(),
  privacy: Privacy,
  available: z.boolean(),
  supports_custom: z.boolean(),
  candidate_id: z.string().nullable().optional(),
  models: z.array(selectionModelSchema),
});
export type SelectionGroup = z.infer<typeof selectionGroupSchema>;

export const selectionPanelSchema = z.object({
  providers: z.array(selectionGroupSchema),
});
export type SelectionPanel = z.infer<typeof selectionPanelSchema>;

export const exampleSchema = z.object({
  input_text: z.string(),
  expected_text: z.string(),
  keypoints: z.array(z.string()).optional().default([]),
  // Per-row governance contract (bench datasets); all optional → plain datasets are unaffected.
  // Read with `?? []` / `?? false`; left optional (not defaulted) so fixtures stay terse.
  expected_behavior: z.enum(["answer", "route", "refuse"]).nullable().optional(),
  expected_citations: z.array(z.string()).optional(),
  accepted_source_ids: z.array(z.string()).optional(),
  requires_citation: z.boolean().optional(),
  requires_refusal: z.boolean().optional(),
  requires_route: z.boolean().optional(),
});

export const corpusSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().default(""),
  source_ids: z.array(z.string()).default([]),
});
export type Corpus = z.infer<typeof corpusSchema>;

export const datasetSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  examples: z.array(exampleSchema),
  corpus_id: z.string().nullable().optional(),
  // A governing system prompt the dataset ships with (e.g. a bench's citation/refusal/route
  // contract). When present, the cockpit auto-fills the System prompt field with it so the dataset
  // is turnkey. Provenance only — never a config_hash input on the backend.
  system_prompt: z.string().nullable().optional(),
  // Seeded sample datasets are flagged so the UI can badge them and offer targeted removal.
  // Optional (not defaulted) so the inferred type stays loose for fixtures; absent reads as falsy.
  is_sample: z.boolean().optional(),
  // Display/management metadata — lives on the API row only (never the domain model). Optional
  // (not defaulted) so the inferred type stays loose for fixtures, matching is_sample; consumers
  // read with `?? []` / `?? ""`.
  tags: z.array(z.string()).optional(),
  created_at: z.string().optional(),
  source: z.string().optional(),
  check_hint: z.string().nullable().optional(),
});
export type Dataset = z.infer<typeof datasetSchema>;

export const importFormatSchema = z.enum(["jsonl", "csv", "markdown"]);
export type ImportFormat = z.infer<typeof importFormatSchema>;

export const parseResultSchema = z.object({
  examples: z.array(exampleSchema),
  warnings: z.array(z.string()),
  count: z.number(),
});
export type ParseResult = z.infer<typeof parseResultSchema>;

export const extractResultSchema = z.object({
  format: importFormatSchema,
  text: z.string(),
  warnings: z.array(z.string()),
});
export type ExtractResult = z.infer<typeof extractResultSchema>;

export const rubricKindSchema = z.enum(["exact", "contains", "similarity", "keypoint", "judge", "bench", "none"]);
export type RubricKind = z.infer<typeof rubricKindSchema>;

// Per-row governance verdict carried on a bench-scored ResultRow (citation/refusal/route/leak).
export const benchVerdictSchema = z.object({
  citation_ok: z.boolean(),
  refusal_ok: z.boolean(),
  route_ok: z.boolean(),
  thinking_leak: z.boolean(),
  private_state_risk: z.boolean(),
  alias_residue: z.boolean(),
  bare_answer: z.boolean(),
  cited_source_ids: z.array(z.string()),
  passed: z.boolean(),
  strict_passed: z.boolean(),
});
export type BenchVerdict = z.infer<typeof benchVerdictSchema>;

export const rubricSchema = z.object({
  kind: rubricKindSchema,
  threshold: z.number(),
  case_sensitive: z.boolean(),
  judge_provider_id: z.string().nullable().optional(),
  judge_model: z.string().nullable().optional(),
});

export const leaderboardEntrySchema = z.object({
  candidate_id: z.string(),
  label: z.string(),
  provider_id: z.string(),
  privacy: Privacy,
  model: z.string().nullable().optional(),
  system_prompt: z.string().nullable().optional(),
  total: z.number(),
  pass_count: z.number(),
  pass_rate: z.number(),
  avg_score: z.number(),
  avg_latency_ms: z.number(),
  total_estimated_cost_usd: z.number(),
  failure_count: z.number(),
  error_count: z.number(),
  recommended: z.boolean(),
  cost_per_quality: z.number().nullable().optional(),
  // Throughput (Σoutput_tokens / Σlatency_s); null when no measured latency. Presentation only.
  tokens_per_second: z.number().nullable().optional(),
});
export type LeaderboardEntry = z.infer<typeof leaderboardEntrySchema>;

// Cross-run standings (B4). Mirrors the Python TrackRecordEntry/TrackRecordGroup — a pure rollup
// over existing leaderboard fields, so these touch no scoring/config_hash. pass_rate is pooled
// (Σpasses / Σexamples across the group's runs), not a mean of per-run rates.
export const trackRecordEntrySchema = z.object({
  candidate_id: z.string(),
  label: z.string(),
  provider_id: z.string(),
  privacy: Privacy,
  model: z.string().nullable().optional(),
  runs: z.number(),
  total_examples: z.number(),
  total_passes: z.number(),
  pass_rate: z.number(),
  avg_cost_usd: z.number(),
  times_recommended: z.number(),
});
export type TrackRecordEntry = z.infer<typeof trackRecordEntrySchema>;

export const trackRecordGroupSchema = z.object({
  dataset_id: z.string(),
  dataset_name: z.string(),
  rubric_kind: rubricKindSchema,
  runs: z.number(),
  entries: z.array(trackRecordEntrySchema),
});
export type TrackRecordGroup = z.infer<typeof trackRecordGroupSchema>;

export const resultRowSchema = z.object({
  candidate_id: z.string(),
  example_index: z.number(),
  input_text: z.string(),
  expected_text: z.string(),
  output_text: z.string(),
  score: z.number().nullable(),
  passed: z.boolean().nullable(),
  latency_ms: z.number(),
  estimated_cost_usd: z.number(),
  input_tokens: z.number().default(0),
  output_tokens: z.number().default(0),
  judge_cost_usd: z.number().default(0),
  judge_latency_ms: z.number().default(0),
  bench_detail: benchVerdictSchema.nullable().optional(),
  privacy: Privacy,
  error: z.string().nullable(),
});
export type ResultRow = z.infer<typeof resultRowSchema>;

export const proofBriefSchema = z.object({
  task_name: z.string(),
  decision_question: z.string(),
  success_criteria: z.string(),
});
export type ProofBrief = z.infer<typeof proofBriefSchema>;

export const proofRunSchema = z.object({
  id: z.string(),
  brief: proofBriefSchema,
  dataset_id: z.string(),
  dataset_name: z.string(),
  rubric: rubricSchema,
  candidates: z.array(candidateSchema),
  config_hash: z.string(),
  created_at: z.string(),
  // Tightened to match the Pydantic Literal so model drift fails loudly at the boundary.
  status: z.literal("complete"),
  mode: z.enum(["full", "quick"]).default("full"),
  chosen_winner: z.string().nullable().optional(),
});

export const runCostSummarySchema = z.object({
  candidate_cost_usd: z.number(),
  judge_cost_usd: z.number(),
  total_cost_usd: z.number(),
});
export type RunCostSummary = z.infer<typeof runCostSummarySchema>;

export const proofReportSchema = z.object({
  run: proofRunSchema,
  leaderboard: z.array(leaderboardEntrySchema),
  results: z.array(resultRowSchema),
  cost_summary: runCostSummarySchema,
});
export type ProofReport = z.infer<typeof proofReportSchema>;

export const healthSchema = z.object({
  status: z.string(),
  service: z.string(),
  version: z.string(),
});
export type Health = z.infer<typeof healthSchema>;

async function getJson<T>(url: string, schema: z.ZodType<T>): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GET ${url} → HTTP ${res.status}`);
  return schema.parse(await res.json());
}

export function getHealth(): Promise<Health> {
  return getJson("/api/health", healthSchema);
}

export function getDatasets(): Promise<Dataset[]> {
  return getJson("/api/datasets", z.array(datasetSchema));
}

export async function previewDataset(body: {
  format: ImportFormat;
  text: string;
}): Promise<ParseResult> {
  const res = await fetch("/api/datasets/preview", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Preview failed (HTTP ${res.status})`);
  }
  return parseResultSchema.parse(await res.json());
}

export async function createDataset(body: {
  name: string;
  description?: string;
  format: ImportFormat;
  text: string;
  tags?: string[];
  source?: string;
  check_hint?: string | null;
}): Promise<Dataset> {
  const res = await fetch("/api/datasets", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Import failed (HTTP ${res.status})`);
  }
  return datasetSchema.parse(await res.json());
}

export async function extractDataset(file: File): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/datasets/extract", { method: "POST", body: form });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Could not read the file (HTTP ${res.status})`);
  }
  return extractResultSchema.parse(await res.json());
}

export async function updateDataset(
  id: string,
  patch: { tags?: string[]; description?: string; check_hint?: string | null },
): Promise<Dataset> {
  const res = await fetch(`/api/datasets/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Update failed (HTTP ${res.status})`);
  }
  return datasetSchema.parse(await res.json());
}

export function getSelection(): Promise<SelectionPanel> {
  return getJson("/api/selection", selectionPanelSchema);
}

// Provider liveness: a free, token-free probe per active provider so the cockpit can gray out a
// candidate that would fail at run time (down / quota / revoked key / local server off).
export const ProviderHealthStatus = z.enum([
  "ok",
  "auth",
  "permission",
  "quota",
  "down",
  "unreachable",
]);
export type ProviderHealthStatus = z.infer<typeof ProviderHealthStatus>;

export const providerHealthSchema = z.object({
  provider_id: z.string(),
  status: ProviderHealthStatus,
  message: z.string(),
  remediation: z.string(),
});
export type ProviderHealth = z.infer<typeof providerHealthSchema>;

export const providerHealthPanelSchema = z.object({
  providers: z.array(providerHealthSchema),
});
export type ProviderHealthPanel = z.infer<typeof providerHealthPanelSchema>;

export function getProviderHealth(): Promise<ProviderHealthPanel> {
  return getJson("/api/health/providers", providerHealthPanelSchema);
}

export const resolvedSelectorSchema = z.object({
  label: z.string(),
  candidate_id: z.string(),
  display_name: z.string(),
  provider_id: z.string(),
  cost_class: z.enum(["free", "$", "$$", "$$$"]),
});
export type ResolvedSelector = z.infer<typeof resolvedSelectorSchema>;

export const unmetSelectorSchema = z.object({
  label: z.string(),
  needs_provider_id: z.string(),
  needs_provider_label: z.string(),
  key_name: z.string(),
});
export type UnmetSelector = z.infer<typeof unmetSelectorSchema>;

export const resolvedRecipeSchema = z.object({
  id: z.string(),
  title: z.string(),
  subtitle: z.string(),
  decision_question: z.string(),
  candidate_ids: z.array(z.string()),
  resolved: z.array(resolvedSelectorSchema),
  unmet: z.array(unmetSelectorSchema),
});
export type ResolvedRecipe = z.infer<typeof resolvedRecipeSchema>;

export const recipesPanelSchema = z.object({ recipes: z.array(resolvedRecipeSchema) });
export type RecipesPanel = z.infer<typeof recipesPanelSchema>;

export function getRecipes(): Promise<RecipesPanel> {
  return getJson("/api/recipes", recipesPanelSchema);
}

const credentialStatusSchema = z.object({ provider_id: z.string(), available: z.boolean() });

export async function setProviderKey(
  providerId: string,
  key: string,
): Promise<z.infer<typeof credentialStatusSchema>> {
  const res = await fetch("/api/credentials", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ provider_id: providerId, key }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Saving the key failed (HTTP ${res.status})`);
  }
  return credentialStatusSchema.parse(await res.json());
}

// Past runs, newest first — each is a full report, so the Receipts view can show the winner
// and reopen the run in the cockpit without a second fetch.
export function getRuns(): Promise<ProofReport[]> {
  return getJson("/api/runs", z.array(proofReportSchema));
}

// Cross-run standings, one group per (dataset, rubric kind). Pass a datasetId to narrow to one
// dataset. Quick/unscored runs are excluded server-side by the core rollup.
export function getTrackRecord(datasetId?: string): Promise<TrackRecordGroup[]> {
  const url = datasetId
    ? `/api/track-record?dataset_id=${encodeURIComponent(datasetId)}`
    : "/api/track-record";
  return getJson(url, z.array(trackRecordGroupSchema));
}

// Record the operator's head-to-head pick on a quick-compare run (candidate id or "tie").
export function patchWinner(runId: string, chosen_winner: string): Promise<ProofReport> {
  return mutate(`/api/runs/${runId}/winner`, "PATCH", proofReportSchema, { chosen_winner });
}

export interface PromptVariant {
  name: string;
  system_prompt: string;
}

export interface QuickExample {
  input_text: string;
  expected_text: string;
}

export interface RunRequest {
  dataset_id?: string;
  candidate_ids: string[];
  rubric?: z.infer<typeof rubricSchema> | null;
  brief: ProofBrief;
  prompt_variants?: PromptVariant[];
  examples?: QuickExample[];
  mode?: "full" | "quick";
  // Models-mode task instruction: one system prompt applied to every selected candidate.
  system_prompt?: string;
}

export function scoredByLabel(rubric: z.infer<typeof rubricSchema>): string {
  if (rubric.kind === "keypoint") return "Keypoint coverage";
  if (rubric.kind === "judge") return `LLM judge · ${rubric.judge_model ?? rubric.judge_provider_id ?? "model"}`;
  if (rubric.kind === "bench") return "Governance bench (citation · refusal · route)";
  if (rubric.kind === "none") return "Quick check (unscored)";
  return { similarity: "Similarity", exact: "Exact match", contains: "Contains" }[rubric.kind] ?? rubric.kind;
}

export async function createRun(body: RunRequest): Promise<ProofReport> {
  const res = await fetch("/api/runs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Run failed (HTTP ${res.status})`);
  }
  return proofReportSchema.parse(await res.json());
}

export function receiptUrl(runId: string, fmt: "md" | "html" | "json"): string {
  return `/api/runs/${runId}/receipt.${fmt}`;
}

// Same receipt, served for rendering (Content-Disposition: inline) so the cockpit can embed it.
// `theme` pins the iframe to the cockpit's resolved theme (overrides the receipt's OS media query).
export function receiptPreviewUrl(runId: string, theme?: "light" | "dark"): string {
  const t = theme ? `&theme=${theme}` : "";
  return `/api/runs/${runId}/receipt.html?inline=1${t}`;
}

// --- Streaming run (Server-Sent Events) ---------------------------------------------------
// The cockpit runs proofs through this so a long run (e.g. a slow local model) shows live,
// cell-by-cell progress instead of a silent spinner. See ADR-0003.

export interface RunStartEvent {
  type: "start";
  total: number;
  n_examples: number;
  candidates: { id: string; label: string; provider_id: string; privacy: "local" | "cloud" }[];
}

export interface RunProgressEvent {
  type: "progress";
  done: number;
  candidate_id: string;
  example_index: number;
  passed: boolean;
  error: boolean;
}

export interface RunStreamHandlers {
  onStart?: (e: RunStartEvent) => void;
  onProgress?: (e: RunProgressEvent) => void;
}

// --- Settings + sample data ---------------------------------------------------------------

export const thresholdsSchema = z.object({
  similarity: z.number(),
  keypoint: z.number(),
  judge: z.number(),
});
export type Thresholds = z.infer<typeof thresholdsSchema>;

export const settingsSchema = z.object({
  sandbox_enabled: z.boolean(),
  thresholds: thresholdsSchema,
});
export type Settings = z.infer<typeof settingsSchema>;

export const dataCountsSchema = z.object({ datasets: z.number(), receipts: z.number() });
export type DataCounts = z.infer<typeof dataCountsSchema>;

export function getSettings(): Promise<Settings> {
  return getJson("/api/settings", settingsSchema);
}

async function mutate<T>(
  url: string,
  method: string,
  schema: z.ZodType<T>,
  body?: unknown,
): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `${method} ${url} → HTTP ${res.status}`);
  }
  return schema.parse(await res.json());
}

export function setSandbox(enabled: boolean): Promise<Settings> {
  return mutate("/api/settings", "PUT", settingsSchema, { sandbox_enabled: enabled });
}

export function setThresholds(thresholds: Thresholds): Promise<Settings> {
  return mutate("/api/settings", "PUT", settingsSchema, { thresholds });
}

export function seedSampleData(): Promise<DataCounts> {
  return mutate("/api/sample-data/seed", "POST", dataCountsSchema);
}

export function removeSampleData(): Promise<DataCounts> {
  return mutate("/api/sample-data", "DELETE", dataCountsSchema);
}

export function clearAllData(): Promise<DataCounts> {
  return mutate("/api/data", "DELETE", dataCountsSchema);
}

// POST the run and consume the SSE stream, invoking handlers as frames arrive. Resolves with
// the final, schema-validated ProofReport — so callers can use it as a mutationFn unchanged.
export async function createRunStream(
  body: RunRequest,
  handlers: RunStreamHandlers = {},
): Promise<ProofReport> {
  const res = await fetch("/api/runs/stream", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Run failed (HTTP ${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let report: ProofReport | null = null;

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by a blank line; keep the trailing partial in the buffer.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const dataLine = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const evt = JSON.parse(dataLine.slice("data:".length).trim());
      if (evt.type === "start") handlers.onStart?.(evt as RunStartEvent);
      else if (evt.type === "progress") handlers.onProgress?.(evt as RunProgressEvent);
      else if (evt.type === "report") report = proofReportSchema.parse(evt.report);
    }
  }

  if (!report) throw new Error("The run ended without a receipt.");
  return report;
}
