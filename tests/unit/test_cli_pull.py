"""`orionfold pull` — thin CLI shell over pull_model + add_to_overlay (hf-own-models).

Hermetic: the streamed pull and the overlay are both stubbed/isolated, so no live Ollama daemon
and no real ~/.orionfold write. Pins the integrity rule: overlay is written only on success.
"""

from __future__ import annotations

from typer.testing import CliRunner

from orionfold.catalog.overlay import load_overlay
from orionfold.cli import app
from orionfold.providers import ollama_pull as pull_mod
from orionfold.providers.http import ProviderError
from orionfold.providers.ollama_pull import PullStatus

runner = CliRunner()
REPO = "hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF"


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))


def test_help_lists_pull():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "pull" in result.stdout


def test_pull_success_records_overlay(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)

    def fake_pull(host, repo_id):
        yield PullStatus(status="pulling manifest")
        yield PullStatus(status="downloading", completed=1_000_000_000, total=2_000_000_000)
        yield PullStatus(status="success")

    # The CLI imports pull_model from this module at call time, so patch it there.
    monkeypatch.setattr(pull_mod, "pull_model", fake_pull)

    result = runner.invoke(app, ["pull", REPO])
    assert result.exit_code == 0, result.stdout
    assert "selectable candidate" in result.stdout
    # The curated catalog entry was recorded (display name preserved), keyed by the repo id.
    overlay = load_overlay()
    assert [m.id for m in overlay] == [REPO]
    assert overlay[0].repo_id == REPO
    assert overlay[0].display_name == "Saul 7B Instruct (Legal)"  # from the curated catalog


def test_pull_failure_does_not_write_overlay(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)

    def fake_pull(host, repo_id):
        yield PullStatus(status="pulling manifest")
        raise ProviderError("ollama pull failed: file does not exist")

    monkeypatch.setattr(pull_mod, "pull_model", fake_pull)

    result = runner.invoke(app, ["pull", "hf.co/Orionfold/nope"])
    assert result.exit_code == 1
    assert "Pull failed" in result.output  # message goes to stderr
    assert load_overlay() == []  # success-gated: nothing recorded


def test_pulled_model_becomes_selectable_via_overlay(tmp_path, monkeypatch):
    # A non-curated HF pull is recorded and then surfaces in the selection panel.
    _isolate(monkeypatch, tmp_path)
    other = "hf.co/some-org/Custom-GGUF"

    def fake_pull(host, repo_id):
        yield PullStatus(status="success")

    monkeypatch.setattr(pull_mod, "pull_model", fake_pull)
    runner.invoke(app, ["pull", other])

    from orionfold.providers import selection as selection_mod

    # Daemon reports it pulled → it shows up available under the ollama group from the overlay.
    monkeypatch.setattr(selection_mod, "list_pulled", lambda host: {f"{other}:latest"})
    panel = selection_mod.selection_panel()
    ollama = next(g for g in panel.providers if g.provider_id == "ollama")
    row = next((m for m in ollama.models if m.model == other), None)
    assert row is not None and row.available is True
