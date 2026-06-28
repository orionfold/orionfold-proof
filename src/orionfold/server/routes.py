"""FastAPI routes for the proof loop — datasets, candidates, runs, and receipt downloads.

All persistence goes through a per-request SQLite connection opened from the path on
``app.state`` (set up in the lifespan). Run ids and timestamps are generated here (the engine
itself stays deterministic and clock-free).
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import sqlite3
import threading
import uuid
from typing import Literal
from datetime import datetime, timezone

from collections.abc import AsyncIterator, Iterator

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from orionfold.catalog import load_catalog
from orionfold.catalog.models import ModelCatalog
from orionfold.config.env_file import set_key_in_env_local
from orionfold.config.keys import CLOUD_KEY_NAMES, has_key
from orionfold.providers.health import probe_all
from orionfold.providers.selection import SelectionPanel, selection_panel
from orionfold.recipes.resolution import RecipesPanel, resolve_recipes
from orionfold.data.importers import DatasetParseError, ImportFormat, ParseResult, parse_dataset
from orionfold.data.extractors import (
    DocExtractError,
    ExtractResult,
    doc_format_for,
    extract_document,
)
from orionfold.corpora import enrich_corpus_sources
from orionfold.domain.models import (
    Candidate,
    Corpus,
    CorpusSource,
    CostRollup,
    Dataset,
    Example,
    HostProfile,
    ProofBrief,
    ProofReport,
    ProofRun,
    PromptVariant,
    ResultRow,
    Rubric,
    TrackRecordGroup,
)
from orionfold.proof.cost_rollup import cost_rollup
from orionfold.proof.engine import build_cost_summary, config_hash, run_matrix_concurrent
from orionfold.proof.runner import execute_resolved
from orionfold.proof.leaderboard import build_leaderboard, track_record
from orionfold.scoring.judge import build_judge
from orionfold.scoring.rubric import default_rubric_for
from orionfold.providers.registry import (
    UnknownCandidateError,
    available_candidates,
    build_candidates,
    expand_prompt_variants,
)
from orionfold.receipts import export
from orionfold.telemetry import RunSampler, detect_host_profile
from orionfold.telemetry import gpu_setup
from orionfold.telemetry.sampler import _nvidia_gpu_util, _powermetrics_gpu_util
from orionfold.sample_data import seed_sample_data
from orionfold.storage.db import apply_migrations, connect
from orionfold.storage.repository import (
    BenchBindingError,
    DuplicateDatasetError,
    clear_all_data,
    get_corpus,
    get_dataset,
    get_dataset_meta,
    get_report,
    list_corpora,
    list_dataset_rows,
    list_datasets,
    list_runs,
    remove_sample_data,
    save_dataset,
    save_report,
    seed_bench_datasets,
    seed_corpora,
    seed_datasets,
    update_dataset_meta,
    validate_bench_binding,
)
from orionfold.storage.settings import (
    get_max_retries,
    get_powermetrics_optin,
    get_sandbox_enabled,
    get_threshold_defaults,
    set_max_retries,
    set_powermetrics_optin,
    set_sandbox_enabled,
    set_threshold_defaults,
)

router = APIRouter(prefix="/api")

# The sampler for the run currently streaming, if any. The cockpit runs one proof at a time, so a
# single ref suffices (no multi-run registry — YAGNI). The /telemetry/stream handler reads its
# .latest(); it is set when a run starts and cleared in a finally when the run ends.
_CURRENT_SAMPLER: RunSampler | None = None

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
    # Models-mode task instruction: a single system prompt applied to every selected candidate so
    # classification/extraction tasks can be proven (the models classify instead of "helping").
    # Ignored when prompt_variants is set (that path supplies a per-variant prompt). Set on a
    # candidate → feeds config_hash (a different, intentional proof); absent → hashes unchanged.
    system_prompt: str | None = None


class WinnerRequest(BaseModel):
    chosen_winner: str  # a candidate_id from the run, or the literal "tie"


class CredentialRequest(BaseModel):
    provider_id: str
    key: str


class CredentialStatus(BaseModel):
    provider_id: str
    available: bool


class ThresholdDefaults(BaseModel):
    """Per-kind default passing thresholds (0..1) the Settings sliders tune."""

    similarity: float = Field(ge=0.0, le=1.0)
    keypoint: float = Field(ge=0.0, le=1.0)
    judge: float = Field(ge=0.0, le=1.0)


class SettingsModel(BaseModel):
    """The full, resolved settings the GET returns."""

    sandbox_enabled: bool
    powermetrics_gpu_optin: bool
    provider_max_retries: int
    thresholds: ThresholdDefaults


class SettingsUpdate(BaseModel):
    """A partial settings update (PUT): only the supplied fields are written, others untouched.

    Kept partial so existing callers that send only ``sandbox_enabled`` keep working and a future
    field is additive rather than a breaking change.
    """

    sandbox_enabled: bool | None = None
    powermetrics_gpu_optin: bool | None = None
    provider_max_retries: int | None = Field(default=None, ge=0, le=10)
    thresholds: ThresholdDefaults | None = None


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
    corpus_id: str | None = None
    system_prompt: str | None = None


def _conn(request: Request) -> sqlite3.Connection:
    return connect(request.app.state.db_path)


def init_db(db_path) -> None:
    """Apply migrations, seed bundled datasets, and hydrate env knobs — called once at startup."""
    conn = connect(db_path)
    try:
        apply_migrations(conn)
        seed_datasets(conn)
        seed_corpora(conn)  # bench bindings validate against bundled corpora — seed them first
        seed_bench_datasets(conn)
        hydrate_env_from_settings(conn)  # seed ORIONFOLD_MAX_RETRIES from the persisted setting
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
        corpus_id=d.corpus_id,
        system_prompt=d.system_prompt,
    )


@router.get("/datasets")
def get_datasets(request: Request) -> list[DatasetRow]:
    conn = _conn(request)
    try:
        return [_to_row(d, m) for d, m in list_dataset_rows(conn)]
    finally:
        conn.close()


@router.get("/corpora")
def get_corpora(request: Request) -> list[Corpus]:
    """The governed corpora a bench dataset can cite against (provenance; not retrieval)."""
    conn = _conn(request)
    try:
        return list_corpora(conn)
    finally:
        conn.close()


@router.get("/corpora/{corpus_id}/sources")
def get_corpus_sources(corpus_id: str, request: Request) -> list[CorpusSource]:
    """Enriched source records for a corpus, DERIVED from the bench examples bound to it (title/
    class/excerpt are flattened into example ``input_text``; the manifest stores only ids). Read-only
    — nothing is persisted. 404 when the corpus id is unknown."""
    conn = _conn(request)
    try:
        corpus = get_corpus(conn, corpus_id)
        if corpus is None:
            raise HTTPException(status_code=404, detail=f"unknown corpus: {corpus_id}")
        bound = [d for d in list_datasets(conn) if d.corpus_id == corpus_id]
        examples = [ex for d in bound for ex in d.examples]
        return enrich_corpus_sources(examples, source_ids=corpus.source_ids)
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


class ProviderHealthModel(BaseModel):
    """One provider's liveness probe result. Contains no credentials — safe to show and log."""

    provider_id: str
    status: Literal["ok", "auth", "permission", "quota", "down", "unreachable"]
    message: str
    remediation: str


