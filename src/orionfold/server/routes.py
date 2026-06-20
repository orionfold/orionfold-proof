"""FastAPI routes for the proof loop — datasets, candidates, runs, and receipt downloads.

All persistence goes through a per-request SQLite connection opened from the path on
``app.state`` (set up in the lifespan). Run ids and timestamps are generated here (the engine
itself stays deterministic and clock-free).
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from orionfold.domain.models import Candidate, ProofBrief, ProofReport, Rubric
from orionfold.proof.engine import run_proof
from orionfold.providers.registry import available_candidates
from orionfold.receipts import export
from orionfold.storage.db import apply_migrations, connect
from orionfold.storage.repository import (
    get_dataset,
    get_report,
    list_datasets,
    list_runs,
    save_report,
    seed_datasets,
)

router = APIRouter(prefix="/api")


class RunRequest(BaseModel):
    dataset_id: str
    candidate_ids: list[str]
    rubric: Rubric = Rubric()
    brief: ProofBrief


def _conn(request: Request) -> sqlite3.Connection:
    return connect(request.app.state.db_path)


def init_db(db_path) -> None:
    """Apply migrations and seed bundled datasets — called once at startup."""
    conn = connect(db_path)
    try:
        apply_migrations(conn)
        seed_datasets(conn)
    finally:
        conn.close()


@router.get("/datasets")
def get_datasets(request: Request):
    conn = _conn(request)
    try:
        return list_datasets(conn)
    finally:
        conn.close()


@router.get("/candidates")
def get_candidates() -> list[Candidate]:
    return available_candidates()


@router.post("/runs")
def create_run(request: Request, body: RunRequest) -> ProofReport:
    conn = _conn(request)
    try:
        dataset = get_dataset(conn, body.dataset_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Unknown dataset")

        available = {c.id: c for c in available_candidates()}
        if not body.candidate_ids:
            raise HTTPException(status_code=400, detail="Select at least one candidate")
        unknown = [cid for cid in body.candidate_ids if cid not in available]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown candidate(s): {unknown}")
        candidates = [available[cid] for cid in body.candidate_ids]

        # Normalize to the trailing-Z form so live receipts match the fixtures/samples.
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        report = run_proof(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            created_at=now,
            brief=body.brief,
            dataset=dataset,
            candidates=candidates,
            rubric=body.rubric,
        )
        save_report(conn, report)
        return report
    finally:
        conn.close()


@router.get("/runs")
def get_runs(request: Request) -> list[ProofReport]:
    conn = _conn(request)
    try:
        return list_runs(conn)
    finally:
        conn.close()


@router.get("/runs/{run_id}")
def get_single_run(request: Request, run_id: str) -> ProofReport:
    conn = _conn(request)
    try:
        report = get_report(conn, run_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Unknown run")
        return report
    finally:
        conn.close()


_FORMATS = {
    "json": (export.to_json, "application/json"),
    "md": (export.to_markdown, "text/markdown"),
    "html": (export.to_html, "text/html"),
}


@router.get("/runs/{run_id}/receipt.{fmt}")
def download_receipt(request: Request, run_id: str, fmt: str) -> Response:
    if fmt not in _FORMATS:
        raise HTTPException(status_code=404, detail="Unknown receipt format")
    conn = _conn(request)
    try:
        report = get_report(conn, run_id)
    finally:
        conn.close()
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown run")

    render, media_type = _FORMATS[fmt]
    body = render(report)
    filename = f"proof-receipt-{report.run.config_hash}.{fmt}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if fmt == "html":
        return Response(content=body, media_type=media_type, headers=headers)
    return PlainTextResponse(content=body, media_type=media_type, headers=headers)
