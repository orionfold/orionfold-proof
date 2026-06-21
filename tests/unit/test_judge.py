import pytest
from orionfold.domain.models import Rubric
from orionfold.scoring.judge import (
    parse_score, MockJudge, LLMJudge, build_judge,
)


def test_parse_score_unit_interval():
    assert parse_score("0.73") == 0.73


def test_parse_score_rescales_percent():
    assert parse_score("Score: 85") == 0.85


def test_parse_score_clamps_and_handles_garbage():
    assert parse_score("1.4") == 1.0
    assert parse_score("no number here") is None


def test_parse_score_rescales_ten_scale():
    assert parse_score("7") == 0.7          # (2,10] -> /10


def test_parse_score_overshoot_clamps_not_rescaled():
    assert parse_score("1.4") == 1.0        # (1,2] is overshoot, clamps to 1.0 (NOT 0.14)


def test_parse_score_hundred_scale():
    assert parse_score("92") == 0.92        # >10 -> /100


def test_mock_judge_is_deterministic():
    a = MockJudge().score("the cat sat", "the cat sat")
    b = MockJudge().score("the cat sat", "the cat sat")
    assert a.score == b.score == 1.0
    assert a.cost_usd == 0.0001 and a.error is None
    assert a.latency_ms == 5


def test_build_judge_requires_provider_id():
    with pytest.raises(ValueError):
        build_judge(Rubric(kind="judge"))


def test_build_judge_mock():
    assert isinstance(build_judge(Rubric(kind="judge", judge_provider_id="mock_judge")), MockJudge)


class _FakeProvider:
    id = "fake"
    label = "Fake"
    privacy = "local"

    def __init__(self, text):
        self._text = text

    def generate(self, example, candidate):
        from orionfold.domain.models import ProviderResult
        return ProviderResult(output_text=self._text, latency_ms=12, estimated_cost_usd=0.003, privacy="local")


class _RaisingProvider:
    id = "raises"
    label = "Raises"
    privacy = "local"

    def generate(self, example, candidate):
        raise RuntimeError("network fail")


def test_llm_judge_parses_and_carries_cost():
    out = LLMJudge(_FakeProvider("0.9"), "m").score("expected", "output")
    assert out.score == 0.9 and out.cost_usd == 0.003 and out.latency_ms == 12 and out.error is None


def test_llm_judge_unparseable_is_error():
    out = LLMJudge(_FakeProvider("I think it is good"), "m").score("expected", "output")
    assert out.score == 0.0 and out.error is not None


def test_llm_judge_provider_error_is_error_outcome():
    out = LLMJudge(_RaisingProvider(), "m").score("expected", "output")
    assert out.score == 0.0 and out.error is not None
