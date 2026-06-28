"""`orionfold gpu enable|status|disable` (headless) — drives the opt-in + sudoers lifecycle.

The DB is isolated via ``ORIONFOLD_DB`` (the same pattern as ``test_cli_unlock``). The privileged
``gpu_setup.install_sudoers``/``remove_sudoers``/``probe_powermetrics`` calls are monkeypatched so the
suite never escalates privilege — we assert the CLI's orchestration (opt-in persistence, exit codes,
honest output), not the real shell-out (that's ``test_gpu_setup``).
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from orionfold.cli import app
from orionfold.storage.db import apply_migrations, connect, default_db_path
from orionfold.storage.settings import get_powermetrics_optin
from orionfold.telemetry import gpu_setup

runner = CliRunner()


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    return tmp_path


def _optin() -> bool:
    conn = connect(default_db_path())
    try:
        apply_migrations(conn)  # a fresh test DB may not be migrated if the CLI bailed pre-DB
        return get_powermetrics_optin(conn)
    finally:
        conn.close()


def test_enable_installs_rule_and_sets_optin(store, monkeypatch) -> None:
    monkeypatch.setattr(gpu_setup, "is_macos", lambda: True)
    monkeypatch.setattr(gpu_setup, "powermetrics_present", lambda: True)
    monkeypatch.setattr(gpu_setup, "install_sudoers", lambda: None)
    monkeypatch.setattr(gpu_setup, "probe_powermetrics", lambda: True)

    result = runner.invoke(app, ["gpu", "enable"])
    assert result.exit_code == 0, result.stdout
    assert "enabled" in result.stdout.lower()
    assert _optin() is True


def test_enable_on_non_macos_exits_2_without_touching_optin(store, monkeypatch) -> None:
    monkeypatch.setattr(gpu_setup, "is_macos", lambda: False)
    # install must never be reached on an unsupported platform.
    monkeypatch.setattr(
        gpu_setup, "install_sudoers", lambda: pytest.fail("install_sudoers called on non-macOS")
    )

    result = runner.invoke(app, ["gpu", "enable"])
    assert result.exit_code == 2
    assert "macos" in result.stderr.lower()
    assert _optin() is False


def test_enable_missing_powermetrics_exits_2(store, monkeypatch) -> None:
    monkeypatch.setattr(gpu_setup, "is_macos", lambda: True)
    monkeypatch.setattr(gpu_setup, "powermetrics_present", lambda: False)
    monkeypatch.setattr(
        gpu_setup, "install_sudoers", lambda: pytest.fail("install_sudoers called without powermetrics")
    )

    result = runner.invoke(app, ["gpu", "enable"])
    assert result.exit_code == 2
    assert "powermetrics" in result.stderr.lower()


def test_enable_install_failure_exits_1_and_leaves_optin_off(store, monkeypatch) -> None:
    monkeypatch.setattr(gpu_setup, "is_macos", lambda: True)
    monkeypatch.setattr(gpu_setup, "powermetrics_present", lambda: True)

    def boom() -> None:
        raise gpu_setup.GpuSetupError("validation failed and was removed")

    monkeypatch.setattr(gpu_setup, "install_sudoers", boom)

    result = runner.invoke(app, ["gpu", "enable"])
    assert result.exit_code == 1
    assert "validation failed" in result.stderr
    assert _optin() is False


def test_status_reports_optin_rule_and_reachable(store, monkeypatch) -> None:
    monkeypatch.setattr(gpu_setup, "sudoers_rule_present", lambda: True)
    monkeypatch.setattr(gpu_setup, "probe_powermetrics", lambda: True)

    result = runner.invoke(app, ["gpu", "status"])
    assert result.exit_code == 0, result.stdout
    out = result.stdout.lower()
    assert "opt-in" in out
    assert "sudoers" in out
    assert "reachable" in out


def test_disable_removes_rule_and_clears_optin(store, monkeypatch) -> None:
    # First enable so there's an opt-in to clear.
    monkeypatch.setattr(gpu_setup, "is_macos", lambda: True)
    monkeypatch.setattr(gpu_setup, "powermetrics_present", lambda: True)
    monkeypatch.setattr(gpu_setup, "install_sudoers", lambda: None)
    monkeypatch.setattr(gpu_setup, "probe_powermetrics", lambda: True)
    runner.invoke(app, ["gpu", "enable"])
    assert _optin() is True

    removed: list[bool] = []
    monkeypatch.setattr(gpu_setup, "remove_sudoers", lambda: removed.append(True))

    result = runner.invoke(app, ["gpu", "disable"])
    assert result.exit_code == 0, result.stdout
    assert "disabled" in result.stdout.lower()
    assert removed == [True]
    assert _optin() is False
