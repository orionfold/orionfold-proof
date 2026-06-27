from orionfold.domain.models import HostProfile
from orionfold.telemetry import host as host_mod


def test_host_profile_defaults_are_none_except_arch():
    p = HostProfile(arch="arm64")
    assert p.arch == "arm64"
    assert p.chip is None
    assert p.cpu_cores is None
    assert p.memory_gb is None
    assert p.os_label is None
    assert p.local_runtime is None
    assert p.gpu_label is None


def test_host_profile_roundtrips():
    p = HostProfile(
        arch="arm64",
        chip="Apple M3 Max",
        cpu_cores=14,
        memory_gb=36.0,
        os_label="macOS 15.1",
        local_runtime="Ollama",
        gpu_label="Apple M3 Max GPU",
    )
    assert HostProfile.model_validate(p.model_dump()) == p


def test_detect_host_profile_always_returns_arch():
    host_mod._clear_cache()
    p = host_mod.detect_host_profile()
    # arch is the one field that always resolves (platform.machine never empty)
    assert p.arch
    assert isinstance(p.arch, str)


def test_detect_host_profile_is_cached():
    host_mod._clear_cache()
    a = host_mod.detect_host_profile()
    b = host_mod.detect_host_profile()
    assert a is b  # same object — cached, not re-probed


def test_probe_failures_degrade_to_none(monkeypatch):
    host_mod._clear_cache()

    # Force every subprocess shell-out to raise → fields go None, never crash.
    def boom(*a, **k):
        raise OSError("no such tool")

    monkeypatch.setattr(host_mod.subprocess, "check_output", boom)
    p = host_mod.detect_host_profile()
    assert p.arch  # still resolves (stdlib platform)
    # chip/os_label come from shell-outs that just failed → None, no exception
    assert p.chip is None
