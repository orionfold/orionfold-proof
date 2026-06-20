"""FastAPI routes for the proof loop — datasets, candidates, runs, and receipt downloads.

All persistence goes through a per-request SQLite connection opened from the path on
``app.state`` (set up in the lifespan). Run ids and timestamps are generated here (the engine
itself stays deterministic and clock-free).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel

from orionfold.data.importers import DatasetParseError, ImportFormat, ParseResult, parse_dataset
from orionfold.domain.models import Candidate, Dataset, ProofBrief, ProofReport, ProofRun, Rubric
from orionfold.proof.engine import config_hash, iter_matrix, run_proof
from orionfold.proof.leaderboard import build_leaderboard
from orionfold.providers.registry import available_candidates
from orionfold.receipts import export
from orionfold.storage.db import apply_migrations, connect
from orionfold.storage.repository import (
    DuplicateDatasetError,
    get_dataset,
    get_report,
    list_datasets,
    list_runs,
    save_dataset,
    save_report,
    seed_datasets,
)

router = APIRouter(prefix="/api")


class DatasetPreviewRequest(BaseModel):
    format: ImportFormat
    text: str


class DatasetCreateRequest(BaseModel):
    name: str
    description: str = ""
    format: ImportFormat
    text: str


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


@router.post("/datasets/preview")
def preview_dataset(body: DatasetPreviewRequest) -> ParseResult:
    """Parse the supplied text and return the pairs + warnings. Never writes."""
    try:
        return parse_dataset(body.text, body.format)
    except DatasetParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/datasets", status_code=201)
def create_dataset(request: Request, body: DatasetCreateRequest) -> Dataset:
    """Re-parse server-side (source of truth), then freeze into a new dataset."""
    try:
        result = parse_dataset(body.text, body.format)
    except DatasetParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    conn = _conn(request)
    try:
        return save_dataset(conn, body.name, body.description, result.examples)
    except DuplicateDatasetError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
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


def _sse(payload: dict) -> str:
    """Serialize one Server-Sent Event frame; the event kind rides in the JSON ``type``."""
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/runs/stream")
def create_run_stream(request: Request, body: RunRequest) -> StreamingResponse:
    """Run a proof, streaming progress as Server-Sent Events.

    Frames (one JSON object per ``data:`` line):
      - ``start``: total cells, examples-per-candidate, and the ordered candidate list. The
        client derives the currently-running cell from ``done`` + this order (candidate-major),
        so progress events stay tiny.
      - ``progress``: cumulative ``done`` count plus the just-finished cell's outcome.
      - ``report``: the full, persisted :class:`ProofReport` (same shape as ``POST /runs``).
    Validation runs synchronously up front so a bad request is a normal 4xx, not an SSE error.
    """
    conn = _conn(request)
    try:
        dataset = get_dataset(conn, body.dataset_id)
    finally:
        conn.close()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    available = {c.id: c for c in available_candidates()}
    if not body.candidate_ids:
        raise HTTPException(status_code=400, detail="Select at least one candidate")
    unknown = [cid for cid in body.candidate_ids if cid not in available]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown candidate(s): {unknown}")
    candidates = [available[cid] for cid in body.candidate_ids]
    db_path = request.app.state.db_path

    def events() -> Iterator[str]:
        n_examples = len(dataset.examples)
        yield _sse(
            {
                "type": "start",
                "total": n_examples * len(candidates),
                "n_examples": n_examples,
                "candidates": [
                    {"id": c.id, "label": c.label, "provider_id": c.provider_id, "privacy": c.privacy}
                    for c in candidates
                ],
            }
        )
        rows = []
        for done, row in enumerate(iter_matrix(dataset, candidates, body.rubric), start=1):
            rows.append(row)
            yield _sse(
                {
                    "type": "progress",
                    "done": done,
                    "candidate_id": row.candidate_id,
                    "example_index": row.example_index,
                    "passed": row.passed,
                    "error": row.error is not None,
                }
            )
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        run = ProofRun(
            id=f"run_{uuid.uuid4().hex[:12]}",
            brief=body.brief,
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            rubric=body.rubric,
            candidates=candidates,
            config_hash=config_hash(dataset, candidates, body.rubric),
            created_at=now,
        )
        report = ProofReport(run=run, leaderboard=build_leaderboard(candidates, rows), results=rows)
        write = connect(db_path)
        try:
            save_report(write, report)
        finally:
            write.close()
        yield _sse({"type": "report", "report": report.model_dump(mode="json")})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Defeat proxy/dev-server buffering so events arrive cell-by-cell, not all at the end.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
def download_receipt(
    request: Request, run_id: str, fmt: str, inline: bool = False, theme: str | None = None
) -> Response:
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
    if fmt == "html":
        body = export.to_html(report, theme=theme)
    else:
        body = render(report)
    filename = f"proof-receipt-{report.run.config_hash}.{fmt}"
    # inline=1 lets the cockpit render the receipt in an iframe; the default download is unchanged.
    disposition = "inline" if inline else "attachment"
    headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
    if fmt == "html":
        # Defense-in-depth for the only renderable format: sandbox the document (no scripts,
        # opaque origin) and forbid content-type sniffing, so even a directly-navigated receipt
        # cannot execute script against the app origin. The body is already fully html-escaped.
        headers["Content-Security-Policy"] = "sandbox"
        headers["X-Content-Type-Options"] = "nosniff"
        return Response(content=body, media_type=media_type, headers=headers)
    return PlainTextResponse(content=body, media_type=media_type, headers=headers)
