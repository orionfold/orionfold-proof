// Heuristic parser for the "retrieved public context" shape some bench datasets flatten into a
// single input_text (the Advisor governance corpus convention): a Question, then a
// "Retrieved public context:" block of repeating `Source N: <id>` records, each optionally carrying
// Label / Class / Title / Excerpt. This is a CONVENTION, not a universal schema — an arbitrary
// imported JSONL set has free-form input_text — so the parser is detect-and-degrade: it returns the
// structured form ONLY when the markers are unmistakable, and `null` otherwise so the caller falls
// back to rendering the raw field. Pure + unit-tested; the React layer stays dumb.

export interface RetrievedSource {
  id: string;
  label?: string;
  class?: string;
  title?: string;
  excerpt?: string;
}

export interface RetrievedContext {
  question: string;
  sources: RetrievedSource[];
}

const CONTEXT_MARKER = "Retrieved public context:";
// A source block opens with `Source <n>: <id>` on its own line.
const SOURCE_LINE = /^Source\s+\d+:\s*(.+)$/;
// The known sub-fields, mapped to the record key they populate. Unknown `Key: value` lines inside a
// block are ignored (they fold into the currently-open field as continuation text instead).
const FIELD_KEYS: Record<string, keyof Omit<RetrievedSource, "id">> = {
  Label: "label",
  Class: "class",
  Title: "title",
  Excerpt: "excerpt",
};
const FIELD_LINE = /^(Label|Class|Title|Excerpt):\s*(.*)$/;

// Parse the flattened retrieved-context shape, or return null when it isn't present. Returning null
// (not a degenerate object) is the contract the caller relies on to fall back to the plain field.
export function parseRetrievedContext(input: string): RetrievedContext | null {
  if (!input) return null;
  const markerAt = input.indexOf(CONTEXT_MARKER);
  if (markerAt === -1) return null;

  // The question is everything before the marker, with a leading "Question:" label stripped.
  const head = input.slice(0, markerAt).trim();
  const question = head.replace(/^Question:\s*/i, "").trim();

  const body = input.slice(markerAt + CONTEXT_MARKER.length);
  const lines = body.split("\n");

  const sources: RetrievedSource[] = [];
  let current: RetrievedSource | null = null;
  let openField: keyof Omit<RetrievedSource, "id"> | null = null;

  const closeField = () => {
    // Trim the accumulated field once its block ends (excerpts can run several lines).
    if (current && openField && current[openField] !== undefined) {
      current[openField] = current[openField]!.trim();
    }
  };

  for (const line of lines) {
    const srcMatch = line.match(SOURCE_LINE);
    if (srcMatch) {
      closeField();
      current = { id: srcMatch[1].trim() };
      sources.push(current);
      openField = null;
      continue;
    }
    if (!current) continue; // text before the first Source: line is noise.

    const fieldMatch = line.match(FIELD_LINE);
    if (fieldMatch) {
      closeField();
      const key = FIELD_KEYS[fieldMatch[1]];
      const value = fieldMatch[2];
      current[key] = value;
      openField = value === "" ? null : key;
      continue;
    }

    // A continuation line for the currently-open field (e.g. a multi-line excerpt).
    if (openField) {
      current[openField] = `${current[openField] ?? ""}\n${line}`;
    }
  }
  closeField();

  // Degrade unless we actually found source records — a bare "Retrieved public context:" with no
  // Source blocks is not the structured shape and should render as plain text.
  if (sources.length === 0) return null;
  return { question, sources };
}
