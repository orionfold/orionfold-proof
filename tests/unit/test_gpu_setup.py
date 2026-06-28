"""`gpu_setup` — the privileged GPU-telemetry onboarding surface, tested without real sudo.

Every privileged shell-out goes through one injectable seam (`gpu_setup._run`), so these tests
verify the install/rollback/probe logic by monkeypatching that seam — the suite NEVER actually
escalates privilege or writes to /etc/sudoers.d. The sudoers scope is asserted to be exactly
`/usr/bin/powermetrics` (no broad NOPASSWD, no user-interpolated path).
"""

from __future__ import annotations

import subprocess

import pytest

from orionfold.telemetry import gpu_setup


def test_sudoers_rule_is_scoped_to_powermetrics_only() -> None:
    rule = gpu_setup.sudoers_rule("alice")
    assert rule == "alice ALL=(root) NOPASSWD: /usr/bin/powermetrics\n"
    # Scope guard: the only command the rule ever grants is powermetrics.
    assert "/usr/bin/powermetrics" in rule
    assert "ALL=(ALL)" not in rule and "NOPASSWD: ALL" not in rule


def test_constants_are_fixed() -> None:
    assert gpu_setup.SUDOERS_PATH == "/etc/sudoers.d/orionfold-powermetrics"
    assert gpu_setup.POWERMETRICS_BIN == "/usr/bin/powermetrics"


def test_probe_powermetrics_uses_the_exact_idle_argv_and_returns_true_on_success(monkeypatch) -> None:
    seen: list[list[str]] = []

    def fake_run(args, **kwargs):
        seen.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="GPU HW active residency: 5.11%\n", stderr="")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    assert gpu_setup.probe_powermetrics() is True
    assert seen == [
        ["sudo", "-n", "powermetrics", "--samplers", "gpu_power", "-n", "1", "-i", "200"]
    ]


def test_probe_powermetrics_false_on_nonzero_exit(monkeypatch) -> None:
    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="sudo: a password is required\n")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    assert gpu_setup.probe_powermetrics() is False


def test_probe_powermetrics_false_on_exception(monkeypatch) -> None:
    def boom(args, **kwargs):
        raise subprocess.TimeoutExpired(args, 3)

    monkeypatch.setattr(gpu_setup, "_run", boom)
    assert gpu_setup.probe_powermetrics() is False


def test_install_sudoers_runs_tee_chmod_visudo_in_order(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    monkeypatch.setattr(gpu_setup, "_current_user", lambda: "bob")

    gpu_setup.install_sudoers()

    # tee the rule into the drop-in, lock it 0440, then validate with visudo -c.
    assert calls[0][:3] == ["sudo", "tee", gpu_setup.SUDOERS_PATH]
    assert calls[1] == ["sudo", "chmod", "0440", gpu_setup.SUDOERS_PATH]
    assert calls[2] == ["sudo", "visudo", "-cf", gpu_setup.SUDOERS_PATH]
    # No rollback rm on the happy path.
    assert not any(c[:2] == ["sudo", "rm"] for c in calls)


def test_install_sudoers_pipes_the_scoped_rule_to_tee(monkeypatch) -> None:
    piped: dict[str, str] = {}

    def fake_run(args, *, input=None, **kwargs):
        if args[:2] == ["sudo", "tee"]:
            piped["input"] = input or ""
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    monkeypatch.setattr(gpu_setup, "_current_user", lambda: "bob")

    gpu_setup.install_sudoers()
    assert piped["input"] == "bob ALL=(root) NOPASSWD: /usr/bin/powermetrics\n"


def test_install_sudoers_rolls_back_and_raises_when_visudo_rejects(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        rc = 1 if args[:3] == ["sudo", "visudo", "-cf"] else 0
        return subprocess.CompletedProcess(args, rc, stdout="", stderr="parse error" if rc else "")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    monkeypatch.setattr(gpu_setup, "_current_user", lambda: "bob")

    with pytest.raises(gpu_setup.GpuSetupError):
        gpu_setup.install_sudoers()

    # An invalid sudoers file must NEVER be left on disk → a rollback rm runs.
    assert ["sudo", "rm", "-f", gpu_setup.SUDOERS_PATH] in calls


def test_install_sudoers_rolls_back_when_a_post_tee_step_raises(monkeypatch) -> None:
    # A raised exception (e.g. Ctrl-C at a sudo re-prompt, missing visudo) past the tee must NOT
    # leave the unvalidated file on disk — a rollback rm runs before the exception propagates.
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["sudo", "chmod"]:
            raise KeyboardInterrupt
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    monkeypatch.setattr(gpu_setup, "_current_user", lambda: "bob")

    with pytest.raises(KeyboardInterrupt):
        gpu_setup.install_sudoers()

    assert ["sudo", "rm", "-f", gpu_setup.SUDOERS_PATH] in calls


def test_install_sudoers_raises_when_tee_fails(monkeypatch) -> None:
    def fake_run(args, **kwargs):
        rc = 1 if args[:2] == ["sudo", "tee"] else 0
        return subprocess.CompletedProcess(args, rc, stdout="", stderr="denied" if rc else "")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    monkeypatch.setattr(gpu_setup, "_current_user", lambda: "bob")

    with pytest.raises(gpu_setup.GpuSetupError):
        gpu_setup.install_sudoers()


def test_remove_sudoers_is_idempotent_rm_f(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(gpu_setup, "_run", fake_run)
    gpu_setup.remove_sudoers()
    assert calls == [["sudo", "rm", "-f", gpu_setup.SUDOERS_PATH]]


def test_sudoers_rule_present_reads_the_filesystem(monkeypatch, tmp_path) -> None:
    drop_in = tmp_path / "orionfold-powermetrics"
    monkeypatch.setattr(gpu_setup, "SUDOERS_PATH", str(drop_in))
    assert gpu_setup.sudoers_rule_present() is False
    drop_in.write_text("bob ALL=(root) NOPASSWD: /usr/bin/powermetrics\n")
    assert gpu_setup.sudoers_rule_present() is True


def test_platform_guards(monkeypatch) -> None:
    monkeypatch.setattr(gpu_setup.sys, "platform", "darwin")
    assert gpu_setup.is_macos() is True
    monkeypatch.setattr(gpu_setup.sys, "platform", "linux")
    assert gpu_setup.is_macos() is False
