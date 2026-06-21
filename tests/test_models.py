from orionfold.domain.models import (
    Example, Rubric, ResultRow, RunCostSummary,
)


def test_example_keypoints_default_empty():
    assert Example(input_text="i", expected_text="e").keypoints == []


def test_rubric_judge_fields_default_none():
    r = Rubric()
    assert r.kind == "similarity"
    assert r.judge_provider_id is None and r.judge_model is None


def test_rubric_accepts_new_kinds():
    assert Rubric(kind="keypoint").kind == "keypoint"
    assert Rubric(kind="judge", judge_provider_id="mock_judge").kind == "judge"


def test_result_row_judge_cost_defaults_zero():
    row = ResultRow(
        candidate_id="c", example_index=0, input_text="i", expected_text="e",
        output_text="o", score=1.0, passed=True, latency_ms=10,
        estimated_cost_usd=0.0, privacy="local",
    )
    assert row.judge_cost_usd == 0.0 and row.judge_latency_ms == 0


def test_run_cost_summary_shape():
    s = RunCostSummary(candidate_cost_usd=0.01, judge_cost_usd=0.002, total_cost_usd=0.012)
    assert s.total_cost_usd == 0.012
