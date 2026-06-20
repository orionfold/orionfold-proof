import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  createDataset,
  previewDataset,
  type ImportFormat,
  type ParseResult,
} from "../../lib/api";

const FORMATS: { value: ImportFormat; label: string; hint: string }[] = [
  { value: "jsonl", label: "JSONL", hint: '{"input": "...", "expected": "..."} per line' },
  { value: "csv", label: "CSV", hint: "input,expected header + one row per example" },
  { value: "markdown", label: "Markdown", hint: "## Input / ## Expected pairs, split by ---" },
];

// Inline import: pick a format, paste or upload text, preview the parsed pairs (+ warnings),
// then freeze into a new dataset. The server re-parses on freeze, so this preview is advisory.
export function DatasetImportPanel({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [format, setFormat] = useState<ImportFormat>("jsonl");
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<ParseResult | null>(null);

  const previewMutation = useMutation({
    mutationFn: () => previewDataset({ format, text }),
    onSuccess: setPreview,
  });
  const createMutation = useMutation({
    mutationFn: () => createDataset({ name, format, text }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      onClose();
    },
  });

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setText(await file.text());
    setPreview(null);
  }

  const hint = FORMATS.find((f) => f.value === format)?.hint ?? "";

  return (
    <section className="grid gap-4 rounded-xl border border-(--color-panel-line) bg-(--color-panel-card) p-5">
      <div className="flex flex-wrap items-center gap-2">
        {FORMATS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => {
              setFormat(f.value);
              setPreview(null);
            }}
            aria-pressed={format === f.value}
            className={
              "rounded-lg border px-3 py-1.5 text-sm " +
              (format === f.value
                ? "border-(--color-accent) text-(--color-ink)"
                : "border-(--color-panel-line) text-(--color-ink-muted) hover:text-(--color-ink)")
            }
          >
            {f.label}
          </button>
        ))}
        <span className="text-xs text-(--color-ink-faint)">{hint}</span>
      </div>

      <label className="grid gap-1 text-sm">
        <span className="text-(--color-ink-muted)">Paste or upload your examples</span>
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPreview(null);
          }}
          rows={6}
          className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-3 font-mono text-xs text-(--color-ink)"
          placeholder={hint}
        />
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".jsonl,.json,.csv,.md,.markdown,.txt"
          onChange={onFile}
          className="text-xs text-(--color-ink-muted)"
        />
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={!text.trim() || previewMutation.isPending}
          className="rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink) disabled:opacity-50"
        >
          {previewMutation.isPending ? "Parsing…" : "Preview"}
        </button>
      </div>

      {previewMutation.isError && (
        <p className="text-sm text-rose-300">{(previewMutation.error as Error).message}</p>
      )}

      {preview && (
        <div className="grid gap-3">
          <p className="text-sm text-(--color-ink-muted)">
            {preview.count} example{preview.count === 1 ? "" : "s"} parsed.
          </p>
          {preview.warnings.length > 0 && (
            <ul className="grid gap-1 rounded-lg border border-dashed border-(--color-panel-line) p-3 text-xs text-(--color-ink-faint)">
              {preview.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          <ol className="grid gap-3">
            {preview.examples.map((ex, i) => (
              <li key={i} className="grid gap-1 border-t border-(--color-panel-line) pt-3 text-sm">
                <span className="text-xs text-(--color-ink-faint)">Input</span>
                <span className="whitespace-pre-wrap text-(--color-ink)">{ex.input_text}</span>
                <span className="text-xs text-(--color-ink-faint)">Expected</span>
                <span className="whitespace-pre-wrap text-(--color-ink)">{ex.expected_text}</span>
              </li>
            ))}
          </ol>

          <label className="grid gap-1 text-sm">
            <span className="text-(--color-ink-muted)">Dataset name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-2 text-sm text-(--color-ink)"
              placeholder="e.g. Client summaries v1"
            />
          </label>
          {createMutation.isError && (
            <p className="text-sm text-rose-300">{(createMutation.error as Error).message}</p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => createMutation.mutate()}
              disabled={!name.trim() || createMutation.isPending}
              className="rounded-lg bg-(--color-accent-strong) px-3 py-1.5 text-sm font-medium text-(--color-accent-ink) disabled:opacity-50"
            >
              {createMutation.isPending ? "Freezing…" : "Freeze dataset"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink-muted)"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
