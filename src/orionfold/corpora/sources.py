"""Parse the flattened "retrieved public context" shape out of bench example ``input_text`` and
aggregate it into enriched :class:`CorpusSource` records.

This is the Python mirror of the frontend ``retrievedContext.ts`` parser. A bench dataset following
the Advisor governance convention embeds its corpus sources inline as repeating
``Source N: <id>`` / ``Label:`` / ``Class:`` / ``Title:`` / ``Excerpt:`` blocks; the corpus manifest
itself stores only ``source_ids``. So the rich content is *derived* from the examples at read time —
detect-and-degrade: parse when the structure is unmistakable, fall back to bare ids otherwise.
"""

from __future__ import annotations

import re

from orionfold.domain.models import CorpusSource, Example

_CONTEXT_MARKER = "Retrieved public context:"
_SOURCE_LINE = re.compile(r"^Source\s+\d+:\s*(.+)$")
_FIELD_LINE = re.compile(r"^(Label|Class|Title|Excerpt):\s*(.*)$")
_FIELD_KEYS = {"Label": "label", "Class": "class", "Title": "title", "Excerpt": "excerpt"}


def parse_retrieved_sources(input_text: str) -> list[dict[str, str]]:
    """Parse the retrieved-context block into ordered source dicts, or ``[]`` when absent.

    Each dict always carries ``id`` and only the sub-fields actually present (so a sparse block
    doesn't fabricate empty titles). Returning ``[]`` (not raising) is the degrade contract.
    """
    if not input_text:
        return []
    marker_at = input_text.find(_CONTEXT_MARKER)
    if marker_at == -1:
        return []

    body = input_text[marker_at + len(_CONTEXT_MARKER) :]
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    open_field: str | None = None

    def close_field() -> None:
        if current is not None and open_field and open_field in current:
            current[open_field] = current[open_field].strip()

    for line in body.split("\n"):
        src = _SOURCE_LINE.match(line)
        if src:
            close_field()
            current = {"id": src.group(1).strip()}
            records.append(current)
            open_field = None
            continue
        if current is None:
            continue
        field = _FIELD_LINE.match(line)
        if field:
            close_field()
            key = _FIELD_KEYS[field.group(1)]
            value = field.group(2)
            current[key] = value
            open_field = None if value == "" else key
            continue
        if open_field:
            current[open_field] = f"{current.get(open_field, '')}\n{line}"
    close_field()
    return records


def enrich_corpus_sources(
    examples: list[Example], *, source_ids: list[str]
) -> list[CorpusSource]:
    """Aggregate enriched source records across a corpus's bound examples.

    Each distinct source id appears once (the first enriched parse wins). ``cited_by`` counts the
    examples whose ``expected_citations``/``accepted_source_ids`` name the source. When no example
    yields any structured record, fall back to the corpus manifest's bare ``source_ids`` so the
    browser still shows a non-empty, if unenriched, corpus.
    """
    enriched: dict[str, dict[str, str]] = {}
    order: list[str] = []
    cited: dict[str, int] = {}

    for ex in examples:
        for sid in set(ex.expected_citations) | set(ex.accepted_source_ids):
            cited[sid] = cited.get(sid, 0) + 1
        for rec in parse_retrieved_sources(ex.input_text):
            sid = rec["id"]
            if sid not in enriched:
                enriched[sid] = rec
                order.append(sid)

    if not order:
        # No structured records anywhere — list the manifest ids bare so the corpus isn't blank.
        return [CorpusSource(id=sid, cited_by=cited.get(sid, 0)) for sid in source_ids]

    return [
        CorpusSource(
            id=sid,
            title=enriched[sid].get("title", ""),
            label=enriched[sid].get("label", ""),
            excerpt=enriched[sid].get("excerpt", ""),
            cited_by=cited.get(sid, 0),
            **{"class": enriched[sid].get("class", "")},
        )
        for sid in order
    ]
