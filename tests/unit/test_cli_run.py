"""`orionfold run` — headless end-to-end over keyless mock candidates."""

import json
from pathlib import Path

from typer.testing import CliRunner

from orionfold.cli import app

runner = CliRunner()
FIXTURE = Path(__file__).parent.parent / "fixtures" / "run_slice_dataset.jsonl"


def test_help_lists_run() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout


def test_run_emits_json_receipt(tmp_path, monkeypatch) -> None:
    # Isolate the DB so the test never writes the real ~/.orionfold/proof.db.
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    result = runner.invoke(
        app,
        [
            "run",
            "--dataset", str(FIXTURE),
            "--candidates", "mock_good,mock_bad",
            "--format", "json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    # stdout is a valid receipt JSON with both candidates.
    payload = json.loads(result.stdout)
    labels = json.dumps(payload)
    assert "mock_good" in labels and "mock_bad" in labels


def test_run_writes_to_out_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    out = tmp_path / "receipt.md"
    result = runner.invoke(
        app,
        [
            "run",
            "--dataset", str(FIXTURE),
            "--candidates", "mock_good,mock_bad",
            "--format", "markdown",
            "--out", str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    text = out.read_text()
    # A Markdown receipt has a heading and names a winner section.
    assert text.lstrip().startswith("#")


def test_run_unknown_candidate_errors_cleanly(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    result = runner.invoke(
        app,
        ["run", "--dataset", str(FIXTURE), "--candidates", "no_such_provider"],
    )
    assert result.exit_code != 0
    # The error is a clean message, not a traceback.
    assert "Traceback" not in result.stdout


def test_run_receipt_is_secret_free(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    result = runner.invoke(
        app,
        ["run", "--dataset", str(FIXTURE), "--candidates", "mock_good", "--format", "json"],
    )
    assert result.exit_code == 0, result.stdout
    # No API-key-shaped material in the output (mocks carry none, but assert the invariant).
    for needle in ("sk-", "api_key", "API_KEY", "Bearer "):
        assert needle not in result.stdout
