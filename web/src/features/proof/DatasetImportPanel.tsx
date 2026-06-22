import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  createDataset,
  extractDataset,
  previewDataset,
  type ImportFormat,
  type ParseResult,
} from "../../lib/api";
import { CHECK_HINTS } from "./tags";

const FORMATS: { value: ImportFormat; label: string; hint: string }[] = [
  { value: "jsonl", label: "JSONL", hint: '{"input": "...", "expected": "..."} per line' },
  { value: "csv", label: "CSV", hint: "input,expected header + one row per example" },
  { value: "markdown", label: "Markdown", hint: "## Input / ## Expected pairs, split by ---" },
];

const DOC_EXTENSIONS = [".xlsx", ".docx", ".pdf"];

// Inline import: pick a format, paste or upload text, preview the parsed pairs (+ warnings),
// then freeze into a new dataset. The server re-parses on freeze, so this preview is advisory.
export function DatasetImportPanel({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [format, setFormat] = useState<ImportFormat>("jsonl");
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<ParseResult | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [checkHint, setCheckHint] = useState("");
  const [source, setSource] = useState("pasted");
  const [extractWarnings, setExtractWarnings] = useState<string[]>([]);

  const previewMutation = useMutation({
    mutationFn: () => previewDataset({ format, text }),
    onSuccess: setPreview,
  });
  const extractMutation = useMutation({
    mutationFn: (file: File) => extractDataset(file),
  });
  const createMutation = useMutation({
    mutationFn: () =>
      createDataset({ name, format, text, tags, source, check_hint: checkHint || null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["datasets"] });
      onClose();
    },
  });

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreview(null);
    previewMutation.reset();
    setExtractWarnings([]);
    setSource(`file:${file.name}`);
    const isDoc = DOC_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (isDoc) {
      const result = await extractMutation.mutateAsync(file);
      setText(result.text);
      setFormat(result.format);
      setExtractWarnings(result.warnings);
    } else {
      setText(await file.text());
    }
  }

  function addTag() {
    const t = tagDraft.trim();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagDraft("");
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
              previewMutation.reset();
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
            previewMutation.reset();
          }}
          rows={6}
          className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-3 font-mono text-xs text-(--color-ink)"
          placeholder={hint}
        />
      </label>

      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".jsonl,.json,.csv,.md,.markdown,.txt,.xlsx,.docx,.pdf"
          onChange={onFile}
          aria-label="Upload dataset file"
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

      {extractMutation.isPending && (
        <p className="text-xs text-(--color-ink-faint)">Reading document…</p>
      )}
      {extractMutation.isError && (
        <p className="text-sm text-(--color-danger)">{(extractMutation.error as Error).message}</p>
      )}
      {extractWarnings.length > 0 && (
        <ul className="grid gap-1 rounded-lg border border-dashed border-(--color-panel-line) p-3 text-xs text-(--color-ink-faint)">
          {extractWarnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}

      {previewMutation.isError && (
        <p className="text-sm text-(--color-danger)">{(previewMutation.error as Error).message}</p>
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
          <label className="grid gap-1 text-sm">
            <span className="text-(--color-ink-muted)">Tags (optional)</span>
            <div className="flex flex-wrap items-center gap-1.5">
              {tags.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTags(tags.filter((x) => x !== t))}
                  className="rounded border border-(--color-panel-line) px-2 py-0.5 text-xs text-(--color-ink-muted) hover:text-(--color-ink)"
                  aria-label={`Remove tag ${t}`}
                >
                  {t} ×
                </button>
              ))}
              <input
                value={tagDraft}
                onChange={(e) => setTagDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addTag();
                  }
                }}
                onBlur={addTag}
                placeholder="e.g. Legal"
                aria-label="Add tag"
                className="rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-1.5 text-xs text-(--color-ink)"
              />
            </div>
          </label>

          <label className="grid gap-1 text-sm">
            <span className="text-(--color-ink-muted)">Check hint (suggests a rubric)</span>
            <select
              value={checkHint}
              onChange={(e) => setCheckHint(e.target.value)}
              className="w-full rounded-lg border border-(--color-panel-line) bg-(--color-panel-card) p-2 text-sm text-(--color-ink)"
            >
              {CHECK_HINTS.map((h) => (
                <option key={h.value} value={h.value}>
                  {h.label}
                </option>
              ))}
            </select>
          </label>

          {createMutation.isError && (
            <p className="text-sm text-(--color-danger)">{(createMutation.error as Error).message}</p>
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
