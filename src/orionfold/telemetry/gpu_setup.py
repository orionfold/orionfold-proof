"""GPU-telemetry onboarding — install / probe / remove the `powermetrics` sudoers drop-in.

The honest end-to-end cost of enabling Apple-Silicon GPU telemetry used to be a terminal gauntlet
(hand-author a sudoers NOPASSWD rule, fight `visudo` + an editor, strand processes). This module
owns that sequence behind one safe, reviewable surface so ``orionfold gpu enable/status/disable``
(and a read-only Settings probe) can drive it.

Security posture:
  * The NOPASSWD scope is **fixed** to ``/usr/bin/powermetrics`` — never interpolated from a request
    or argument. The username comes from the OS (``getpass.getuser``), not from input.
  * ``install_sudoers`` writes via the proven ``tee`` + ``chmod 0440`` + ``visudo -cf`` sequence and
    **rolls back** (``rm -f``) any file that fails ``visudo`` validation — an invalid sudoers file is
    never left on disk. The privileged ``tee``/``chmod``/``rm`` run as plain (interactive) ``sudo`` so
    macOS prompts for the password ONCE in the user's own terminal (conscious authorization). No
    editor is ever launched.
  * Every privileged shell-out goes through the single ``_run`` seam so the logic is unit-tested
    without real escalation.

GPU telemetry is presentation-only and excluded from ``config_hash`` — enabling or disabling it never
changes any run's identity or receipt.
"""

from __future__ import annotations

import getpass
import subprocess
import sys
from pathlib import Path

SUDOERS_PATH = "/etc/sudoers.d/orionfold-powermetrics"
POWERMETRICS_BIN = "/usr/bin/powermetrics"

# The exact at-rest sample argv (matches sampler._powermetrics_gpu_util). Success of this command is
# the reachability signal: it only succeeds when passwordless sudo for powermetrics is in place.
_PROBE_ARGV = ["sudo", "-n", "powermetrics", "--samplers", "gpu_power", "-n", "1", "-i", "200"]
_PROBE_TIMEOUT_S = 3


class GpuSetupError(Exception):
    """A privileged setup step failed (the message is safe to show the user)."""


def _run(args: list[str], *, input: str | None = None, timeout: int | None = None) -> subprocess.CompletedProcess:
    """The single subprocess seam (monkeypatched in tests so no real sudo runs)."""
    return subprocess.run(
        args,
        input=input,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _current_user() -> str:
    return getpass.getuser()


def is_macos() -> bool:
    return sys.platform == "darwin"


def powermetrics_present() -> bool:
    return Path(POWERMETRICS_BIN).exists()


def sudoers_rule(user: str) -> str:
    """The drop-in line granting passwordless powermetrics to one user — scope is fixed."""
    return f"{user} ALL=(root) NOPASSWD: {POWERMETRICS_BIN}\n"


def sudoers_rule_present() -> bool:
    return Path(SUDOERS_PATH).exists()


def probe_powermetrics() -> bool:
    """True iff a single privileged powermetrics sample succeeds (passwordless sudo is primed).

    Best-effort: any non-zero exit, timeout, or exception → False. Output is not parsed — we only
    care whether the command is reachable without a password prompt.
    """
    try:
        proc = _run(_PROBE_ARGV, timeout=_PROBE_TIMEOUT_S)
    except Exception:
        return False
    return proc.returncode == 0


def install_sudoers() -> None:
    """Write the validated powermetrics NOPASSWD drop-in. Raises ``GpuSetupError`` on failure.

    Steps (privileged, interactive sudo — prompts once): tee the scoped rule → chmod 0440 →
    ``visudo -cf`` validate. If validation fails, the unvalidated file is removed before raising so a
    broken sudoers file can never lock the user out of sudo.
    """
    rule = sudoers_rule(_current_user())

    tee = _run(["sudo", "tee", SUDOERS_PATH], input=rule)
    if tee.returncode != 0:
        raise GpuSetupError(
            "Could not write the sudoers drop-in (the sudo password prompt may have been cancelled)."
        )

    # The file now exists at the default mode and is UNVALIDATED. Any failure past this point — a
    # non-zero exit, a raised exception, or a Ctrl-C at a sudo re-prompt — must roll it back so a
    # broken/over-permissive file can never linger in /etc/sudoers.d. ``BaseException`` catches
    # KeyboardInterrupt too.
    try:
        chmod = _run(["sudo", "chmod", "0440", SUDOERS_PATH])
        if chmod.returncode != 0:
            raise GpuSetupError("Could not set permissions on the sudoers drop-in; rolled back.")

        check = _run(["sudo", "visudo", "-cf", SUDOERS_PATH])
        if check.returncode != 0:
            raise GpuSetupError(
                "The sudoers drop-in failed validation and was removed (no change made)."
            )
    except BaseException:
        _run(["sudo", "rm", "-f", SUDOERS_PATH])
        raise


def remove_sudoers() -> None:
    """Remove the drop-in (idempotent — ``rm -f`` succeeds when it's already absent)."""
    _run(["sudo", "rm", "-f", SUDOERS_PATH])
