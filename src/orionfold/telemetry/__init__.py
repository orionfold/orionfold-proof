"""Host telemetry: static host profile + live run sampling.

Presentation-only — nothing here ever enters ``config_hash``. Best-effort: any probe
that fails degrades a field to ``None``/"unavailable" and never raises into a run.
"""

from orionfold.telemetry.host import detect_host_profile
from orionfold.telemetry.sampler import RunSampler

__all__ = ["RunSampler", "detect_host_profile"]
