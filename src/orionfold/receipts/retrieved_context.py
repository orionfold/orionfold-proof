"""Parser for the flattened "retrieved public context" shape that some bench datasets pack into a
single ``input_text`` (the Advisor governance corpus convention): a Question, then a
``Retrieved public context:`` block of repeating ``Source N: <id>`` records, each optionally
carrying Label / Class / Title / Excerpt.

This is a **faithful port** of the cockpit's ``web/src/features/proof/retrievedContext.ts`` so the
receipt renders the SAME structured shape the live cockpit shows for datasets / corpus / evals —
one parsing→rendering solution, two surfaces. Like the TS original it is *detect-and-degrade*: it
returns the structured form ONLY when the markers are unmistakable, and ``None`` otherwise so the
caller falls back to rendering the raw field as-is (an arbitrary imported JSONL set has free-form
``input_text``). Keep the two implementations in sync; the shared test fixtures guard the parity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CONTEXT_MARKER = "Retrieved public context:"
# A source block opens with `Source <n>: <id>` on its own line.
_SOURCE_LINE = re.compile(r"^Source\s+\d+:\s*(.+)$")
# The known sub-fields, mapped to the record attribute they populate. Unknown `Key: value` lines
# inside a block fold into the currently-open field as continuation text instead.
_FIELD_LINE = re.compile(r"^(Label|Class|Title|Excerpt):\s*(.*)$")
_FIELD_ATTR = {"Label": "label", "Class": "class_", "Title": "title", "Excerpt": "excerpt"}


@dataclass
class RetrievedSource:
    id: str
    label: str | None = None
    class_: str | None = None
    title: str | None = None
    excerpt: str | None = None


@dataclass
class RetrievedContext:
    question: str
    sources: list[RetrievedSource]


def parse_retrieved_context(input_text: str) -> RetrievedContext | None:
    """Parse the flattened retrieved-context shape, or return ``None`` when it isn't present.
    Returning ``None`` (not a degenerate object) is the contract the caller relies on to fall back
    to the plain field — mirrors the TS parser exactly."""
    if not input_text:
        return None
    marker_at = input_text.find(_CONTEXT_MARKER)
    if marker_at == -1:
        return None

    # The question is everything before the marker, with a leading "Question:" label stripped.
    head = input_text[:marker_at].strip()
    question = re.sub(r"^Question:\s*", "", head, flags=re.IGNORECASE).strip()

    body = input_text[marker_at + len(_CONTEXT_MARKER) :]
    sources: list[RetrievedSource] = []
    current: RetrievedSource | None = None
    open_field: str | None = None

    def close_field() -> None:
        # Trim the accumulated field once its block ends (excerpts can run several lines).
        if current is not None and open_field is not None:
            val = getattr(current, open_field)
            if val is not None:
                setattr(current, open_field, val.strip())

    for line in body.split("\n"):
        src = _SOURCE_LINE.match(line)
        if src:
            close_field()
            current = RetrievedSource(id=src.group(1).strip())
            sources.append(current)
            open_field = None
            continue
        if current is None:
            continue  # text before the first Source: line is noise.

        field = _FIELD_LINE.match(line)
        if field:
            close_field()
            attr = _FIELD_ATTR[field.group(1)]
            value = field.group(2)
            setattr(current, attr, value)
            open_field = None if value == "" else attr
            continue

        # A continuation line for the currently-open field (e.g. a multi-line excerpt).
        if open_field is not None:
            prev = getattr(current, open_field) or ""
            setattr(current, open_field, f"{prev}\n{line}")

    close_field()

    # Degrade unless we actually found source records — a bare marker with no Source blocks is not
    # the structured shape and should render as plain text.
    if not sources:
        return None
    return RetrievedContext(question=question, sources=sources)
