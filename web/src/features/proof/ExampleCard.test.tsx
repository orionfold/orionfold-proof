import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import { ExampleCard } from "./ExampleCard";
import type { Example } from "../../lib/api";

function ex(over: Partial<Example> = {}): Example {
  return { input_text: "the input", expected_text: "the expected", keypoints: [], ...over };
}

test("bench example shows the behavior, required gates, and expected citations", () => {
  const { container } = render(
    <ExampleCard
      kind="bench"
      example={ex({
        expected_behavior: "answer",
        requires_citation: true,
        expected_citations: ["article_hermes_serving_lane_on_spark"],
      })}
    />,
  );
  const text = container.textContent ?? "";
  expect(text).toContain("Answer");
  expect(text).toContain("needs:");
  expect(text).toContain("cite");
  expect(text).toContain("article_hermes_serving_lane_on_spark");
});

test("a refuse bench row hides the reference answer (the model should decline, not answer)", () => {
  const { container } = render(
    <ExampleCard
      kind="bench"
      example={ex({ expected_behavior: "refuse", requires_refusal: true, expected_text: "should not show" })}
    />,
  );
  const text = container.textContent ?? "";
  expect(text).toContain("Refuse");
  expect(text).not.toContain("should not show");
});

test("keypoint example renders the expected facts as a checklist", () => {
  const { container } = render(
    <ExampleCard kind="keypoint" example={ex({ keypoints: ["22%", "$48.2M"] })} />,
  );
  const text = container.textContent ?? "";
  expect(text).toContain("Expected covers");
  expect(text).toContain("22%");
  expect(text).toContain("$48.2M");
});

test("an exact example shows the equality match rule", () => {
  const { container } = render(<ExampleCard kind="exact" example={ex({ expected_text: "billing" })} />);
  const text = container.textContent ?? "";
  expect(text).toContain("must equal");
  expect(text).toContain("billing");
});

test("a contains example shows the substring rule", () => {
  const { container } = render(<ExampleCard kind="contains" example={ex({ expected_text: "$42,500" })} />);
  expect(container.textContent ?? "").toContain("must contain");
});

test("a similarity example labels the expected as a reference, not 'Expected'", () => {
  const { container } = render(<ExampleCard kind="similarity" example={ex()} />);
  const text = container.textContent ?? "";
  expect(text).toContain("reference answer");
  expect(text).toContain("the expected");
});

test("a keypoint example with no keypoints degrades to a plain expected field", () => {
  const { container } = render(<ExampleCard kind="keypoint" example={ex({ keypoints: [] })} />);
  const text = container.textContent ?? "";
  expect(text).toContain("Expected");
  expect(text).toContain("the expected");
});
