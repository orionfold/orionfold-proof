"""Unit tests for the derived corpus-source enrichment (the Python mirror of the FE
retrievedContext parser). Pure functions — no DB, no network."""

from __future__ import annotations

from orionfold.corpora.sources import (
    enrich_corpus_sources,
    parse_retrieved_sources,
)
from orionfold.domain.models import Example

ADVISOR_INPUT = """Question: Did the MoE or the dense 32B win?

Retrieved public context:
Source 1: article_hermes_serving_lane_on_spark
Label: Field Note: The Hermes Serving Lane
Class: field_note / book2_field_note
Title: The Hermes Serving Lane on a DGX Spark
Excerpt: The NIM Nemotron lane is the incumbent.
Source 2: artifact_spark_hermes_profile
Label: Artifact: spark-hermes-profile
Class: artifact_harness / public_artifact_manifest
Title: Which local lane should drive your always-on Spark agent?
Excerpt: slug: spark-hermes-profile kind: harness"""


def test_parse_retrieved_sources_advisor_shape() -> None:
    records = parse_retrieved_sources(ADVISOR_INPUT)
    assert len(records) == 2
    first = records[0]
    assert first["id"] == "article_hermes_serving_lane_on_spark"
    assert first["title"] == "The Hermes Serving Lane on a DGX Spark"
    assert first["class"] == "field_note / book2_field_note"
    assert first["label"] == "Field Note: The Hermes Serving Lane"
    assert first["excerpt"] == "The NIM Nemotron lane is the incumbent."
    assert records[1]["id"] == "artifact_spark_hermes_profile"


def test_parse_retrieved_sources_free_form_returns_empty() -> None:
    assert parse_retrieved_sources("Summarize the memo in three bullets.") == []
    assert parse_retrieved_sources("") == []


def test_parse_retrieved_sources_multiline_excerpt() -> None:
    records = parse_retrieved_sources(
        "Retrieved public context:\nSource 1: doc_a\nExcerpt: line one\nline two"
    )
    assert records[0]["excerpt"] == "line one\nline two"


def test_parse_retrieved_sources_missing_subfields() -> None:
    records = parse_retrieved_sources(
        "Retrieved public context:\nSource 1: doc_only\nSource 2: doc_titled\nTitle: A title"
    )
    assert records[0] == {"id": "doc_only"}
    assert records[1] == {"id": "doc_titled", "title": "A title"}


def _ex(input_text: str, *, expected: list[str] | None = None) -> Example:
    return Example(input_text=input_text, expected_text="", expected_citations=expected or [])


def test_enrich_dedupes_across_examples_and_counts_citations() -> None:
    # Two examples; one cites source A, both surface source A in context. The enriched source A
    # appears once, with cited_by == 1 (only one example names it in a citation gate).
    ex1 = _ex(ADVISOR_INPUT, expected=["article_hermes_serving_lane_on_spark"])
    ex2 = _ex(ADVISOR_INPUT, expected=[])
    sources = enrich_corpus_sources([ex1, ex2], source_ids=[])
    by_id = {s.id: s for s in sources}
    assert by_id["article_hermes_serving_lane_on_spark"].cited_by == 1
    assert by_id["artifact_spark_hermes_profile"].cited_by == 0
    # title/class/excerpt carried through on the deduped record
    assert by_id["article_hermes_serving_lane_on_spark"].title.startswith("The Hermes")
    assert by_id["article_hermes_serving_lane_on_spark"].klass == "field_note / book2_field_note"


def test_enrich_falls_back_to_manifest_ids_when_no_structure() -> None:
    # A corpus whose examples are free-form still lists its manifest source ids (bare, no enrichment),
    # so the browser shows the corpus is non-empty.
    sources = enrich_corpus_sources(
        [_ex("plain question with no context")], source_ids=["doc_x", "doc_y"]
    )
    ids = {s.id for s in sources}
    assert ids == {"doc_x", "doc_y"}
    assert all(s.title == "" for s in sources)


def test_enrich_accepted_source_ids_also_count_as_cited() -> None:
    ex = Example(
        input_text=ADVISOR_INPUT,
        expected_text="",
        accepted_source_ids=["artifact_spark_hermes_profile"],
    )
    sources = enrich_corpus_sources([ex], source_ids=[])
    by_id = {s.id: s for s in sources}
    assert by_id["artifact_spark_hermes_profile"].cited_by == 1
