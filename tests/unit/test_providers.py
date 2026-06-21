"""Mock providers must be deterministic, keyless, and error-safe across the boundary."""

from math import ceil

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, Example, ProviderResult
from orionfold.providers.base import Provider, redact_secrets, safe_generate
from orionfold.providers.mock import MockBadProvider, MockGoodProvider, _shape_for_prompt
from orionfold.providers.registry import available_candidates, get_provider


def _example(text: str) -> Example:
    return Example(input_text=text, expected_text="Revenue grew 20% on strong demand.")


def test_registry_exposes_the_mocks():
    ids = {c.provider_id for c in available_candidates()}
    assert {"mock_good", "mock_bad"} <= ids  # mocks are always offered (see test_registry)
    assert isinstance(get_provider("mock_good"), Provider)


def test_mock_good_returns_expected_text_and_is_deterministic():
    provider = MockGoodProvider()
    ex = _example("Quarterly report: revenue up 20%.")
    cand = Candidate(id="mock_good", label="g", provider_id="mock_good")
    first = provider.generate(ex, cand)
    second = provider.generate(ex, cand)
    assert first.output_text == ex.expected_text
    assert first.error is None
    assert first.privacy == "local"
    assert first.estimated_cost_usd == 0.0
    assert first == second  # fully deterministic


def test_mock_bad_eventually_errors_but_via_safe_generate_returns_result():
    provider = MockBadProvider()
    cand = Candidate(id="mock_bad", label="b", provider_id="mock_bad")
    results: list[ProviderResult] = [
        safe_generate(provider, _example(f"input number {i}"), cand) for i in range(40)
    ]
    # Every call yields a ProviderResult — no exception escaped the boundary.
    assert all(isinstance(r, ProviderResult) for r in results)
    # At least one deterministic error was produced (exercises the failure path).
    assert any(r.error is not None for r in results)
    # Erroring results carry the local privacy boundary and empty output.
    errored = [r for r in results if r.error]
    assert all(r.privacy == "local" and r.output_text == "" for r in errored)


def test_mock_bad_errors_on_at_least_one_bundled_example():
    # The happy-path e2e and the "always a failure case" guarantee depend on this invariant.
    provider = MockBadProvider()
    cand = Candidate(id="mock_bad", label="b", provider_id="mock_bad")
    dataset = load_dataset("investment-memo-summarization")
    results = [safe_generate(provider, ex, cand) for ex in dataset.examples]
    assert sum(1 for r in results if r.error is not None) >= 1


def test_safe_generate_redacts_secrets_from_error_messages():
    class LeakyProvider:
        id = "leaky"
        label = "leaky"
        privacy = "local"

        def generate(self, example: Example, candidate: Candidate) -> ProviderResult:
            raise RuntimeError("auth failed for key sk-abcdef123456 via Bearer tok_secret")

    result = safe_generate(
        LeakyProvider(),
        _example("x"),
        Candidate(id="leaky", label="leaky", provider_id="leaky"),
    )
    assert result.error is not None
    assert "sk-abcdef123456" not in result.error
    assert "[redacted]" in result.error


def test_redact_secrets_covers_common_credential_shapes():
    assert "sk-" not in redact_secrets("token sk-ABCDEF123456")
    assert "[redacted]" in redact_secrets("Authorization: Bearer abc.def.ghi")
    assert "[redacted]" in redact_secrets("api_key=supersecretvalue")


def _demo_ex0():
    # The bundled example whose expected_text carries 4 keypoints (22%, $48.2M, 118%, 79%).
    return load_dataset("investment-memo-summarization").examples[0]


def test_shape_verbatim_when_system_prompt_is_none():
    base = "Revenue grew 22% to $48.2M, with 118% net retention and 79% margins."
    # Identity (same object) — model-compare path must not even re-join whitespace.
    assert _shape_for_prompt(base, None) is base


def test_shape_verbatim_when_no_concise_cue():
    base = "Revenue grew 22% to $48.2M, with 118% net retention and 79% margins."
    assert _shape_for_prompt(base, "Be neutral and complete.") is base


def test_shape_strong_cue_truncates_to_40_percent():
    base = " ".join(f"w{i}" for i in range(10))  # 10 words
    out = _shape_for_prompt(base, "Answer in as few words as possible.")
    assert out == " ".join(f"w{i}" for i in range(ceil(0.4 * 10)))  # first 4 words


def test_shape_mild_cue_keeps_more_than_strong_cue():
    base = " ".join(f"w{i}" for i in range(10))
    mild = _shape_for_prompt(base, "Be concise.")
    strong = _shape_for_prompt(base, "Be terse.")
    assert len(mild.split()) > len(strong.split())


def test_shape_strongest_cue_wins_when_both_present():
    base = " ".join(f"w{i}" for i in range(10))
    both = _shape_for_prompt(base, "Be concise and terse.")  # mild + strong
    assert both == _shape_for_prompt(base, "terse")  # strong (0.4) dominates


def test_shape_keeps_at_least_one_word():
    assert _shape_for_prompt("solo", "as few words as possible") == "solo"


def test_mock_good_drops_keypoints_under_concise_prompt():
    provider = MockGoodProvider()
    ex = _demo_ex0()
    full = provider.generate(ex, Candidate(id="m", label="m", provider_id="mock_good"))
    concise = provider.generate(
        ex,
        Candidate(id="m#c", label="c", provider_id="mock_good",
                  system_prompt="Answer in as few words as possible."),
    )
    def present(kps, text):
        return sum(1 for k in kps if k in text)

    assert full.output_text == ex.expected_text  # baseline still perfect
    assert len(concise.output_text) < len(full.output_text)
    assert present(ex.keypoints, concise.output_text) < present(ex.keypoints, full.output_text)


def test_mock_good_prompt_shaping_is_deterministic():
    provider = MockGoodProvider()
    ex = _demo_ex0()
    cand = Candidate(id="m#c", label="c", provider_id="mock_good", system_prompt="Be terse.")
    assert provider.generate(ex, cand) == provider.generate(ex, cand)


def test_mock_bad_still_errors_regardless_of_system_prompt():
    provider = MockBadProvider()
    cand = Candidate(id="b#c", label="b", provider_id="mock_bad", system_prompt="Be terse.")
    results = [safe_generate(provider, _example(f"input number {i}"), cand) for i in range(40)]
    assert any(r.error is not None for r in results)