class ProviderHealthPanel(BaseModel):
    """All currently-active providers' health, for graying out failing candidates in the UI."""

    providers: list[ProviderHealthModel]


@router.get("/health/providers")
def get_provider_health() -> ProviderHealthPanel:
    """Probe every active provider with a free, token-free request and report each one's health.

    Cloud providers hit a metadata endpoint (e.g. ``GET /v1/models``) — never a generation
    endpoint, so no tokens are spent — and the result distinguishes a working key from a
    down / rate-limited / billing-blocked / revoked one. Local providers (Ollama, LM Studio)
    report whether their server is reachable. Read-only; contains no key material.
    """
    results = probe_all()
    return ProviderHealthPanel(
        providers=[
            ProviderHealthModel(
                provider_id=r.provider_id,
                status=r.status,
                message=r.message,
                remediation=r.remediation,
            )
            for r in results
        ]
    )


_LOCAL_RUNTIME_LABELS = {"ollama": "Ollama", "lmstudio": "LM Studio", "llamacpp": "llama.cpp"}


def _configured_local_runtime() -> str | None:
    """Friendly label for the real local runtime that is actually serving, or None.

    The registry always lists Ollama/LM Studio (keyless local profiles), so presence alone
    would dishonestly claim "Ollama" even when nothing is running. We only label a runtime that
    is (a) a *real* hardware runtime — the mock providers carry ``privacy="local"`` to simulate
    a local model for the keyless demo, but they are not hardware and must never appear here —
    and (b) reachable per its health probe (``status == "ok"``), the same honest signal the
    cockpit uses to gray out unrunnable candidates.
    """
    reachable = {r.provider_id for r in probe_all() if r.status == "ok"}
    for pid in _LOCAL_RUNTIME_LABELS:  # only the real local runtimes, in preference order
        if pid in reachable:
            return _LOCAL_RUNTIME_LABELS[pid]
    return None


