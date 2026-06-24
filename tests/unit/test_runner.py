"""execute_run() — the pure core stitch shared by the route and the CLI."""

from orionfold.domain.models import Dataset, Example, ProofBrief, ProofReport
from orionfold.proof.runner import execute_run

_BRIEF = ProofBrief(task_name="Slice test", decision_question="Which mock wins?")
_DATASET = Dataset(
    id="t-runner",
    name="Runner test",
    examples=[
        Example(input_text="ping", expected_text="ping"),
        Example(input_text="hello", expected_text="hello"),
    ],
)


def test_execute_run_returns_report_over_mock_candidates() -> None:
    report = execute_run(
        dataset=_DATASET,
        candidate_ids=["mock_good", "mock_bad"],
        brief=_BRIEF,
    )

    assert isinstance(report, ProofReport)
    # One leaderboard entry per candidate.
    assert {e.candidate_id for e in report.leaderboard} == {"mock_good", "mock_bad"}
    # 2 candidates x 2 examples = 4 result rows.
    assert len(report.results) == 4
    # The run carries injected provenance.
    assert report.run.id.startswith("run_")
    assert report.run.created_at.endswith("Z")
    assert report.run.config_hash  # non-empty
    assert report.run.mode == "full"


def test_execute_run_resolves_default_rubric_when_none_given() -> None:
    # No keypoints on the examples → default_rubric_for picks "similarity".
    report = execute_run(
        dataset=_DATASET,
        candidate_ids=["mock_good"],
        brief=_BRIEF,
    )
    assert report.run.rubric.kind == "similarity"


def test_execute_run_honors_explicit_rubric() -> None:
    from orionfold.domain.models import Rubric

    report = execute_run(
        dataset=_DATASET,
        candidate_ids=["mock_good"],
        brief=_BRIEF,
        rubric=Rubric(kind="exact", threshold=1.0),
    )
    assert report.run.rubric.kind == "exact"


def test_execute_resolved_runs_from_prebuilt_objects() -> None:
    from orionfold.domain.models import Rubric
    from orionfold.providers.registry import build_candidates
    from orionfold.proof.runner import execute_resolved

    cands = build_candidates(["mock_good"])
    report = execute_resolved(
        dataset=_DATASET,
        candidates=cands,
        rubric=Rubric(kind="exact", threshold=1.0),
        brief=_BRIEF,
    )
    assert report.run.rubric.kind == "exact"
    assert report.run.id.startswith("run_")


def test_proof_package_public_surface() -> None:
    import orionfold.proof as proof

    assert "execute_run" in proof.__all__
    assert "execute_resolved" in proof.__all__
    # The engine primitives are part of the curated public surface too.
    for name in ("run_proof", "run_matrix", "iter_matrix", "config_hash", "build_cost_summary"):
        assert name in proof.__all__, name
        assert hasattr(proof, name), name
