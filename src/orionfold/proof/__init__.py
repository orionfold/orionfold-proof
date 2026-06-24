"""Proof core — the run engine, the run stitch, and the cross-run primitives.

This package's ``__all__`` is the curated public surface (ADR-0004 §2). Consumers import from
here (``from orionfold.proof import execute_run``); names not listed are internal.
"""

from orionfold.proof.engine import (
    build_cost_summary,
    config_hash,
    iter_matrix,
    run_matrix,
    run_proof,
)
from orionfold.proof.runner import execute_run

__all__ = [
    "execute_run",
    "run_proof",
    "run_matrix",
    "iter_matrix",
    "config_hash",
    "build_cost_summary",
]
