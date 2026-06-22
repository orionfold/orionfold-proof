"""FastAPI routes for the proof loop — datasets, candidates, runs, and receipt downloads.

All persistence goes through a per-request SQLite connection opened from the path on
``app.state`` (set up in the lifespan). Run ids and timestamps are generated here (the engine
itself stays deterministic and clock-free).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Literal
from datetime import datetime, timezone

from collections.abc import Iterator

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel

from orionfold.catalog import load_catalog
from orionfold.catalog.models import ModelCatalog
from orionfold.config.env_file import set_key_in_env_local
from orionfold.config.keys import CLOUD_KEY_NAMES, has_key
from orionfold.providers.selection import SelectionPanel, selection_panel
from orionfold.recipes.resolution import RecipesPanel, resolve_recipes
from orionfold.data.importers import DatasetParseError, ImportFormat, ParseResult, parse_dataset
from orionfold.data.extractors import (
    DocExtractError,
    ExtractResult,
    doc_format_for,
    extract_document,
)
from orionfold.domain.models import Candidate, Dataset, Example, ProofBrief, ProofReport, ProofRun, PromptVariant, Rubric
from orionfold.proof.engine import build_cost_summary, config_hash, iter_matrix, run_proof
from orionfold.proof.leaderboard import build_leaderboard
from orionfold.scoring.judge import build_judge
from orionfold.scoring.rubric import default_rubric_for
from orionfold.providers.registry import (
    UnknownCandidateError,
    available_candidates,
    build_candidates,
    expand_prompt_variants,
)
from orionfold.receipts import export
from orionfold.sample_data import seed_sample_data
from orionfold.storage.db import apply_migrations, connect
from orionfold.storage.repository import (
    DuplicateDatasetError,
    clear_all_data,
    get_dataset,
    get_dataset_meta,
    get_report,
    list_dataset_rows,
    list_runs,
    remove_sample_data,
    save_dataset,
    save_report,
    seed_datasets,
    update_dataset_meta,
)
from orionfold.storage.settings import get_sandbox_enabled, set_sandbox_enabled

router = APIRouter(prefix="/api")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB — datasets are small; this guards memory + abuse.


class DatasetPreviewRequest(BaseModel):
    format: ImportFormat
    text: str


class DatasetCreateRequest(BaseModel):
    name: str
    description: str = ""
    format: ImportFormat
    text: str
    tags: list[str] = []
    source: str = ""
    check_hint: str | None = None


class DatasetPatchRequest(BaseModel):
    tags: list[str] | None = None
    description: str | None = None
    check_hint: str | None = None


class RunRequest(BaseModel):
    dataset_id: str = ""  # ignored when `examples` is provided (quick-compare)
    candidate_ids: list[str]
    rubric: Rubric | None = None
    brief: ProofBrief
    prompt_variants: list[PromptVariant] | None = None
    examples: list[Example] | None = None  # inline ad-hoc examples (quick-compare); no dataset row
    mode: Literal["full", "quick"] = "full"


class WinnerRequest(BaseModel):
    chosen_winner: str  # a candidate_id from the run, or the literal "tie"


class CredentialRequest(BaseModel):
    provider_id: str
    key: str


class CredentialStatus(BaseModel):
    provider_id: str
    available: bool


class SettingsModel(BaseModel):
    sandbox_enabled: bool


class DataCounts(BaseModel):
    datasets: int
    receipts: int


class DatasetRow(BaseModel):
    id: str
    name: str
    description: str
    examples: list[Example]
    is_sample: bool
    tags: list[str] = []
    created_at: str = ""
    source: str = ""
    check_hint: str | None = None


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


def _to_row(d: Dataset, m) -> DatasetRow:
    return DatasetRow(
        id=d.id,
        name=d.name,
        description=d.description,
        examples=d.examples,
        is_sample=m.is_sample,
        tags=m.tags,
        created_at=m.created_at,
        source=m.source,
        check_hint=m.check_hint,
    )


@router.get("/datasets")
def get_datasets(request: Request) -> list[DatasetRow]:
    conn = _conn(request)
    try:
        return [_to_row(d, m) for d, m in list_dataset_rows(conn)]
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
def create_dataset(request: Request, body: DatasetCreateRequest) -> DatasetRow:
    """Re-parse server-side (source of truth), then freeze into a new dataset."""
    try:
        result = parse_dataset(body.text, body.format)
    except DatasetParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    conn = _conn(request)
    try:
        created = save_dataset(
            conn,
            body.name,
            body.description,
            result.examples,
            tags=body.tags,
            source=body.source or "pasted",
            check_hint=body.check_hint,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        meta = get_dataset_meta(conn, created.id)
        assert meta is not None
        return _to_row(created, meta)
    except DuplicateDatasetError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    finally:
        conn.close()


@router.post("/datasets/extract")
async def extract_dataset(file: UploadFile = File(...)) -> ExtractResult:
    """Extract an uploaded .xlsx/.docx/.pdf into normalized import text. Never writes."""
    doc_format = doc_format_for(file.filename or "")
    if doc_format is None:
        raise HTTPException(
            status_code=422,
            detail="Unsupported file type. Upload .xlsx, .docx, or .pdf (or paste text directly).",
        )
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (5 MB max).")
    try:
        return extract_document(data, doc_format)
    except DocExtractError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch("/datasets/{dataset_id}")
def patch_dataset(request: Request, dataset_id: str, body: DatasetPatchRequest) -> DatasetRow:
    """Edit display metadata (tags/description/check_hint) only — never the frozen examples."""
    provided = body.model_dump(exclude_unset=True)
    conn = _conn(request)
    try:
        ok = update_dataset_meta(
            conn,
            dataset_id,
            tags=provided.get("tags"),
            description=provided.get("description"),
            check_hint=provided.get("check_hint"),
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        ds = get_dataset(conn, dataset_id)
        meta = get_dataset_meta(conn, dataset_id)
        assert ds is not None and meta is not None
        return _to_row(ds, meta)
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
def get_selection(request: Request) -> SelectionPanel:
    """The model picker's data: provider groups with availability + catalog models.

    Read-only and resolved server-side so the cockpit (and later decision recipes) share one
    availability source. The simulated Mock provider appears only when Sandbox is enabled.
    Contains no credentials.
    """
    conn = _conn(request)
    try:
        return selection_panel(sandbox=get_sandbox_enabled(conn))
    finally:
        conn.close()


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


@router.get("/settings")
def read_settings(request: Request) -> SettingsModel:
    conn = _conn(request)
    try:
        return SettingsModel(sandbox_enabled=get_sandbox_enabled(conn))
    finally:
        conn.close()


@router.put("/settings")
def update_settings(request: Request, body: SettingsModel) -> SettingsModel:
    conn = _conn(request)
    try:
        set_sandbox_enabled(conn, body.sandbox_enabled)
        return SettingsModel(sandbox_enabled=get_sandbox_enabled(conn))
    finally:
        conn.close()


@router.post("/sample-data/seed")
def seed_samples(request: Request) -> DataCounts:
    """Populate the install with a sample dataset + a finished receipt (generated by the mocks)."""
    conn = _conn(request)
    try:
        datasets, receipts = seed_sample_data(conn)
        return DataCounts(datasets=datasets, receipts=receipts)
    finally:
        conn.close()


@router.delete("/sample-data")
def delete_samples(request: Request) -> DataCounts:
    """Remove only the seeded sample data; the user's own datasets and receipts are kept."""
    conn = _conn(request)
    try:
        datasets, receipts = remove_sample_data(conn)
        return DataCounts(datasets=datasets, receipts=receipts)
    finally:
        conn.close()


