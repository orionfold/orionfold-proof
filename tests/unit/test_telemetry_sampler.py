from orionfold.domain.models import TelemetrySummary


def test_telemetry_summary_unsampled_default_is_honest():
    s = TelemetrySummary()
    assert s.sampled is False
    assert s.n_samples == 0
    assert s.cpu_util_mean is None
    assert s.gpu_util_max is None
