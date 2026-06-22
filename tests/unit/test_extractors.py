"""Document extractors turn .xlsx/.docx/.pdf uploads into normalized import text that the
existing importers parse. Pure and keyless; the pdf text seam is monkeypatched so no binary
fixture is needed."""

import io

import pytest
from openpyxl import Workbook

from orionfold.data.extractors import (
    DocExtractError,
    doc_format_for,
    extract_document,
    normalize_pairs_to_markdown,
)
from orionfold.data.importers import parse_dataset


def _xlsx_bytes(rows: list[tuple[str, str]], header=("input", "expected")) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(list(header))
    for a, b in rows:
        ws.append([a, b])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_doc_format_for_maps_extensions():
    assert doc_format_for("cases.xlsx") == "xlsx"
    assert doc_format_for("memo.DOCX") == "docx"
    assert doc_format_for("report.pdf") == "pdf"
    assert doc_format_for("notes.txt") is None


def test_extract_xlsx_yields_csv_text_that_parses():
    data = _xlsx_bytes([("What is 2+2?", "4"), ("Capital of France?", "Paris")])
    result = extract_document(data, "xlsx")
    assert result.format == "csv"
    parsed = parse_dataset(result.text, result.format)
    assert parsed.count == 2
    assert parsed.examples[0].input_text == "What is 2+2?"
    assert parsed.examples[1].expected_text == "Paris"


def test_extract_xlsx_missing_columns_warns():
    data = _xlsx_bytes([("a", "b")], header=("question", "answer"))
    result = extract_document(data, "xlsx")
    assert result.warnings  # surfaced, not raised
    assert "input" in result.warnings[0].lower() or "expected" in result.warnings[0].lower()


def test_extract_docx_table_yields_markdown_pairs():
    import docx

    doc = docx.Document()
    table = doc.add_table(rows=0, cols=2)
    header = table.add_row().cells
    header[0].text = "input"
    header[1].text = "expected"
    row = table.add_row().cells
    row[0].text = "Define proof."
    row[1].text = "Evidence you can rerun."
    buf = io.BytesIO()
    doc.save(buf)
    result = extract_document(buf.getvalue(), "docx")
    assert result.format == "markdown"
    parsed = parse_dataset(result.text, result.format)
    assert parsed.count == 1
    assert parsed.examples[0].input_text == "Define proof."


def test_extract_pdf_uses_text_seam_and_warns_lossy(monkeypatch):
    monkeypatch.setattr(
        "orionfold.data.extractors._pdf_text",
        lambda data: "Input\nWhat is proof?\nExpected\nA repeatable receipt.\n",
    )
    result = extract_document(b"%PDF-fake", "pdf")
    assert result.format == "markdown"
    assert any("lossy" in w.lower() or "review" in w.lower() for w in result.warnings)
    parsed = parse_dataset(result.text, result.format)
    assert parsed.count == 1


def test_normalize_pairs_to_markdown_promotes_bare_labels():
    text, _warnings = normalize_pairs_to_markdown("Input\nQ1\nExpected\nA1\n")
    assert "## Input" in text and "## Expected" in text


def test_extract_unknown_format_raises():
    with pytest.raises(DocExtractError):
        extract_document(b"not a workbook", "xlsx")
