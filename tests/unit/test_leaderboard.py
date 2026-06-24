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


def test_leaderboard_entry_carries_candidate_system_prompt():
    from orionfold.domain.models import Candidate, ResultRow
    from orionfold.proof.leaderboard import build_leaderboard

    cand = Candidate(id="ollama#terse", label="Terse", provider_id="ollama",
                     model="llama3.2", system_prompt="Be terse.")
    rows = [ResultRow(candidate_id="ollama#terse", example_index=0, input_text="a",
                      expected_text="b", output_text="b", score=1.0, passed=True,
                      latency_ms=10, estimated_cost_usd=0.0, privacy="local", error=None)]
    [entry] = build_leaderboard([cand], rows)
    assert entry.system_prompt == "Be terse."


def test_leaderboard_entry_system_prompt_none_for_model_compare():
    from orionfold.domain.models import Candidate, ResultRow
    from orionfold.proof.leaderboard import build_leaderboard

    cand = Candidate(id="mock_good", label="Mock", provider_id="mock_good")
    rows = [ResultRow(candidate_id="mock_good", example_index=0, input_text="a",
                      expected_text="b", output_text="b", score=1.0, passed=True,
                      latency_ms=10, estimated_cost_usd=0.0, privacy="local", error=None)]
    [entry] = build_leaderboard([cand], rows)
    assert entry.system_prompt is None


def test_cost_per_quality_is_cost_over_avg_score():
    # 0.10 total cost at avg_score 0.5 -> 0.20 dollars per quality point.
    cands = [_cand("c")]
    results = [
        _row("c", 0, score=0.5, passed=False, latency=100, cost=0.05),
        _row("c", 1, score=0.5, passed=True, latency=100, cost=0.05),
    ]
    [entry] = build_leaderboard(cands, results)
    assert entry.avg_score == 0.5
    assert entry.total_estimated_cost_usd == 0.10
    assert entry.cost_per_quality == 0.20


def test_cost_per_quality_is_none_when_avg_score_zero():
    # No quality to be efficient about -> undefined (renders "—"), never a divide-by-zero.
    cands = [_cand("z")]
    results = [_row("z", 0, score=0.0, passed=False, latency=0, error="boom")]
    [entry] = build_leaderboard(cands, results)
    assert entry.avg_score == 0.0
    assert entry.cost_per_quality is None


def test_cost_per_quality_is_zero_when_free():
    # Local/mock cost 0 with real quality -> 0.0 (renders "Free"), the local-first win.
    cands = [_cand("free")]
    results = [_row("free", 0, score=1.0, passed=True, latency=10, cost=0.0)]
    [entry] = build_leaderboard(cands, results)
    assert entry.cost_per_quality == 0.0


def test_cost_per_quality_does_not_change_ranking():
    # A cheap high-quality candidate still outranks an expensive low-quality one on pass_rate,
    # not on the new efficiency field.
    cands = [_cand("good"), _cand("bad")]
    results = [
        _row("good", 0, score=1.0, passed=True, latency=40, cost=0.50),
        _row("bad", 0, score=0.1, passed=False, latency=10, cost=0.00),
    ]
    entries = build_leaderboard(cands, results)
    assert entries[0].candidate_id == "good"  # pass_rate wins; cheaper "bad" does not jump it


def test_leaderboard_is_none_safe_for_unscored_rows():
    # Quick-compare rows have score=None/passed=None; aggregation must not crash and must
    # never crown an unscored candidate.
    cands = [_cand("a"), _cand("b")]
    results = [
        ResultRow(candidate_id="a", example_index=0, input_text="x", expected_text="",
                  output_text="out", score=None, passed=None, latency_ms=10,
                  estimated_cost_usd=0.0, privacy="local"),
        ResultRow(candidate_id="b", example_index=0, input_text="x", expected_text="",
                  output_text="out", score=None, passed=None, latency_ms=20,
                  estimated_cost_usd=0.0, privacy="local"),
    ]
    entries = build_leaderboard(cands, results)
    assert len(entries) == 2
    for e in entries:
        assert e.avg_score == 0.0
        assert e.pass_count == 0
        assert e.recommended is False


# ─── Throughput (tokens_per_second) — presentation-only generalization metric ─────────


def _row_tok(cid: str, idx: int, *, latency: int, out_tokens: int) -> ResultRow:
    return ResultRow(
        candidate_id=cid, example_index=idx, input_text="in", expected_text="exp",
        output_text="out", score=1.0, passed=True, latency_ms=latency,
        estimated_cost_usd=0.0, output_tokens=out_tokens, privacy="local",
    )


def test_tokens_per_second_is_token_weighted_rollup():
    # Σoutput_tokens / Σ(latency_s): (100 + 300) / ((1000 + 1000)/1000) = 400 / 2 = 200.
    rows = [_row_tok("a", 0, latency=1000, out_tokens=100),
            _row_tok("a", 1, latency=1000, out_tokens=300)]
    entry = build_leaderboard([_cand("a")], rows)[0]
    assert entry.tokens_per_second == 200.0


def test_tokens_per_second_none_when_no_latency():
    rows = [_row_tok("a", 0, latency=0, out_tokens=50)]
    entry = build_leaderboard([_cand("a")], rows)[0]
    assert entry.tokens_per_second is None


def test_tokens_per_second_does_not_change_ranking():
    # A faster-tok/s candidate with a worse pass rate must NOT outrank a slower one — throughput
    # is informational, latency stays the tiebreaker.
    fast_weak = [_row("fast", 0, score=0.0, passed=False, latency=10)]
    slow_strong = [_row("slow", 0, score=1.0, passed=True, latency=999)]
    board = build_leaderboard([_cand("fast"), _cand("slow")], fast_weak + slow_strong)
    assert board[0].candidate_id == "slow"  # higher pass rate wins regardless of tok/s
