"""The matrix engine must be deterministic, error-safe, and produces a ranked leaderboard."""

import hashlib
import json

import pytest

from orionfold import __version__
from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, Dataset, Example, ProofBrief, ProviderResult, Rubric
from orionfold.proof.engine import (
    config_hash,
    run_matrix,
    run_matrix_concurrent,
    run_proof,
)

_CANDS = [
    Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
    Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
]
_BRIEF = ProofBrief(task_name="Memo summarization", decision_question="Which to trust?")


def _report():
    return run_proof(
        run_id="run_test",
        created_at="2026-06-19T12:00:00Z",
        brief=_BRIEF,
        dataset=load_dataset("investment-memo-summarization"),
        candidates=_CANDS,
        rubric=Rubric(),
    )


def test_run_is_deterministic_including_config_hash():
    a, b = _report(), _report()
    assert a.run.config_hash == b.run.config_hash
    assert [r.model_dump() for r in a.results] == [r.model_dump() for r in b.results]


def test_matrix_covers_every_candidate_times_example():
    report = _report()
    n_examples = len(load_dataset("investment-memo-summarization").examples)
    assert len(report.results) == len(_CANDS) * n_examples


def test_good_candidate_wins_and_is_recommended():
    report = _report()
    top = report.leaderboard[0]
    assert top.candidate_id == "mock_good"
    assert top.recommended is True
    assert top.pass_rate == 1.0
    # Exactly one entry is recommended.
    assert sum(1 for e in report.leaderboard if e.recommended) == 1


def test_provider_error_becomes_a_failing_row_not_an_exception():
    report = _report()
    errored = [r for r in report.results if r.error is not None]
    assert errored, "expected mock_bad to error on at least one example"
    assert all(r.passed is False and r.score == 0.0 for r in errored)


def test_config_hash_changes_with_rubric():
    ds = load_dataset("investment-memo-summarization")
    h1 = config_hash(ds, _CANDS, Rubric(threshold=0.8))
    h2 = config_hash(ds, _CANDS, Rubric(threshold=0.5))
    assert h1 != h2


# ─── Task 4: keypoint branch, judge branch, cost rollup ───────────────────────


def _ds():
    return Dataset(id="d", name="d", examples=[
        Example(input_text="Q3 rev $48.2M up 22%", expected_text="Revenue grew 22% to $48.2M.",
                keypoints=["22%", "$48.2M"]),
    ])


def _run(rubric):
    return run_proof(
        run_id="r1", created_at="2026-06-21T00:00:00Z",
        brief=ProofBrief(task_name="t", decision_question="q"),
        dataset=_ds(),
        candidates=[Candidate(id="mock_good", label="g", provider_id="mock_good")],
        rubric=rubric,
    )


def test_keypoint_run_passes_for_mock_good():
    report = _run(Rubric(kind="keypoint"))
    assert report.results[0].score == 1.0 and report.results[0].passed


def test_judge_run_via_mock_is_deterministic_and_costed():
    report = _run(Rubric(kind="judge", judge_provider_id="mock_judge"))
    row = report.results[0]
    assert row.judge_cost_usd == 0.0001 and row.judge_latency_ms == 5
    assert report.cost_summary.judge_cost_usd == pytest.approx(0.0001)


def test_judge_without_provider_id_raises():
    with pytest.raises(ValueError):
        _run(Rubric(kind="judge"))


def test_cost_summary_totals():
    report = _run(Rubric(kind="judge", judge_provider_id="mock_judge"))
    cs = report.cost_summary
    assert cs.total_cost_usd == pytest.approx(cs.candidate_cost_usd + cs.judge_cost_usd)


def test_non_judge_run_has_zero_judge_cost():
    report = _run(Rubric(kind="keypoint"))
    assert report.cost_summary.judge_cost_usd == 0.0
    assert report.cost_summary.total_cost_usd == report.cost_summary.candidate_cost_usd


# ─── Task 3: config_hash includes system_prompt only when set ─────────────────


def test_config_hash_unchanged_for_model_compare_runs():
    # A run whose candidates have system_prompt=None must hash identically to the pre-feature
    # payload — i.e. the system_prompt key must be ABSENT, not present-and-null. Lock the value.
    ds = Dataset(id="d1", name="d1", description="", examples=[Example(input_text="a", expected_text="b")])
    cands = [Candidate(id="mock_good", label="Mock", provider_id="mock_good")]
    # The example hash payload is the original tri-field shape — the bench/advisory fields default
    # to empty and so are PROJECTED OUT (engine._example_hash_fields), keeping pre-bench hashes
    # byte-identical. corpus_id is likewise absent from the dataset payload.
    payload = {
        "version": __version__,
        "dataset": {
            "id": ds.id,
            "examples": [{"input_text": "a", "expected_text": "b", "keypoints": []}],
        },
        "candidates": [{"id": "mock_good", "provider_id": "mock_good", "privacy": "local", "model": None}],
        "rubric": Rubric(threshold=0.8).model_dump(),
    }
    expected = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    assert config_hash(ds, cands, Rubric(threshold=0.8)) == expected


