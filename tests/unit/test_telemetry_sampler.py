from orionfold.domain.models import TelemetrySummary
from orionfold.telemetry.sampler import (
    RunSampler,
    _bucket_peaks,
    _parse_gpu_util,
    _runtime_rss_gb,
    _sample_once,
)


# Real `powermetrics --samplers gpu_power` output captured on a Mac15,10 / macOS Sequoia
# (24G623). This OS reports "GPU HW active residency", NOT the older "GPU active"/"GPU Busy"
# the parser used to grep for — and the line carries many colons + a trailing paren, which a
# naive split(":")[-1] mis-parses. This fixture locks the real-world shape.
SEQUOIA_GPU_POWER = """\
Machine model: Mac15,10
*** Sampled system activity ***

**** GPU usage ****

GPU HW active frequency: 338 MHz
GPU HW active residency:   5.11% (338 MHz: 5.1% 618 MHz:   0% 796 MHz:   0%)
GPU SW requested state: (P1 : 100% P2 :   0%)
GPU idle residency:  94.89%
GPU Power: 29 mW
"""

# Older powermetrics label still seen on some macOS builds.
LEGACY_GPU_BUSY = """\
**** GPU usage ****
GPU active frequency: 700 MHz
GPU Busy: 42.0%
"""


def test_parse_gpu_util_reads_sequoia_active_residency():
    # The bug this session caught while enabling GPU on a real Mac: "GPU HW active residency"
    # must be parsed, and only the FIRST percentage (5.11), not a value from inside the parens.
    assert _parse_gpu_util(SEQUOIA_GPU_POWER) == 5.11


def test_parse_gpu_util_reads_legacy_busy_label():
    assert _parse_gpu_util(LEGACY_GPU_BUSY) == 42.0


def test_parse_gpu_util_falls_back_to_inverting_idle_residency():
    # If only an idle line is present, active = 100 - idle (they sum to 100 by definition).
    assert _parse_gpu_util("GPU idle residency: 94.89%") == round(100 - 94.89, 2)  # → 5.11


def test_parse_gpu_util_none_when_no_gpu_line():
    assert _parse_gpu_util("Machine model: Mac15,10\nGPU Power: 29 mW\n") is None


# A process record is (pid, ppid, name, rss_bytes). _runtime_rss_gb must sum the RSS of every
# process in the runtime's TREE (the matched parent + all descendants), so the multi-GB model
# weights — which Ollama holds in an `ollama runner` CHILD, not the thin server shim — are counted.
GB = 1024**3


def test_runtime_rss_sums_ollama_server_and_runner_child():
    # The real bug: the `ollama` server shim is ~0.06 GB; the model weights live in the `ollama
    # runner` child (~5 GB). Matching only the first "ollama" process reported 0.1 GB for a 4B
    # model. Summing the tree must report the real footprint.
    procs = [
        (1948, 1, "Ollama", int(0.06 * GB)),  # the .app wrapper
        (1974, 1948, "ollama", int(0.06 * GB)),  # the server shim (matched by name)
        (2001, 1974, "ollama runner", int(5.0 * GB)),  # the weights — child of the shim
        (9999, 1, "Finder", int(0.5 * GB)),  # unrelated, must not count
    ]
    assert _runtime_rss_gb(procs) == 5.12  # 0.06 + 0.06 + 5.0, rounded to 0.01 GB


def test_runtime_rss_counts_llama_subprocess_child_by_lineage_not_name():
    # A runner child named `llama` (or anything) is still counted because it descends from the
    # matched runtime process — lineage, not a name allow-list, is what catches the weights.
    procs = [
        (100, 1, "ollama", int(0.05 * GB)),
        (200, 100, "llama", int(6.2 * GB)),  # generic-named child holding weights
    ]
    assert _runtime_rss_gb(procs) == 6.25


def test_runtime_rss_none_when_no_runtime_process():
    procs = [(1, 0, "launchd", int(0.1 * GB)), (2, 1, "Finder", int(0.5 * GB))]
    assert _runtime_rss_gb(procs) is None


