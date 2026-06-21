"""build_leaderboard ranking + recommend-gate (the 'what to trust' verdict)."""

from __future__ import annotations

from orionfold.domain.models import Candidate, ResultRow
from orionfold.proof.leaderboard import build_leaderboard


def _cand(cid: str) -> Candidate:
    return Candidate(id=cid, label=cid, provider_id=cid)


def _row(cid: str, idx: int, *, score: float, passed: bool, latency: int,
         cost: float = 0.0, error: str | None = None) -> ResultRow:
    return ResultRow(
        candidate_id=cid,
        example_index=idx,
        input_text="in",
        expected_text="exp",
        output_text="" if error else "out",
        score=score,
        passed=passed,
        latency_ms=latency,
        estimated_cost_usd=cost,
        privacy="local",
        error=error,
    )


def test_all_errored_candidate_ranks_below_a_real_low_scorer():
    # 'erro' errors on every example (0ms/$0.00); 'real' runs but scores low.
    cands = [_cand("erro"), _cand("real")]
    results = [
        _row("erro", 0, score=0.0, passed=False, latency=0, error="boom"),
        _row("erro", 1, score=0.0, passed=False, latency=0, error="boom"),
        _row("real", 0, score=0.05, passed=False, latency=3000),
        _row("real", 1, score=0.05, passed=False, latency=3000),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "real"  # any real output beats a total error
    assert entries[1].candidate_id == "erro"


def test_real_zero_score_still_beats_total_error_on_tie():
    # Both 0/5 at avg_score 0.0; the errored one reports 0ms so the OLD tiebreak crowned it.
    cands = [_cand("erro"), _cand("real")]
    results = [
        _row("erro", 0, score=0.0, passed=False, latency=0, error="boom"),
        _row("real", 0, score=0.0, passed=False, latency=2500),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "real"


def test_no_candidate_recommended_when_top_passes_zero():
    cands = [_cand("a"), _cand("b")]
    results = [
        _row("a", 0, score=0.1, passed=False, latency=100),
        _row("b", 0, score=0.0, passed=False, latency=50, error="boom"),
    ]
    entries = build_leaderboard(cands, results)
    assert all(not e.recommended for e in entries)


def test_top_recommended_when_it_passes_at_least_one():
    cands = [_cand("good"), _cand("bad")]
    results = [
        _row("good", 0, score=1.0, passed=True, latency=40),
        _row("bad", 0, score=0.1, passed=False, latency=120),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "good"
    assert entries[0].recommended is True
    assert entries[1].recommended is False


def test_error_count_is_computed():
    cands = [_cand("mix")]
    results = [
        _row("mix", 0, score=0.0, passed=False, latency=0, error="boom"),
        _row("mix", 1, score=0.3, passed=False, latency=120),
    ]
    [entry] = build_leaderboard(cands, results)
    assert entry.error_count == 1
    assert entry.failure_count == 2
