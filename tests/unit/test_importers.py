import pytest

from orionfold.data.importers import DatasetParseError, parse_dataset


def test_jsonl_parses_both_key_spellings():
    text = (
        '{"input": "a", "expected": "b"}\n'
        '{"input_text": "c", "expected_text": "d"}\n'
    )
    r = parse_dataset(text, "jsonl")
    assert r.count == 2
    assert r.examples[0].input_text == "a" and r.examples[0].expected_text == "b"
    assert r.examples[1].input_text == "c" and r.examples[1].expected_text == "d"
    assert r.warnings == []


def test_jsonl_skips_malformed_and_blank_lines_with_warnings():
    text = '{"input": "a", "expected": "b"}\n\nnot json\n{"input": "x"}\n'
    r = parse_dataset(text, "jsonl")
    assert r.count == 1
    assert any("Line 3" in w for w in r.warnings)  # not json
    assert any("Line 4" in w for w in r.warnings)  # missing expected


def test_csv_case_insensitive_headers():
    text = "Input,Expected\nhello,world\n"
    r = parse_dataset(text, "csv")
    assert r.count == 1
    assert r.examples[0].input_text == "hello"
    assert r.examples[0].expected_text == "world"


def test_csv_missing_columns_yields_no_examples_and_errors():
    with pytest.raises(DatasetParseError):
        parse_dataset("foo,bar\n1,2\n", "csv")


def test_csv_skips_rows_missing_a_value():
    text = "input,expected\na,b\n,d\ne,\n"
    r = parse_dataset(text, "csv")
    assert r.count == 1
    assert len(r.warnings) == 2


def test_markdown_heading_pairs_with_multiline_prose():
    text = (
        "## Input\nline one\nline two\n\n## Expected\nsummary\n\n---\n\n"
        "## Input\nsecond\n\n## Expected\nsecond out\n"
    )
    r = parse_dataset(text, "markdown")
    assert r.count == 2
    assert r.examples[0].input_text == "line one\nline two"
    assert r.examples[0].expected_text == "summary"
    assert r.examples[1].input_text == "second"


def test_markdown_input_without_expected_warns_and_skips():
    text = "## Input\nonly input\n\n---\n\n## Input\ngood\n## Expected\nok\n"
    r = parse_dataset(text, "markdown")
    assert r.count == 1
    assert any("Example 1" in w for w in r.warnings)


def test_markdown_headings_are_case_and_level_insensitive():
    text = "# input\nx\n### EXPECTED\ny\n"
    r = parse_dataset(text, "markdown")
    assert r.count == 1


def test_whitespace_only_fields_are_skipped():
    r_jsonl = parse_dataset('{"input": "  ", "expected": "ok"}\n{"input":"a","expected":"b"}\n', "jsonl")
    assert r_jsonl.count == 1


def test_zero_valid_examples_raises():
    with pytest.raises(DatasetParseError):
        parse_dataset("\n\n", "jsonl")
