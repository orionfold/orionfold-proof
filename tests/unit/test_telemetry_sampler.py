from orionfold.domain.models import TelemetrySummary
from orionfold.telemetry.sampler import RunSampler, _sample_once


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
