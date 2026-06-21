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

from orionfold.catalog import load_catalog
from orionfold.catalog.models import ModelCatalog
from orionfold.config.env_file import set_key_in_env_local
from orionfold.config.keys import CLOUD_KEY_NAMES, has_key
from orionfold.providers.selection import SelectionPanel, selection_panel
from orionfold.recipes.resolution import RecipesPanel, resolve_recipes
from orionfold.data.importers import DatasetParseError, ImportFormat, ParseResult, parse_dataset
from orionfold.domain.models import Candidate, Dataset, ProofBrief, ProofReport, ProofRun, Rubric
from orionfold.proof.engine import build_cost_summary, config_hash, iter_matrix, run_proof
from orionfold.proof.leaderboard import build_leaderboard
from orionfold.providers.registry import (
    UnknownCandidateError,
    available_candidates,
    build_candidates,
)
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


class CredentialRequest(BaseModel):
    provider_id: str
    key: str


class CredentialStatus(BaseModel):
    provider_id: str
    available: bool


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


@router.get("/catalog")
def get_catalog() -> ModelCatalog:
    """The bundled model catalog (provider → model → capabilities). Read-only reference data.

    Consumed by the model picker and decision recipes (later sub-projects). Contains no
    credentials — purely static selection metadata.
    """
    return load_catalog()


@router.get("/selection")
def get_selection() -> SelectionPanel:
    """The model picker's data: provider groups with availability + catalog models + mocks.

    Read-only and resolved server-side so the cockpit (and later decision recipes) share one
    availability source. Contains no credentials.
    """
    return selection_panel()


@router.get("/recipes")
def get_recipes() -> RecipesPanel:
    """Named decision recipes, resolved against the current environment (catalog ∩ availability).

    Read-only SELECTION metadata: provider labels, model ids, and the env-var NAME a provider
    needs — never a key value, never run provenance.
    """
    return resolve_recipes()


@router.post("/credentials")
def set_credential(body: CredentialRequest) -> CredentialStatus:
    """Write one cloud provider's API key into .env.local so its candidates unlock.

    Whitelisted to the four cloud providers (no arbitrary env writes). The key is written to a
    git-ignored 0o600 file and is NEVER logged or echoed in the response.
    """
    key_name = CLOUD_KEY_NAMES.get(body.provider_id)
    if key_name is None:
        raise HTTPException(status_code=400, detail=f"Unknown cloud provider: {body.provider_id}")
    if not body.key.strip():
        raise HTTPException(status_code=422, detail="Key must not be empty")
    set_key_in_env_local(key_name, body.key.strip())
    return CredentialStatus(provider_id=body.provider_id, available=has_key(key_name))


@router.post("/runs")
def create_run(request: Request, body: RunRequest) -> ProofReport:
    conn = _conn(request)
    try:
        dataset = get_dataset(conn, body.dataset_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Unknown dataset")

        if not body.candidate_ids:
            raise HTTPException(status_code=400, detail="Select at least one candidate")
        try:
            candidates = build_candidates(body.candidate_ids)
        except UnknownCandidateError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

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
    if not body.candidate_ids:
        raise HTTPException(status_code=400, detail="Select at least one candidate")
    try:
        candidates = build_candidates(body.candidate_ids)
    except UnknownCandidateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
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
        report = ProofReport(
            run=run,
            leaderboard=build_leaderboard(candidates, rows),
            results=rows,
            cost_summary=build_cost_summary(rows),
        )
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
        # Only the HTML receipt is themeable, so it bypasses the generic render to pass the theme.
        # Validate the reflected param to a known set here (defense-in-depth: to_html guards too, but
        # the boundary must stay safe even if that inner guard is ever refactored away). An unknown
        # value falls back to the OS-adaptive default receipt.
        safe_theme = theme if theme in ("light", "dark") else None
        body = export.to_html(report, theme=safe_theme)
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