def _labeled_host_profile() -> HostProfile:
    """The cached static profile with the reachable local runtime labeled (a fresh copy each call,
    so the cache stays unmutated). Used by the host endpoint AND the run capture so the receipt's
    hardware stanza names the serving runtime."""
    return detect_host_profile().model_copy(update={"local_runtime": _configured_local_runtime()})


@router.get("/telemetry/host")
def telemetry_host() -> HostProfile:
    """Static host profile, with the configured local runtime labeled. Read-only, no secrets."""
    return _labeled_host_profile()


class GpuIdle(BaseModel):
    gpu_util: float | None = None


@router.get("/telemetry/gpu-idle")
def telemetry_gpu_idle(request: Request) -> GpuIdle:
    """A single at-rest GPU utilization read for the rail (so the GPU cell shows idle %, not blank).

    The unprivileged NVIDIA query is always tried first. The macOS powermetrics path is privileged
    (sudo) and is gated SERVER-SIDE behind the operator's opt-in — this endpoint refuses to shell
    out unless ``powermetrics_gpu_optin`` is set, regardless of who calls it (the FE's throttle is a
    courtesy; this is the guarantee). Best-effort: any failure returns ``gpu_util=None`` (the cell
    shows "at rest"/"unavailable", never an error). One-shot, no standing thread.
    """
    nv = _nvidia_gpu_util()
    if nv is not None:
        return GpuIdle(gpu_util=nv)
    conn = _conn(request)
    try:
        optin = get_powermetrics_optin(conn)
    finally:
        conn.close()
    if not optin:
        return GpuIdle(gpu_util=None)
    return GpuIdle(gpu_util=_powermetrics_gpu_util())


class GpuSetupStatus(BaseModel):
    """Whether GPU telemetry is set up — drives the Settings "ready / needs setup" badge."""

    supported: bool  # this host can report GPU util (macOS+powermetrics, or any NVIDIA host)
    opt_in: bool  # the persisted powermetrics opt-in toggle
    reachable: bool  # a single GPU read currently succeeds (NVIDIA, or primed passwordless sudo)


@router.get("/telemetry/gpu-setup")
def telemetry_gpu_setup(request: Request) -> GpuSetupStatus:
    """Report GPU-telemetry setup state so the cockpit can guide onboarding without a terminal.

    Read-only and mutates nothing. The NVIDIA query is unprivileged and always tried first; on a Mac,
    ``reachable`` runs the same fixed one-shot powermetrics probe the sampler uses (it only succeeds
    when the operator has installed the ``orionfold gpu enable`` sudoers rule). The privileged probe
    is gated behind the opt-in — same as ``telemetry_gpu_idle`` — so it never shells out without
    consent; with the opt-in off it reports ``reachable=False`` (the Settings badge only renders while
    the opt-in is on, so nothing user-facing is lost). Carries no secrets.
    """
    conn = _conn(request)
    try:
        opt_in = get_powermetrics_optin(conn)
    finally:
        conn.close()

    nvidia_ok = _nvidia_gpu_util() is not None
    if nvidia_ok:
        return GpuSetupStatus(supported=True, opt_in=opt_in, reachable=True)

    supported = gpu_setup.is_macos() and gpu_setup.powermetrics_present()
    reachable = gpu_setup.probe_powermetrics() if (supported and opt_in) else False
    return GpuSetupStatus(supported=supported, opt_in=opt_in, reachable=reachable)


