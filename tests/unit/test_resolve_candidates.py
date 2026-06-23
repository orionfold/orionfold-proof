"""WS-A1: Models-mode task instruction. RunRequest.system_prompt sets one system prompt on every
selected candidate in model-compare runs, so classification/extraction tasks can be proven. When
absent it must leave candidates byte-identical → model-compare config_hashes stay unchanged (the
mock matrix `config_hash 467ddd96c9a5` invariant)."""

from __future__ import annotations

import pytest

from orionfold.domain.models import Dataset, Example, ProofBrief, PromptVariant, Rubric
from orionfold.proof.engine import config_hash
from orionfold.server.routes import RunRequest, _resolve_candidates


@pytest.fixture(autouse=True)
def _no_keys(tmp_path, monkeypatch):
    """Hermetic: tmp CWD (no .env.local) and cloud keys unset so only mocks resolve."""
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


_BRIEF = ProofBrief(task_name="Triage", decision_question="Which classifies best?")


def _req(**kw) -> RunRequest:
    return RunRequest(candidate_ids=["mock_good", "mock_bad"], brief=_BRIEF, **kw)


def test_instruction_set_on_every_candidate():
    cands = _resolve_candidates(_req(system_prompt="Reply with only the label."))
    assert [c.system_prompt for c in cands] == ["Reply with only the label."] * 2


def test_no_instruction_leaves_candidates_unchanged():
    # No system_prompt → byte-identical to bare build → model-compare hashes unchanged.
    base = _resolve_candidates(_req())
    assert all(c.system_prompt is None for c in base)


def test_blank_instruction_is_ignored():
    # Whitespace-only must NOT mint a system_prompt (would change config_hash spuriously).
    cands = _resolve_candidates(_req(system_prompt="   \n  "))
    assert all(c.system_prompt is None for c in cands)


def test_instruction_is_stripped():
    [c, _] = _resolve_candidates(_req(system_prompt="  Classify it.  "))
    assert c.system_prompt == "Classify it."


def test_config_hash_unchanged_when_absent_changes_when_set():
    ds = Dataset(id="d1", name="d1", description="", examples=[Example(input_text="a", expected_text="b")])
    rubric = Rubric(threshold=0.8)
    bare = _resolve_candidates(_req())
    instructed = _resolve_candidates(_req(system_prompt="Classify it."))
    assert config_hash(ds, instructed, rubric) != config_hash(ds, bare, rubric)


def test_prompt_variants_path_ignores_instruction():
    # When prompt_variants is set, the per-variant prompt wins; the Models-mode instruction is moot.
    req = RunRequest(
        candidate_ids=["mock_good"],
        brief=_BRIEF,
        system_prompt="Should be ignored.",
        prompt_variants=[
            PromptVariant(name="A", system_prompt="Prompt A"),
            PromptVariant(name="B", system_prompt="Prompt B"),
        ],
    )
    cands = _resolve_candidates(req)
    assert [c.system_prompt for c in cands] == ["Prompt A", "Prompt B"]
