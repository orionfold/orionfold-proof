import { describe, it, expect } from "vitest";

import { parseRetrievedContext } from "./retrievedContext";

// A faithful slice of the real Advisor bench input_text shape (see
// src/orionfold/data/datasets/advisor_curveball_v0_2.json): a Question, then a
// "Retrieved public context:" block of repeating Source N: / Label: / Class: / Title: / Excerpt:.
const ADVISOR_INPUT = `Question: Did the MoE or the dense 32B win the serving-lane bakeoff?

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
Excerpt: slug: spark-hermes-profile kind: harness class: agent-harness`;

describe("parseRetrievedContext", () => {
  it("parses the Advisor shape into a question and ordered source records", () => {
    const r = parseRetrievedContext(ADVISOR_INPUT);
    expect(r).not.toBeNull();
    expect(r!.question).toBe(
      "Did the MoE or the dense 32B win the serving-lane bakeoff?",
    );
    expect(r!.sources).toHaveLength(2);
    expect(r!.sources[0]).toEqual({
      id: "article_hermes_serving_lane_on_spark",
      label: "Field Note: The Hermes Serving Lane",
      class: "field_note / book2_field_note",
      title: "The Hermes Serving Lane on a DGX Spark",
      excerpt:
        "The NIM Nemotron lane is the incumbent. MOE LANE Qwen3-30B-A3B 3B active of 30B.",
    });
    expect(r!.sources[1].id).toBe("artifact_spark_hermes_profile");
    expect(r!.sources[1].title).toBe(
      "Which local lane should drive your always-on Spark agent?",
    );
  });

  it("preserves the source ids that the cite-gate cross-links against", () => {
    // The whole point of the smart parse: the parsed source ids ARE the ids the
    // bench row expects cited, so the UI can mark "this is the source you must cite".
    const r = parseRetrievedContext(ADVISOR_INPUT);
    const ids = r!.sources.map((s) => s.id);
    expect(ids).toContain("article_hermes_serving_lane_on_spark");
  });

  it("returns null for a free-form input with no retrieved-context structure", () => {
    expect(
      parseRetrievedContext("Summarize the attached memo in three bullet points."),
    ).toBeNull();
  });

  it("returns null when the Source blocks are absent even if a question exists", () => {
    expect(
      parseRetrievedContext("Question: what is 2 + 2?\n\nRetrieved public context:\n(none)"),
    ).toBeNull();
  });

  it("tolerates a source block missing some sub-fields", () => {
    const input = `Question: q

Retrieved public context:
Source 1: doc_only_id
Source 2: doc_with_title
Title: A title but no class or excerpt`;
    const r = parseRetrievedContext(input);
    expect(r).not.toBeNull();
    expect(r!.sources).toHaveLength(2);
    expect(r!.sources[0]).toEqual({ id: "doc_only_id" });
    expect(r!.sources[1]).toEqual({ id: "doc_with_title", title: "A title but no class or excerpt" });
  });

  it("handles a question that has no explicit 'Question:' label", () => {
    // Some sets may lead straight into context. The question is then whatever precedes it.
    const input = `Pick the cheaper lane.

Retrieved public context:
Source 1: doc_a
Title: Doc A`;
    const r = parseRetrievedContext(input);
    expect(r).not.toBeNull();
    expect(r!.question).toBe("Pick the cheaper lane.");
    expect(r!.sources[0].id).toBe("doc_a");
  });

  it("returns null on empty / whitespace input", () => {
    expect(parseRetrievedContext("")).toBeNull();
    expect(parseRetrievedContext("   \n  ")).toBeNull();
  });

  it("keeps a multi-line excerpt as a single trimmed block", () => {
    const input = `Question: q

Retrieved public context:
Source 1: doc_a
Excerpt: line one
line two
line three`;
    const r = parseRetrievedContext(input);
    expect(r!.sources[0].excerpt).toBe("line one\nline two\nline three");
  });
});