@router.get("/telemetry/stream")
async def telemetry_stream() -> StreamingResponse:
    """Emit the latest live sample ~every 500ms while a run is active; closes when idle.

    Reads only the current run's sampler (OS stats); carries no secrets. Closes itself after a
    short idle window so a client that connects between runs doesn't hang open forever.
    """

    async def gen() -> AsyncIterator[str]:
        idle_ticks = 0
        while idle_ticks < 4:  # ~2s of no active sampler → close
            sample = _CURRENT_SAMPLER.latest() if _CURRENT_SAMPLER else None
            if sample is None:
                idle_ticks += 1
            else:
                idle_ticks = 0
                yield _sse(sample)
            await asyncio.sleep(0.5)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


# Env var the provider HTTP layer reads for its retry cap. The Settings store is the UI's
# persistence; mirroring the value here is what lets a PUT take effect live (no server restart).
_MAX_RETRIES_ENV = "ORIONFOLD_MAX_RETRIES"


def hydrate_env_from_settings(conn: sqlite3.Connection) -> None:
    """Seed env knobs from persisted settings at startup so a fresh process honors the UI value.

    A value already present in the shell env WINS — env is the source of truth for a power user;
    the DB is just where the Settings UI persists its choice. Called once from the lifespan.
    """
    if _MAX_RETRIES_ENV not in os.environ:
        os.environ[_MAX_RETRIES_ENV] = str(get_max_retries(conn))


def _read_settings(conn: sqlite3.Connection) -> SettingsModel:
    return SettingsModel(
        sandbox_enabled=get_sandbox_enabled(conn),
        powermetrics_gpu_optin=get_powermetrics_optin(conn),
        provider_max_retries=get_max_retries(conn),
        thresholds=ThresholdDefaults(**get_threshold_defaults(conn)),
    )


@router.get("/settings")
def read_settings(request: Request) -> SettingsModel:
    conn = _conn(request)
    try:
        return _read_settings(conn)
    finally:
        conn.close()


@router.put("/settings")
def update_settings(request: Request, body: SettingsUpdate) -> SettingsModel:
    conn = _conn(request)
    try:
        if body.sandbox_enabled is not None:
            set_sandbox_enabled(conn, body.sandbox_enabled)
        if body.powermetrics_gpu_optin is not None:
            set_powermetrics_optin(conn, body.powermetrics_gpu_optin)
        if body.provider_max_retries is not None:
            set_max_retries(conn, body.provider_max_retries)
            # Mirror into env so the provider layer picks it up immediately (no restart). Read back
            # the persisted (clamped) value rather than the raw body so env matches the DB exactly.
            os.environ[_MAX_RETRIES_ENV] = str(get_max_retries(conn))
        if body.thresholds is not None:
            set_threshold_defaults(conn, body.thresholds.model_dump())
        return _read_settings(conn)
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
        # Models mode: an optional task instruction applies one system prompt to every candidate.
        # Empty/whitespace → leave None so model-compare runs keep byte-identical config_hashes.
        instruction = (body.system_prompt or "").strip()
        if instruction:
            return [c.model_copy(update={"system_prompt": instruction}) for c in base]
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


def _validate_bench_run(conn: sqlite3.Connection, rubric: Rubric, dataset: Dataset) -> None:
    """Enforce the bench binding integrity gate (spec §4): a bench dataset must bind a known corpus
    and cite only ids drawn from it. No-op for every non-bench rubric kind."""
    if rubric.kind != "bench":
        return
    try:
        validate_bench_binding(conn, dataset.corpus_id, dataset.examples)
    except BenchBindingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/runs")