def test_runtime_rss_suppressed_when_implausibly_small():
    # Honest absence over a wrong number: if the only thing we can find is the bare shim (no runner
    # child loaded yet), the footprint is implausibly small for a served model — return None rather
    # than print a misleading 0.1 GB into a permanent receipt.
    procs = [(1974, 1948, "ollama", int(0.06 * GB))]
    assert _runtime_rss_gb(procs) is None


def test_telemetry_summary_unsampled_default_is_honest():
    s = TelemetrySummary()
    assert s.sampled is False
    assert s.n_samples == 0
    assert s.cpu_util_mean is None
    assert s.gpu_util_max is None


def test_sample_once_has_cpu_and_mem_and_honest_gpu():
    s = _sample_once(gpu_opt_in=False)
    assert "cpu_util" in s
    assert "mem_used_gb" in s
    assert s["gpu_util"] is None  # opt-in off, no NVIDIA → honest None, never fabricated


def test_rollup_of_fixed_samples_computes_means_and_maxes():
    samples = [
        {"cpu_util": 40.0, "mem_used_gb": 20.0, "process_rss_gb": 8.0, "gpu_util": None},
        {"cpu_util": 60.0, "mem_used_gb": 22.0, "process_rss_gb": 8.4, "gpu_util": None},
    ]
    summary = RunSampler._rollup(samples, sampled=True)
    assert summary.sampled is True
    assert summary.n_samples == 2
    assert summary.cpu_util_mean == 50.0
    assert summary.cpu_util_max == 60.0
    assert summary.mem_used_gb_max == 22.0
    assert summary.process_rss_gb_max == 8.4
    assert summary.gpu_util_max is None  # all None → stays None, never 0


def test_bucket_peaks_seals_a_peak_every_bucket_samples():
    # Mirrors the FE pushSample({bucket:2}) peak-over-window: every 2 samples seal to their max.
    assert _bucket_peaks([5.0, 9.0, 4.0, 1.0], 2) == [9.0, 4.0]


def test_bucket_peaks_seals_a_trailing_partial_window():
    # Unlike the live FE (which keeps a forming bucket), the STORED series seals the trailing
    # partial window too so the last samples aren't lost from the persisted record.
    assert _bucket_peaks([5.0, 9.0, 4.0], 2) == [9.0, 4.0]


def test_bucket_peaks_ignores_nulls_within_a_window_and_drops_all_null_windows():
    # null contributes nothing to a window's peak; a window with only nulls produces no bar.
    assert _bucket_peaks([7.0, None, 3.0, None], 2) == [7.0, 3.0]
    assert _bucket_peaks([None, None], 2) == []


def test_bucket_peaks_empty_is_empty():
    assert _bucket_peaks([], 2) == []


def test_rollup_persists_per_bucket_trend_series():
    samples = [
        {"cpu_util": 40.0, "mem_used_gb": 20.0, "process_rss_gb": 8.0, "gpu_util": 30.0},
        {"cpu_util": 60.0, "mem_used_gb": 22.0, "process_rss_gb": 8.4, "gpu_util": 50.0},
        {"cpu_util": 55.0, "mem_used_gb": 21.0, "process_rss_gb": 8.2, "gpu_util": 45.0},
    ]
    summary = RunSampler._rollup(samples, sampled=True)
    # bucket=2 over 3 samples: [max(40,60)=60, trailing max(55)=55].
    assert summary.cpu_series == [60.0, 55.0]
    assert summary.mem_series == [22.0, 21.0]
    assert summary.gpu_series == [50.0, 45.0]


def test_rollup_series_are_empty_when_unsampled():
    summary = RunSampler._rollup([], sampled=False)
    assert summary.cpu_series == []
    assert summary.gpu_series == []
    assert summary.mem_series == []


def test_rollup_of_no_samples_is_unsampled():
    summary = RunSampler._rollup([], sampled=False)
    assert summary.sampled is False
    assert summary.n_samples == 0


def test_sampler_that_never_started_is_unsampled():
    summary = RunSampler(gpu_opt_in=False).stop()
    assert summary.sampled is False
    assert summary.n_samples == 0
