"""Parity tests for the Python retrieved-context parser — mirrors
web/src/features/proof/retrievedContext.test.ts so the receipt parses the bench input_text shape
identically to the cockpit."""

from orionfold.receipts.retrieved_context import parse_retrieved_context

# A faithful slice of the real Advisor bench input_text shape (same fixture as the TS test).
ADVISOR_INPUT = """Question: Did the MoE or the dense 32B win the serving-lane bakeoff?

Retrieved public context:
Source 1: article_hermes_serving_lane_on_spark
Label: Field Note: The Hermes Serving Lane
Class: field_note / book2_field_note
Title: The Hermes Serving Lane on a DGX Spark
Excerpt: The NIM Nemotron lane is the incumbent. MOE LANE Qwen3-30B-A3B 3B active of 30B.
Source 2: artifact_spark_hermes_profile
Label: Artifact: spark-hermes-profile
Class: artifact_harness / public_artifact_manifest
Title: Which local lane should drive your always-on Spark agent?
Excerpt: slug: spark-hermes-profile kind: harness class: agent-harness"""


def test_parses_the_advisor_shape_into_question_and_ordered_sources():
    r = parse_retrieved_context(ADVISOR_INPUT)
    assert r is not None
    assert r.question == "Did the MoE or the dense 32B win the serving-lane bakeoff?"
    assert len(r.sources) == 2
    s0 = r.sources[0]
    assert s0.id == "article_hermes_serving_lane_on_spark"
    assert s0.label == "Field Note: The Hermes Serving Lane"
    assert s0.class_ == "field_note / book2_field_note"
    assert s0.title == "The Hermes Serving Lane on a DGX Spark"
    assert s0.excerpt == "The NIM Nemotron lane is the incumbent. MOE LANE Qwen3-30B-A3B 3B active of 30B."
    assert r.sources[1].id == "artifact_spark_hermes_profile"
    assert r.sources[1].title == "Which local lane should drive your always-on Spark agent?"


def test_returns_none_for_free_form_text_without_the_marker():
    assert parse_retrieved_context("Just classify this ticket: my password reset failed.") is None
    assert parse_retrieved_context("") is None


def test_returns_none_for_a_bare_marker_with_no_source_blocks():
    # The marker alone, no Source records → not the structured shape → degrade to plain text.
    assert parse_retrieved_context("Question: x\n\nRetrieved public context:\n(nothing here)") is None


def test_multiline_excerpt_folds_continuation_lines():
    text = (
        "Question: q\n\nRetrieved public context:\n"
        "Source 1: doc_a\n"
        "Excerpt: line one\nline two\nline three"
    )
    r = parse_retrieved_context(text)
    assert r is not None
    assert r.sources[0].excerpt == "line one\nline two\nline three"


def test_question_label_is_stripped_case_insensitively():
    text = "question: lowercase label\n\nRetrieved public context:\nSource 1: doc_a"
    r = parse_retrieved_context(text)
    assert r is not None
    assert r.question == "lowercase label"
