from orionfold.domain.models import TelemetrySummary
from orionfold.telemetry.sampler import RunSampler, _runtime_rss_gb, _sample_once


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


def test_rollup_of_no_samples_is_unsampled():
    summary = RunSampler._rollup([], sampled=False)
    assert summary.sampled is False
    assert summary.n_samples == 0


def test_sampler_that_never_started_is_unsampled():
    summary = RunSampler(gpu_opt_in=False).stop()
    assert summary.sampled is False
    assert summary.n_samples == 0
