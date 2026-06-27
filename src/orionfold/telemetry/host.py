"""Static host-profile detection. Best-effort, cached, cross-platform.

Mirrors the ``providers/health.py`` posture: every probe is wrapped; a failure sets the
field to ``None`` ("unavailable") rather than raising. Result is cached for the process.
"""

from __future__ import annotations

import platform
import subprocess

import psutil

from orionfold.domain.models import HostProfile

_cache: HostProfile | None = None


def _clear_cache() -> None:
    global _cache
    _cache = None


def _sh(args: list[str]) -> str | None:
    """Run a short command, return stripped stdout, or None on any failure."""
    try:
        out = subprocess.check_output(args, stderr=subprocess.DEVNULL, timeout=3)
        return out.decode("utf-8", "replace").strip() or None
    except Exception:
        return None


def _macos_chip() -> str | None:
    # `sysctl -n machdep.cpu.brand_string` → "Apple M3 Max" on Apple Silicon.
    return _sh(["sysctl", "-n", "machdep.cpu.brand_string"])


def _macos_os_label() -> str | None:
    name = _sh(["sw_vers", "-productName"])
    ver = _sh(["sw_vers", "-productVersion"])
    if name and ver:
        return f"{name} {ver}"
    return name or ver


def _linux_gpu_label() -> str | None:
    # `nvidia-smi -L` → "GPU 0: NVIDIA RTX 4090 (UUID: ...)"; take the model substring.
    out = _sh(["nvidia-smi", "-L"])
    if not out:
        return None
    first = out.splitlines()[0]
    if ":" in first:
        model = first.split(":", 1)[1].split("(")[0].strip()
        return model or None
    return None


def detect_host_profile() -> HostProfile:
    """Return a cached, best-effort description of this machine."""
    global _cache
    if _cache is not None:
        return _cache

    arch = platform.machine() or "unknown"
    system = platform.system()  # "Darwin" / "Linux" / "Windows"

    chip: str | None = None
    os_label: str | None = None
    gpu_label: str | None = None

    if system == "Darwin":
        chip = _macos_chip()
        os_label = _macos_os_label()
        gpu_label = f"{chip} GPU" if chip else None  # Apple Silicon: GPU is the SoC
    elif system == "Linux":
        os_label = _sh(["sh", "-c", '. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME"'])
        gpu_label = _linux_gpu_label()
    else:
        os_label = f"{system} {platform.release()}".strip() or None

    try:
        cpu_cores = psutil.cpu_count(logical=True)
    except Exception:
        cpu_cores = None
    try:
        memory_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        memory_gb = None

    _cache = HostProfile(
        arch=arch,
        chip=chip,
        cpu_cores=cpu_cores,
        memory_gb=memory_gb,
        os_label=os_label,
        local_runtime=None,  # filled by the route layer from the provider registry (Task 4)
        gpu_label=gpu_label,
    )
    return _cache