def create_run(request: Request, body: RunRequest) -> ProofReport:
    conn = _conn(request)
    try:
        dataset = _resolve_dataset(conn, body)

        if not body.candidate_ids:
            raise HTTPException(status_code=400, detail="Select at least one candidate")
        candidates = _resolve_candidates(body)

        _meta = get_dataset_meta(conn, dataset.id)
        rubric = body.rubric or default_rubric_for(
            dataset, get_threshold_defaults(conn), check_hint=_meta.check_hint if _meta else None
        )
        if rubric.kind == "judge":
            try:
                build_judge(rubric)
            except (ValueError, KeyError) as exc:
                raise HTTPException(status_code=422, detail=f"Judge not available: {exc}")
        _validate_bench_run(conn, rubric, dataset)
        try:
            # The id/timestamp generation + run_proof call live in the shared core (also used by
            # the CLI). The route owns candidate fan-out, rubric resolution, and the judge check.
            report = execute_resolved(
                dataset=dataset,
                candidates=candidates,
                rubric=rubric,
                brief=body.brief,
                mode=body.mode,
            )
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
      - ``start``: total cells, examples-per-candidate, and the ordered candidate list.
      - ``progress``: a cumulative ``done`` count plus the just-finished cell's
        ``candidate_id`` + ``example_index`` and outcome. Candidates run CONCURRENTLY (cloud
        parallel, local serialized), so cells complete out of order — the client keys per-candidate
        progress on ``candidate_id``/``example_index``, never on the order frames arrive.
      - ``report``: the full, persisted :class:`ProofReport` (same shape as ``POST /runs``).
    Validation runs synchronously up front so a bad request is a normal 4xx, not an SSE error.
    """
    conn = _conn(request)
    try:
        dataset = _resolve_dataset(conn, body)
        threshold_overrides = get_threshold_defaults(conn)
        meta = get_dataset_meta(conn, dataset.id)
        # Resolve the rubric here so the bench binding gate can run while the connection is open
        # (validation is synchronous up front → a bad request is a normal 4xx, not an SSE error).
        rubric = body.rubric or default_rubric_for(
            dataset, threshold_overrides, check_hint=meta.check_hint if meta else None
        )
        _validate_bench_run(conn, rubric, dataset)
        gpu_optin = get_powermetrics_optin(conn)
    finally:
        conn.close()
    if not body.candidate_ids:
        raise HTTPException(status_code=400, detail="Select at least one candidate")
    candidates = _resolve_candidates(body)
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
        # Candidates run concurrently on worker threads; each completed cell is pushed onto a
        # thread-safe queue, and this generator (the request thread) drains it into SSE frames as
        # they arrive. A sentinel (None) marks the end. The worker also captures the assembled rows.
        cell_queue: queue.Queue[ResultRow | None] = queue.Queue()
        produced: dict[str, list[ResultRow]] = {}
        failure: list[BaseException] = []
        # Cooperative cancel: set when the client disconnects (the Stop button aborts the SSE fetch).
        # The worker checks it between examples and stops starting new ones; the report is then never
        # built or saved — a stopped run is DISCARDED, never persisted as a finished proof.
        cancel = threading.Event()

        # Live hardware telemetry for this run. Best-effort + isolated (reads only OS stats), so it
        # can never perturb run output or config_hash. Registered globally so /telemetry/stream can
        # read the latest sample; always cleared + stopped in the finally below.
        global _CURRENT_SAMPLER
        sampler = RunSampler(gpu_opt_in=gpu_optin)
        sampler.start()
        _CURRENT_SAMPLER = sampler

        def produce() -> None:
            try:
                produced["rows"] = run_matrix_concurrent(
                    dataset, candidates, rubric, on_cell=cell_queue.put, cancel=cancel
                )
            except BaseException as exc:  # surface to the consumer; never swallow silently
                failure.append(exc)
            finally:
                cell_queue.put(None)  # sentinel: production finished (even on error)

        worker = threading.Thread(target=produce, name="proof-run-stream", daemon=True)
        worker.start()

        # Everything below runs inside a try so that a client disconnect (Starlette throws
        # GeneratorExit into this generator at the next yield) diverts straight to the finally —
        # BEFORE the report is built or save_report runs. The finally signals cancel, drains the
        # worker, and always tears down the sampler (no stranded global, no leaked sampler thread).
        try:
            done = 0
            while True:
                row = cell_queue.get()
                if row is None:
                    break
                done += 1
                yield _sse(
                    {
                        "type": "progress",
                        "done": done,
                        "candidate_id": row.candidate_id,
                        "example_index": row.example_index,
                        "passed": row.passed,
                        "error": row.error is not None,
                        "cost": row.estimated_cost_usd + row.judge_cost_usd,
                    }
                )
            worker.join()
            telemetry = sampler.stop()
            _CURRENT_SAMPLER = None
            if failure:
                raise failure[0]
            rows = produced["rows"]
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
                host=_labeled_host_profile(),
                telemetry=telemetry,
            )
            write = connect(db_path)
            try:
                save_report(write, report)
            finally:
                write.close()
            yield _sse({"type": "report", "report": report.model_dump(mode="json")})
        finally:
            # Reached on normal completion, error, OR client disconnect (GeneratorExit). Tell the
            # worker to stop starting examples, let it drain to its sentinel, and roll up + clear the
            # sampler exactly like end-of-run so the gauges never strand "live".
            cancel.set()
            if _CURRENT_SAMPLER is sampler:
                try:
                    sampler.stop()  # idempotent; rolls up + joins the sampler thread
                except Exception:
                    pass
                _CURRENT_SAMPLER = None
            if worker.is_alive():
                # On disconnect the worker may still be inside an in-flight score_cell. cancel is set,
                # so it returns after that cell, hits its own finally (which puts the sentinel onto the
                # unbounded queue — never blocks), and exits. Bound the wait so a hung provider call
                # can't pin the request thread; the worker is a daemon, so a timeout here is benign.
                worker.join(timeout=10.0)

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


@router.get("/runs/latest")
def get_latest_run(request: Request) -> ProofReport | None:
    """The newest stored run, or null when there are none — the rail's at-rest hydrate.

    Read-only, mirrors ``/cost-summary``: a finished run is the only thing that moves it, so the
    rail refetches on a run's end. ``list_runs`` is newest-first and already drops un-picked quick
    drafts, so the first element is the latest receipt. Declared before ``/runs/{run_id}`` so the
    literal path wins over the parameterized one.
    """
    conn = _conn(request)
    try:
        runs = list_runs(conn)
        return runs[0] if runs else None
    finally:
        conn.close()


@router.get("/track-record")
def get_track_record(request: Request, dataset_id: str | None = None) -> list[TrackRecordGroup]:
    """Cross-run standings — pure rollup over past runs, one group per (dataset, rubric kind).

    Thin shell over the core ``track_record`` fn (ADR-0004 §3/§5): reads existing leaderboard
    fields only, re-runs no scoring, never touches ``config_hash``. ``dataset_id`` narrows to one
    dataset. Quick/unscored runs are excluded by the core fn.
    """
    conn = _conn(request)
    try:
        return track_record(list_runs(conn), dataset_id=dataset_id)
    finally:
        conn.close()


@router.get("/cost-summary")
def get_cost_summary(request: Request, window: Literal["today", "all"] = "today") -> CostRollup:
    """Cumulative spend across stored runs — eval/judge split + a cost/pass-rate trend series.

    Read-only rollup over persisted ``cost_summary`` fields (same hash-inert pattern as
    ``track_record``): re-runs no scoring, touches no ``config_hash`` or receipt byte.
    ``window=today`` keeps runs created on the current UTC date; ``window=all`` is cumulative.
    Drafts (un-picked quick-compare runs) are excluded by the core fn.
    """
    conn = _conn(request)
    try:
        return cost_rollup(list_runs(conn), window=window)
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
