// Typed client for the local proof API. Zod validates every response at the boundary so a
// drift between the Python models and the cockpit fails loudly instead of rendering garbage.
import { z } from "zod";

export const Privacy = z.enum(["local", "cloud"]);

export const candidateSchema = z.object({
  id: z.string(),
  label: z.string(),
  provider_id: z.string(),
  privacy: Privacy,
  model: z.string().nullable().optional(),
});
export type Candidate = z.infer<typeof candidateSchema>;

export const exampleSchema = z.object({
  input_text: z.string(),
  expected_text: z.string(),
});

export const datasetSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  examples: z.array(exampleSchema),
});
export type Dataset = z.infer<typeof datasetSchema>;

export const rubricSchema = z.object({
  kind: z.enum(["exact", "contains", "similarity"]),
  threshold: z.number(),
  case_sensitive: z.boolean(),
});

export const leaderboardEntrySchema = z.object({
  candidate_id: z.string(),
  label: z.string(),
  provider_id: z.string(),
  privacy: Privacy,
  model: z.string().nullable().optional(),
  total: z.number(),
  pass_count: z.number(),
  pass_rate: z.number(),
  avg_score: z.number(),
  avg_latency_ms: z.number(),
  total_estimated_cost_usd: z.number(),
  failure_count: z.number(),
  recommended: z.boolean(),
});
export type LeaderboardEntry = z.infer<typeof leaderboardEntrySchema>;

export const resultRowSchema = z.object({
  candidate_id: z.string(),
  example_index: z.number(),
  input_text: z.string(),
  expected_text: z.string(),
  output_text: z.string(),
  score: z.number(),
  passed: z.boolean(),
  latency_ms: z.number(),
  estimated_cost_usd: z.number(),
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
});

export const proofReportSchema = z.object({
  run: proofRunSchema,
  leaderboard: z.array(leaderboardEntrySchema),
  results: z.array(resultRowSchema),
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

export function getCandidates(): Promise<Candidate[]> {
  return getJson("/api/candidates", z.array(candidateSchema));
}

// Past runs, newest first — each is a full report, so the Receipts view can show the winner
// and reopen the run in the cockpit without a second fetch.
export function getRuns(): Promise<ProofReport[]> {
  return getJson("/api/runs", z.array(proofReportSchema));
}

export interface RunRequest {
  dataset_id: string;
  candidate_ids: string[];
  brief: ProofBrief;
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
export function receiptPreviewUrl(runId: string): string {
  return `/api/runs/${runId}/receipt.html?inline=1`;
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
