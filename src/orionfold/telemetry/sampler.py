"""Live run sampler — a background thread reading OS stats ~every 500ms during a run.

Re-authored from Arena's Telemetry shape for the local-first context. Best-effort: a sample
that fails is skipped; if no sample ever succeeds the summary is ``sampled=False`` (honest
absence). The thread only READS OS stats — it never touches provider threads, run output, or
``config_hash``.
"""

from __future__ import annotations

import re
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


# powermetrics' GPU-utilization line label varies by macOS version. Newer builds (Sequoia and
# later) report "GPU HW active residency: NN.NN% (...)" — note the trailing per-frequency
# breakdown in parens, which a naive split(":")[-1] mis-parses. Older builds reported
# "GPU Busy: NN%" / "GPU active: NN%". We match any of these and pull the FIRST percentage after
# the label. As a last resort we invert "GPU idle residency" (active = 100 - idle). `_PCT` is
# anchored to grab a number immediately followed by `%`, so it never grabs a MHz/mW value.
_PCT = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*%")
_ACTIVE_LABELS = ("GPU HW active residency", "GPU active", "GPU Busy")


def _parse_gpu_util(text: str) -> float | None:
    """Extract GPU utilization % from `powermetrics --samplers gpu_power` output, or None.

    Pure (no subprocess) so the label/format handling is unit-tested against real fixtures.
    """
    idle: float | None = None
    for line in text.splitlines():
        for label in _ACTIVE_LABELS:
            if label in line:
                m = _PCT.search(line)
                if m:
                    return float(m.group(1))
        if "GPU idle residency" in line:
            m = _PCT.search(line)
            if m:
                idle = float(m.group(1))
    # Fallback: only an idle figure was present — active is its complement.
    return round(100 - idle, 2) if idle is not None else None


def _powermetrics_gpu_util() -> float | None:
    # Opt-in, macOS: needs passwordless sudo for `powermetrics`. `-n 1` = one sample.
    try:
        out = subprocess.check_output(
            ["sudo", "-n", "powermetrics", "--samplers", "gpu_power", "-n", "1", "-i", "200"],
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).decode()
        return _parse_gpu_util(out)
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


_TREND_BUCKET = 2  # samples per sealed bar; matches the FE sparkline's pushSample({bucket:2}).


def _bucket_peaks(values: list[float | None], bucket: int) -> list[float]:
    """Peak-over-window reduction matching the FE sparkline (``pushSample``), for the STORED series.

    Seals one bar (the window's max) every ``bucket`` samples; nulls contribute nothing to a
    window's peak, and an all-null window yields no bar. Unlike the live FE — which keeps a
    forming bucket open — the persisted series also seals the trailing partial window so the last
    samples survive in the record. Pure: a plain reduction over the metric column, unit-tested
    against the FE's bucket semantics.
    """
    bucket = max(1, bucket)
    peaks: list[float] = []
    for i in range(0, len(values), bucket):
        window = [v for v in values[i : i + bucket] if v is not None]
        if window:
            peaks.append(max(window))
    return peaks


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
            # Per-bucket peak series for the rail's dimmed last-run sparkline (persisted record).
            cpu_series=_bucket_peaks([s.get("cpu_util") for s in samples], _TREND_BUCKET),
            gpu_series=_bucket_peaks([s.get("gpu_util") for s in samples], _TREND_BUCKET),
            mem_series=_bucket_peaks([s.get("mem_used_gb") for s in samples], _TREND_BUCKET),
        )
