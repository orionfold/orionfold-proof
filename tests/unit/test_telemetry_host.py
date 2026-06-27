from orionfold.domain.models import HostProfile


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
