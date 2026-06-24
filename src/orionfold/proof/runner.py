"""The headless run stitch — shared by the FastAPI route and the CLI.

``execute_run`` is the single place that turns a resolved dataset + candidate ids + (optional)
rubric into a finished :class:`ProofReport`. It is pure: no FastAPI, no database, no file IO.
The id and timestamp are generated here (the engine stays clock-free, per ADR-0003); the format
matches ``server/routes.py`` exactly so CLI receipts are byte-compatible with the cockpit's.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from orionfold.domain.models import Dataset, ProofBrief, ProofReport, Rubric
from orionfold.proof.engine import run_proof
from orionfold.providers.registry import build_candidates
from orionfold.scoring.rubric import default_rubric_for


def _now() -> str:
    """UTC, seconds precision, trailing-Z — matches the live route and the receipt fixtures."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def execute_run(
    *,
    dataset: Dataset,
    candidate_ids: list[str],
    brief: ProofBrief,
    rubric: Rubric | None = None,
    mode: Literal["full", "quick"] = "full",
) -> ProofReport:
    """Run the full proof matrix and return the assembled report.

    ``candidate_ids`` are resolved via ``build_candidates`` (raising ``UnknownCandidateError`` on
    an unavailable/unknown id). When ``rubric`` is ``None`` the default is resolved from the
    dataset via ``default_rubric_for``. The run id and ``created_at`` are generated here.
    """
    candidates = build_candidates(candidate_ids)
    resolved_rubric = rubric or default_rubric_for(dataset)
    report = run_proof(
        run_id=f"run_{uuid.uuid4().hex[:12]}",
        created_at=_now(),
        brief=brief,
        dataset=dataset,
        candidates=candidates,
        rubric=resolved_rubric,
    )
    report.run.mode = mode
    return report