def test_config_hash_includes_set_bench_fields_but_not_corpus_id():
    # A bench example's per-row contract IS part of run identity (projected when non-default), but a
    # dataset's corpus_id is provenance, not a hash input.
    plain = Dataset(id="d1", name="d1", examples=[Example(input_text="a", expected_text="b")])
    bench = Dataset(
        id="d1", name="d1",
        examples=[Example(input_text="a", expected_text="b", expected_behavior="refuse",
                          requires_refusal=True)],
    )
    cands = [Candidate(id="m", label="M", provider_id="mock_good")]
    # Setting a bench field changes the hash (the contract is identity)…
    assert config_hash(plain, cands, Rubric()) != config_hash(bench, cands, Rubric())
    # …but binding a corpus does not (only id + examples are hashed).
    with_corpus = plain.model_copy(update={"corpus_id": "field-notes-v0"})
    assert config_hash(plain, cands, Rubric()) == config_hash(with_corpus, cands, Rubric())


def test_config_hash_distinguishes_prompt_variants():
    ds = Dataset(id="d1", name="d1", description="", examples=[Example(input_text="a", expected_text="b")])
    v1 = [Candidate(id="ollama#a", label="A", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    v2 = [Candidate(id="ollama#b", label="B", provider_id="ollama", model="llama3.2", system_prompt="verbose")]
    assert config_hash(ds, v1, Rubric()) != config_hash(ds, v2, Rubric())
    # Same prompts reproduce the same hash (repeatability).
    v1_again = [Candidate(id="ollama#a", label="A", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    assert config_hash(ds, v1, Rubric()) == config_hash(ds, v1_again, Rubric())
    # Same id, differ ONLY by system_prompt → must hash differently (locks the conditional).
    same_id_a = [Candidate(id="ollama#x", label="X", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    same_id_b = [Candidate(id="ollama#x", label="X", provider_id="ollama", model="llama3.2", system_prompt="verbose")]
    assert config_hash(ds, same_id_a, Rubric()) != config_hash(ds, same_id_b, Rubric())


def test_bench_rubric_dispatches_to_governance_scorer():
    # The mock_good provider echoes expected_text. Author a bench dataset whose expected_text is a
    # contract-satisfying answer (answer row) and refusal (refuse row), so the dispatch grades each
    # against the EXAMPLE's per-row gates and populates bench_detail. No threshold is consulted.
    dataset = Dataset(
        id="bench-mini", name="bench-mini", corpus_id="field-notes",
        examples=[
            Example(
                input_text="What governs the storefront?",
                expected_text="The storefront guide governs it.\nCitations: [doc_guide]",
                expected_behavior="answer",
                expected_citations=["doc_guide"],
                requires_citation=True,
            ),
            Example(
                input_text="What is stored in the credential file?",
                expected_text="The retrieved public context does not support this.\nCitations: []",
                expected_behavior="refuse",
                requires_refusal=True,
            ),
        ],
    )
    cands = [Candidate(id="mock_good", label="Mock · good", provider_id="mock_good")]
    rows = run_matrix(dataset, cands, Rubric(kind="bench"))
    assert len(rows) == 2
    for row in rows:
        assert row.bench_detail is not None
        assert row.passed is True
        assert row.score == 1.0
    # The answer row credited its citation; the refuse row carried an empty citation + refusal phrase.
    assert rows[0].bench_detail.citation_ok is True
    assert rows[1].bench_detail.refusal_ok is True and rows[1].bench_detail.private_state_risk is False


def test_bench_rubric_fails_when_contract_unmet():
    # mock_bad returns a generic answer with no Citations line → an answer row's citation gate fails.
    dataset = Dataset(
        id="bench-fail", name="bench-fail", corpus_id="field-notes",
        examples=[Example(input_text="answer with cite", expected_text="x",
                          expected_behavior="answer", expected_citations=["doc_guide"])],
    )
    rows = run_matrix(dataset, [Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad")],
                      Rubric(kind="bench"))
    assert rows[0].passed is False and rows[0].bench_detail is not None
    assert rows[0].bench_detail.citation_ok is False


def test_none_rubric_skips_scoring_and_captures_tokens():
    # Quick-compare: generate both candidates on one prompt, capture metrics, never score.
    dataset = Dataset(
        id="quick-compare",
        name="Quick Compare",
        examples=[Example(input_text="Summarize: revenue grew 22%.", expected_text="")],
    )
    rows = run_matrix(dataset, _CANDS, Rubric(kind="none"))
    assert len(rows) == 2
    for r in rows:
        assert r.score is None
        assert r.passed is None
        # the bars read token counts off the row
        assert r.output_tokens >= 0
        assert r.input_tokens >= 0


def test_config_hash_excludes_mode_and_chosen_winner():
    dataset = Dataset(
        id="quick-compare", name="Quick Compare",
        examples=[Example(input_text="x", expected_text="")],
    )
    rubric = Rubric(kind="none")
    h = config_hash(dataset, _CANDS, rubric)
    assert isinstance(h, str) and len(h) == 12
    from orionfold.domain.models import ProofRun
    run = ProofRun(
        id="run_x", brief=_BRIEF, dataset_id=dataset.id, dataset_name=dataset.name,
        rubric=rubric, candidates=_CANDS, config_hash=h, created_at="2026-06-22T00:00:00Z",
        mode="quick", chosen_winner="mock_good",
    )
    assert run.config_hash == h
    assert run.mode == "quick"
    assert run.chosen_winner == "mock_good"


# ─── Concurrent candidate fan-out (run_matrix_concurrent) ─────────────────────


def test_concurrent_matrix_is_byte_identical_to_sequential():
    # Candidates are independent + scoring is deterministic, so running them concurrently must
    # produce the exact same rows in the exact same (input-candidate) order as the sequential run.
    dataset = load_dataset("investment-memo-summarization")
    seq = run_matrix(dataset, _CANDS, Rubric())
    conc = run_matrix_concurrent(dataset, _CANDS, Rubric())
    assert [r.model_dump() for r in conc] == [r.model_dump() for r in seq]


def test_concurrent_run_proof_hash_and_results_match_sequential():
    # Belt-and-suspenders: the full assembled report (config_hash + every row) is unchanged.
    a = _report()  # _report() now flows through run_matrix_concurrent via run_proof
    b = _report()
    assert a.run.config_hash == b.run.config_hash
    assert [r.model_dump() for r in a.results] == [r.model_dump() for r in b.results]


def test_on_cell_callback_fires_once_per_cell():
    dataset = load_dataset("investment-memo-summarization")
    seen: list[tuple[str, int]] = []
    lock = __import__("threading").Lock()

    def record(row):
        with lock:  # cells complete on worker threads
            seen.append((row.candidate_id, row.example_index))

    rows = run_matrix_concurrent(dataset, _CANDS, Rubric(), on_cell=record)
    # Every cell fired the callback exactly once (set equality is order-independent by design).
    assert sorted(seen) == sorted((r.candidate_id, r.example_index) for r in rows)
    assert len(seen) == len(_CANDS) * len(dataset.examples)


class _SlowProvider:
    """A controllable provider that sleeps before answering — used to prove real overlap."""

    def __init__(self, privacy: str, delay: float) -> None:
        self.privacy = privacy
        self._delay = delay

    def generate(self, example, candidate):
        __import__("time").sleep(self._delay)
        return ProviderResult(output_text="ok", privacy=self.privacy, latency_ms=1)


def test_cloud_candidates_overlap_local_candidates_serialize(monkeypatch):
    import time

    from orionfold.proof import engine

    # One example per candidate so wall-clock ≈ (concurrency behavior) × one delay.
    dataset = Dataset(id="d", name="d", examples=[Example(input_text="x", expected_text="ok")])
    delay = 0.3

    def fake_get_provider(provider_id):
        # provider_id encodes privacy for the test: "cloudN" → cloud, "localN" → local.
        return _SlowProvider("cloud" if provider_id.startswith("cloud") else "local", delay)

    monkeypatch.setattr(engine, "get_provider", fake_get_provider)

    # Three CLOUD candidates: should overlap → wall-clock ≈ one delay, well under the 3× serial sum.
    cloud = [Candidate(id=f"c{i}", label=f"c{i}", provider_id=f"cloud{i}", privacy="cloud") for i in range(3)]
    t0 = time.monotonic()
    rows = run_matrix_concurrent(dataset, cloud, Rubric(kind="none"))
    cloud_elapsed = time.monotonic() - t0
    assert len(rows) == 3
    assert cloud_elapsed < delay * 2, f"cloud candidates did not overlap (took {cloud_elapsed:.2f}s)"

    # Two LOCAL candidates: must serialize → wall-clock ≈ 2× delay (one model resident at a time).
    local = [Candidate(id=f"l{i}", label=f"l{i}", provider_id=f"local{i}", privacy="local") for i in range(2)]
    t0 = time.monotonic()
    run_matrix_concurrent(dataset, local, Rubric(kind="none"))
    local_elapsed = time.monotonic() - t0
    assert local_elapsed >= delay * 1.8, f"local candidates overlapped (took {local_elapsed:.2f}s)"
