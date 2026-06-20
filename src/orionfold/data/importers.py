"""Dataset importers — turn user-supplied JSONL / CSV / Markdown text into frozen example
pairs. Pure and keyless: no network, no secrets, deterministic. Each parser skips rows it
cannot read (recording a warning) and the entry point refuses input that yields no example.
"""

from __future__ import annotations

import csv
import io
import json
import re
from typing import Literal

from pydantic import BaseModel

from orionfold.domain.models import Example

ImportFormat = Literal["jsonl", "csv", "markdown"]


class ParseResult(BaseModel):
    """Parsed examples plus per-row warnings (skipped lines) and the valid count."""

    examples: list[Example]
    warnings: list[str]
    count: int


class DatasetParseError(ValueError):
    """No valid example could be parsed — surfaced to the API as HTTP 422."""


def parse_dataset(text: str, fmt: ImportFormat) -> ParseResult:
    if fmt == "jsonl":
        examples, warnings = _parse_jsonl(text)
    elif fmt == "csv":
        examples, warnings = _parse_csv(text)
    elif fmt == "markdown":
        examples, warnings = _parse_markdown(text)
    else:  # defensive — the Literal makes this unreachable for typed callers
        raise DatasetParseError(f"Unknown format: {fmt}")
    if not examples:
        raise DatasetParseError(
            "No valid examples found. Each example needs a non-empty input and expected value."
        )
    return ParseResult(examples=examples, warnings=warnings, count=len(examples))


def _pair_from_obj(obj: dict) -> tuple[str, str] | None:
    """Pull a trimmed (input, expected) from a dict, accepting both key spellings."""
    raw_in = obj.get("input", obj.get("input_text", ""))
    raw_out = obj.get("expected", obj.get("expected_text", ""))
    if not isinstance(raw_in, str) or not isinstance(raw_out, str):
        return None
    input_text, expected_text = raw_in.strip(), raw_out.strip()
    if not input_text or not expected_text:
        return None
    return input_text, expected_text


def _parse_jsonl(text: str) -> tuple[list[Example], list[str]]:
    examples: list[Example] = []
    warnings: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            warnings.append(f"Line {lineno}: not valid JSON — skipped.")
            continue
        if not isinstance(obj, dict):
            warnings.append(f"Line {lineno}: expected a JSON object — skipped.")
            continue
        pair = _pair_from_obj(obj)
        if pair is None:
            warnings.append(f"Line {lineno}: missing input/expected — skipped.")
            continue
        examples.append(Example(input_text=pair[0], expected_text=pair[1]))
    return examples, warnings


def _parse_csv(text: str) -> tuple[list[Example], list[str]]:
    examples: list[Example] = []
    warnings: list[str] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return examples, warnings
    headers = {(name or "").strip().lower(): name for name in reader.fieldnames}
    input_key = headers.get("input", headers.get("input_text"))
    expected_key = headers.get("expected", headers.get("expected_text"))
    if input_key is None or expected_key is None:
        missing = [c for c, k in (("input", input_key), ("expected", expected_key)) if k is None]
        warnings.append(f"CSV is missing required column(s): {', '.join(missing)} — skipping.")
        return examples, warnings
    for rowno, row in enumerate(reader, start=2):  # row 1 is the header
        input_text = (row.get(input_key) or "").strip()
        expected_text = (row.get(expected_key) or "").strip()
        if not input_text or not expected_text:
            warnings.append(f"Row {rowno}: missing input/expected — skipped.")
            continue
        examples.append(Example(input_text=input_text, expected_text=expected_text))
    return examples, warnings


_HEADING = re.compile(r"^#{1,6}\s+(.*\S)\s*$")
_RULE = re.compile(r"^-{3,}\s*$")


def _parse_markdown(text: str) -> tuple[list[Example], list[str]]:
    # First pass: split into (label, content-lines) sections on headings; a horizontal rule
    # ends the current section. Only content under an Input/Expected heading is kept.
    sections: list[tuple[str, list[str]]] = []
    label: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if label is not None:
            sections.append((label, buffer.copy()))

    for raw in text.splitlines():
        heading = _HEADING.match(raw)
        if heading:
            flush()
            label = heading.group(1).strip().lower()
            buffer = []
        elif _RULE.match(raw):
            flush()
            label = None
            buffer = []
        elif label is not None:
            buffer.append(raw)
    flush()

    # Second pass: pair each 'input' section with the immediately following 'expected'.
    examples: list[Example] = []
    warnings: list[str] = []
    idx = 0
    example_no = 0
    while idx < len(sections):
        section_label, content = sections[idx]
        if section_label == "input":
            example_no += 1
            has_expected = idx + 1 < len(sections) and sections[idx + 1][0] == "expected"
            if has_expected:
                input_text = "\n".join(content).strip()
                expected_text = "\n".join(sections[idx + 1][1]).strip()
                if input_text and expected_text:
                    examples.append(
                        Example(input_text=input_text, expected_text=expected_text)
                    )
                else:
                    warnings.append(f"Example {example_no}: empty input or expected — skipped.")
                idx += 2
                continue
            warnings.append(
                f"Example {example_no}: 'Input' without a following 'Expected' — skipped."
            )
        idx += 1
    return examples, warnings