@router.delete("/data")
def clear_data(request: Request) -> DataCounts:
    """Delete ALL datasets and runs on this install (settings are kept). Irreversible."""
    conn = _conn(request)
    try:
        datasets, receipts = clear_all_data(conn)
        return DataCounts(datasets=datasets, receipts=receipts)
    finally:
        conn.close()


def _resolve_candidates(body: RunRequest) -> list[Candidate]:
    """Resolve the run's candidates, fanning out prompt variants when requested.

    Model-compare (no prompt_variants): today's behavior exactly. Prompt-compare: exactly one
    model, at least two non-empty variants, fanned out via expand_prompt_variants.
    """
    try:
        base = build_candidates(body.candidate_ids)
    except UnknownCandidateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not body.prompt_variants:
        return base
    if len(base) != 1:
        raise HTTPException(status_code=422, detail="Prompt comparison needs exactly one model.")
    variants = body.prompt_variants
    if len(variants) < 2:
        raise HTTPException(status_code=422, detail="Add at least two prompt variants to compare.")
    for v in variants:
        if not v.name.strip() or not v.system_prompt.strip():
            raise HTTPException(
                status_code=422, detail="Each prompt variant needs a name and prompt text."
            )
    return expand_prompt_variants(base[0], variants)


def _resolve_dataset(conn: sqlite3.Connection, body: RunRequest) -> Dataset:
    """The dataset under test: an ephemeral one for quick-compare, else the stored row."""
    if body.examples:
        return Dataset(id="quick-compare", name="Quick Compare", examples=body.examples)
    dataset = get_dataset(conn, body.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    return dataset


@router.post("/runs")
def create_run(request: Request, body: RunRequest) -> ProofReport:
    conn = _conn(request)
    try:
        dataset = _resolve_dataset(conn, body)

        if not body.candidate_ids:
            raise HTTPException(status_code=400, detail="Select at least one candidate")
        candidates = _resolve_candidates(body)

        rubric = body.rubric or default_rubric_for(dataset)
        if rubric.kind == "judge":
            try:
                build_judge(rubric)
            except (ValueError, KeyError) as exc:
                raise HTTPException(status_code=422, detail=f"Judge not available: {exc}")
        # Normalize to the trailing-Z form so live receipts match the fixtures/samples.
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            report = run_proof(
                run_id=f"run_{uuid.uuid4().hex[:12]}",
                created_at=now,
                brief=body.brief,
                dataset=dataset,
                candidates=candidates,
                rubric=rubric,
            )
            report.run.mode = body.mode
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
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
        dataset = _resolve_dataset(conn, body)
    finally:
        conn.close()
    if not body.candidate_ids:
        raise HTTPException(status_code=400, detail="Select at least one candidate")
    candidates = _resolve_candidates(body)
    rubric = body.rubric or default_rubric_for(dataset)
    if rubric.kind == "judge":
        try:
            build_judge(rubric)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=f"Judge not available: {exc}")
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
        for done, row in enumerate(iter_matrix(dataset, candidates, rubric), start=1):
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
            rubric=rubric,
            candidates=candidates,
            config_hash=config_hash(dataset, candidates, rubric),
            created_at=now,
            mode=body.mode,
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


@router.patch("/runs/{run_id}/winner")
def set_winner(request: Request, run_id: str, body: WinnerRequest) -> ProofReport:
    """Record the operator's head-to-head pick on a quick-compare run."""
    conn = _conn(request)
    try:
        report = get_report(conn, run_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Unknown run")
        if report.run.mode != "quick":
            raise HTTPException(status_code=400, detail="Only quick-compare runs take a pick.")
        valid = {c.id for c in report.run.candidates} | {"tie"}
        if body.chosen_winner not in valid:
            raise HTTPException(status_code=400, detail="Pick must be one of the run's candidates.")
        report.run.chosen_winner = body.chosen_winner
        save_report(conn, report)
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
