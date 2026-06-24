"""`orionfold dataset`, `runs`, and `track-record` — headless over keyless mock candidates.

Every test isolates the DB via ``ORIONFOLD_DB`` (matching ``test_cli_run.py``) so it never
touches the real ~/.orionfold/proof.db.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from orionfold.cli import app

runner = CliRunner()
FIXTURE = Path(__file__).parent.parent / "fixtures" / "run_slice_dataset.jsonl"


@pytest.fixture()
def db(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "test.db"
    monkeypatch.setenv("ORIONFOLD_DB", str(path))
    return path


def _import(name: str = "Triage") -> None:
    result = runner.invoke(
        app, ["dataset", "import", str(FIXTURE), "--name", name, "--check-hint", "exact"]
    )
    assert result.exit_code == 0, result.stdout


def _run(dataset_id: str, candidates: str = "mock_good,mock_bad", rubric: str = "exact") -> str:
    """Run a proof over a stored dataset by re-using the file path, return the run id."""
    # The CLI `run` command takes a file path, not a stored id; we feed the same fixture so
    # the run lands a report in the isolated DB.
    result = runner.invoke(
        app,
        ["run", "--dataset", str(FIXTURE), "--candidates", candidates, "--rubric", rubric,
         "--format", "json"],
    )
    assert result.exit_code == 0, result.stdout
    # The JSON receipt is the flattened export structure (run_id at top level), identical to
    # what `runs show --format json` emits.
    return json.loads(result.stdout)["run_id"]


# ── dataset ─────────────────────────────────────────────────────────────────────────────────


def test_dataset_import_then_list(db) -> None:
    result = runner.invoke(
        app, ["dataset", "import", str(FIXTURE), "--name", "My Set", "--check-hint", "exact"]
    )
    assert result.exit_code == 0, result.stdout
    assert "Imported 'My Set'" in result.stdout
    assert "examples" in result.stdout

    listed = runner.invoke(app, ["dataset", "list"])
    assert listed.exit_code == 0, listed.stdout
    assert "My Set" in listed.stdout
    assert "exact" in listed.stdout


def test_dataset_list_empty(db) -> None:
    result = runner.invoke(app, ["dataset", "list"])
    assert result.exit_code == 0
    assert "No datasets yet" in result.stdout


def test_dataset_import_duplicate_name_errors_cleanly(db) -> None:
    _import("Dup")
    result = runner.invoke(app, ["dataset", "import", str(FIXTURE), "--name", "Dup"])
    assert result.exit_code != 0
    assert "already exists" in result.output
    assert "Traceback" not in result.output


def test_dataset_import_unsupported_extension(db, tmp_path) -> None:
    bad = tmp_path / "data.txt"
    bad.write_text("nope")
    result = runner.invoke(app, ["dataset", "import", str(bad)])
    assert result.exit_code == 2
    assert "Unsupported" in result.output


# ── runs ────────────────────────────────────────────────────────────────────────────────────


def test_runs_list_empty(db) -> None:
    result = runner.invoke(app, ["runs", "list"])
    assert result.exit_code == 0
    assert "No runs yet" in result.stdout


def test_runs_list_after_a_run(db) -> None:
    run_id = _run("triage")
    result = runner.invoke(app, ["runs", "list"])
    assert result.exit_code == 0, result.stdout
    assert run_id in result.stdout
    assert "exact" in result.stdout


def test_runs_show_verdict_summary(db) -> None:
    run_id = _run("triage")
    result = runner.invoke(app, ["runs", "show", run_id])
    assert result.exit_code == 0, result.stdout
    assert run_id in result.stdout
    assert "CANDIDATE" in result.stdout
    assert "Run cost:" in result.stdout
    # mock_good echoes the expected exactly → it is the recommended (★) candidate.
    assert "★" in result.stdout


def test_runs_show_format_json_matches_run(db) -> None:
    run_id = _run("triage")
    shown = runner.invoke(app, ["runs", "show", run_id, "--format", "json"])
    assert shown.exit_code == 0, shown.stdout
    payload = json.loads(shown.stdout)
    assert payload["run_id"] == run_id

    # Lock the "one renderer, one protected artifact" invariant: `runs show --format json`
    # must be byte-identical to the canonical receipt renderer applied to the stored report
    # (typer.echo appends the trailing newline). Both CLI paths share _FORMAT_RENDERERS, so
    # this can only diverge if someone forks the renderer — which this assert forbids.
    from orionfold.receipts import export
    from orionfold.storage.db import connect, default_db_path
    from orionfold.storage.repository import get_report

    conn = connect(default_db_path())
    try:
        stored = get_report(conn, run_id)
    finally:
        conn.close()
    assert stored is not None
    assert shown.stdout == export.to_json(stored) + "\n"


def test_runs_show_unknown_id_errors_cleanly(db) -> None:
    result = runner.invoke(app, ["runs", "show", "run_does_not_exist"])
    assert result.exit_code == 1
    assert "Unknown run" in result.output
    assert "Traceback" not in result.output


# ── track-record ──────────────────────────────────────────────────────────────────────────


def test_track_record_empty(db) -> None:
    result = runner.invoke(app, ["track-record"])
    assert result.exit_code == 0
    assert "No comparable runs" in result.stdout


def test_track_record_after_runs(db) -> None:
    _run("triage")
    _run("triage")  # second run over the same dataset+rubric → one group, runs=2
    result = runner.invoke(app, ["track-record"])
    assert result.exit_code == 0, result.stdout
    assert "exact" in result.stdout
    assert "CANDIDATE" in result.stdout
    assert "RUNS" in result.stdout
    # mock_good appears in the standings.
    assert "mock" in result.stdout.lower()


def test_track_record_dataset_filter_no_match(db) -> None:
    _run("triage")
    result = runner.invoke(app, ["track-record", "--dataset", "nonexistent"])
    assert result.exit_code == 0
    assert "No comparable runs" in result.stdout


def test_workflow_output_is_secret_free(db) -> None:
    _import()
    _run("triage")
    for argv in (["dataset", "list"], ["runs", "list"], ["track-record"]):
        result = runner.invoke(app, argv)
        for needle in ("sk-", "api_key", "API_KEY", "Bearer "):
            assert needle not in result.stdout
