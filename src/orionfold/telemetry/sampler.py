"""Live run sampler — a background thread reading OS stats ~every 500ms during a run.

Re-authored from Arena's Telemetry shape for the local-first context. Best-effort: a sample
that fails is skipped; if no sample ever succeeds the summary is ``sampled=False`` (honest
absence). The thread only READS OS stats — it never touches provider threads, run output, or
``config_hash``.
"""

from __future__ import annotations

import subprocess
import threading

import psutil

from orionfold.domain.models import TelemetrySummary

_INTERVAL_S = 0.5

# Process-name fragments for the local runtimes whose RSS we want (the llama_server memory).
_RUNTIME_PROCS = ("ollama", "llama_server", "llama-server", "lm-studio", "lmstudio")

# Below this, a "serving runtime" footprint is implausibly small for a loaded model — it's the bare
# server shim with no weights resident (e.g. Ollama's ~0.06 GB API process before/without a runner
# child). Report None (honest absence) rather than bake a misleading number into a permanent
# receipt. A genuinely tiny model on CPU still clears this comfortably.
_MIN_PLAUSIBLE_RSS_GB = 0.5


def _nvidia_gpu_util() -> float | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return float(out.decode().strip().splitlines()[0])
    except Exception:
        return None


def _powermetrics_gpu_util() -> float | None:
    # Opt-in, macOS: needs sudo. `-n 1` one sample. Parse the "GPU active"/"GPU Busy" line.
    try:
        out = subprocess.check_output(
            ["sudo", "-n", "powermetrics", "--samplers", "gpu_power", "-n", "1", "-i", "200"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).decode()
        for line in out.splitlines():
            if "GPU active" in line or "GPU Busy" in line:
                pct = line.split(":")[-1].strip().rstrip("%")
                return float(pct)
        return None
    except Exception:
        return None


def _gpu_util(gpu_opt_in: bool) -> float | None:
    nv = _nvidia_gpu_util()
    if nv is not None:
        return nv
    if gpu_opt_in:
        return _powermetrics_gpu_util()
    return None  # Mac without opt-in → honest unavailable, never a fabricated number


def _runtime_rss_gb(procs: list[tuple[int, int, str, int]]) -> float | None:
    """Sum RSS (GB) across the local runtime's whole process TREE, best-effort.

    ``procs`` is ``(pid, ppid, name, rss_bytes)`` for every process. Ollama is a client/server
    split: the process whose name matches ``_RUNTIME_PROCS`` is the thin server shim, while the
    model weights live in an ``ollama runner`` CHILD (often named generically, e.g. ``llama``).
    Matching only the shim reported ~0.1 GB for a multi-GB model. So: seed from every name-matched
    process, then walk the parent→child graph to include all descendants, and sum their RSS — the
    weights get counted whatever the child is named. Returns None when nothing matches, or when the
    total is implausibly small (the shim alone, no weights resident) — honest absence over a wrong
    number.
    """
    children: dict[int, list[int]] = {}
    rss_by_pid: dict[int, int] = {}
    seeds: list[int] = []
    for pid, ppid, name, rss in procs:
        children.setdefault(ppid, []).append(pid)
        rss_by_pid[pid] = rss
        if any(k in (name or "").lower() for k in _RUNTIME_PROCS):
            seeds.append(pid)
    if not seeds:
        return None
    # BFS over the tree from each seed; a set guards against double-counting shared subtrees.
    seen: set[int] = set()
    queue = list(seeds)
    while queue:
        pid = queue.pop()
        if pid in seen:
            continue
        seen.add(pid)
        queue.extend(children.get(pid, ()))
    total_gb = sum(rss_by_pid.get(pid, 0) for pid in seen) / (1024**3)
    if total_gb < _MIN_PLAUSIBLE_RSS_GB:
        return None
    return round(total_gb, 2)


def _serving_rss_gb() -> float | None:
    """RSS of the local runtime's process tree (the weights-bearing runner), best-effort."""
    try:
        procs: list[tuple[int, int, str, int]] = []
        for p in psutil.process_iter(["ppid", "name", "memory_info"]):
            mem = p.info.get("memory_info")
            procs.append(
                (p.pid, p.info.get("ppid") or 0, p.info.get("name") or "", mem.rss if mem else 0)
            )
    except Exception:
        return None
    return _runtime_rss_gb(procs)


def _sample_once(gpu_opt_in: bool) -> dict:
    try:
        cpu = psutil.cpu_percent(interval=None)
    except Exception:
        cpu = 0.0
    try:
        vm = psutil.virtual_memory()
        mem_used = round((vm.total - vm.available) / (1024**3), 1)
    except Exception:
        mem_used = None
    return {
        "cpu_util": cpu,
        "mem_used_gb": mem_used,
        "process_rss_gb": _serving_rss_gb(),
        "gpu_util": _gpu_util(gpu_opt_in),
    }


class RunSampler:
    """Background sampler for one run. ``start()`` then ``stop() -> TelemetrySummary``.

    ``latest()`` exposes the most recent sample for the live SSE stream.
    """

    def __init__(self, gpu_opt_in: bool = False) -> None:
        self._gpu_opt_in = gpu_opt_in
        self._samples: list[dict] = []
        self._latest: dict | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = False

    def start(self) -> None:
        self._started = True
        self._thread = threading.Thread(target=self._loop, name="proof-telemetry", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        psutil.cpu_percent(interval=None)  # prime the cpu_percent baseline (first call is 0.0)
        while not self._stop.wait(_INTERVAL_S):
            s = _sample_once(self._gpu_opt_in)
            self._samples.append(s)
            self._latest = s

    def latest(self) -> dict | None:
        return self._latest

    def stop(self) -> TelemetrySummary:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        return self._rollup(self._samples, sampled=self._started and bool(self._samples))

    @staticmethod
    def _rollup(samples: list[dict], *, sampled: bool) -> TelemetrySummary:
        if not samples:
            return TelemetrySummary(sampled=False, n_samples=0)
        cpu = [s["cpu_util"] for s in samples if s.get("cpu_util") is not None]
        mem = [s["mem_used_gb"] for s in samples if s.get("mem_used_gb") is not None]
        rss = [s["process_rss_gb"] for s in samples if s.get("process_rss_gb") is not None]
        gpu = [s["gpu_util"] for s in samples if s.get("gpu_util") is not None]
        return TelemetrySummary(
            sampled=sampled,
            n_samples=len(samples),
            cpu_util_mean=round(sum(cpu) / len(cpu), 1) if cpu else None,
            cpu_util_max=max(cpu) if cpu else None,
            mem_used_gb_max=max(mem) if mem else None,
            process_rss_gb_max=max(rss) if rss else None,
            gpu_util_mean=round(sum(gpu) / len(gpu), 1) if gpu else None,
            gpu_util_max=max(gpu) if gpu else None,
        )
