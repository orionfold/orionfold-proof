"""Typer CLI for Orionfold Proof.

``orionfold up``  — serve the embedded cockpit + API (production-style, no reload).
``orionfold dev`` — run the API with auto-reload for backend development; the cockpit is
                    served separately by Vite (``pnpm --dir web dev``) proxying ``/api``.
``orionfold run`` — run a proof headlessly and emit a receipt (the engineer/researcher path).
``orionfold dataset import|list`` — import and list datasets headlessly.
``orionfold runs list|show``      — inspect run history.
``orionfold track-record``        — cross-run standings per (dataset, rubric kind).
``orionfold field-note``          — export a publish-ready field note for one run.
``orionfold pull``                — pull an HF/GGUF model into Ollama so it's a candidate.
``orionfold codegen``             — regenerate the frontend's shared constants from the core.

Each workflow command is a thin shell over the reusable core (ADR-0004 §3): it opens a
local DB connection, calls a pure core/repository function, and renders. No shell
re-implements core logic.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, cast

import typer
import uvicorn
from pydantic import ValidationError

from orionfold import __version__
from orionfold.data.importers import DatasetParseError, ImportFormat, parse_dataset
from orionfold.domain.models import Dataset, ProofBrief, ProofReport, Rubric, RubricKind
from orionfold.proof import execute_run, track_record
from orionfold.providers.registry import UnknownCandidateError
from orionfold.receipts import build_field_note, export
from orionfold.storage.db import apply_migrations, connect, default_db_path
from orionfold.storage.settings import get_powermetrics_optin, set_powermetrics_optin
from orionfold.storage.repository import (
    BenchBindingError,
    DuplicateDatasetError,
    get_report,
    list_corpora,
    list_dataset_rows,
    list_runs,
    save_dataset,
    save_report,
    seed_corpora,
    upsert_corpus,
    validate_bench_binding,
)

if TYPE_CHECKING:
    from orionfold.catalog.models import CatalogModel

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Orionfold Proof — prove which AI is worth trusting.",
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

_APP_TARGET = "orionfold.server.app:create_app"


def _serve(host: str, port: int, reload: bool) -> None:
    uvicorn.run(_APP_TARGET, host=host, port=port, reload=reload, factory=True)


@contextmanager
def _with_conn() -> Iterator[sqlite3.Connection]:
    """Open the local DB, ensure the schema exists, and always close.

    The web app applies migrations at startup; the headless path has no such hook, so every
    CLI command that touches the DB ensures the schema itself. ``ORIONFOLD_DB`` (honored by
    ``default_db_path``) lets tests isolate the database.
    """
    conn = connect(default_db_path())
    try:
        apply_migrations(conn)
        seed_corpora(conn)  # bundled corpora are needed to validate any bench dataset binding
        yield conn
    finally:
        conn.close()


@app.command()
def up(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind."),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind."),
) -> None:
    """Serve the cockpit and API at http://localhost:8787 (flagship shortcut)."""
    typer.echo(f"Orionfold Proof v{__version__} → http://{host}:{port}")
    _serve(host=host, port=port, reload=False)


@app.command()
def dev(
    host: str = typer.Option(DEFAULT_HOST, help="Host to bind."),
    port: int = typer.Option(DEFAULT_PORT, help="Port to bind."),
) -> None:
    """Run the API with auto-reload (run `pnpm --dir web dev` for the cockpit)."""
    typer.echo(f"Orionfold Proof v{__version__} (dev, reload) → http://{host}:{port}")
    _serve(host=host, port=port, reload=True)


@app.command()
def codegen() -> None:
    """Regenerate the frontend's shared constants from the canonical Python core.

    Writes ``web/src/features/proof/thresholds.generated.ts`` from ``DEFAULT_THRESHOLDS``.
    A backend test asserts the committed file matches, so run this after editing the map.
    """
    from orionfold.codegen import write_generated_files

    for path in write_generated_files():
        typer.echo(f"Wrote {path}")


_FORMAT_RENDERERS = {
    "json": export.to_json,
    "markdown": export.to_markdown,
    "html": export.to_html,
}

_EXT_TO_FORMAT: dict[str, ImportFormat] = {
    ".jsonl": "jsonl",
    ".csv": "csv",
    ".md": "markdown",
    ".markdown": "markdown",
}


@app.command()
def run(
    dataset: Path = typer.Option(..., "--dataset", help="Path to a dataset file (.jsonl/.csv/.md)."),
    candidates: str = typer.Option(
        ..., "--candidates", help="Comma-separated candidate ids, e.g. 'mock_good,mock_bad'."
    ),
    rubric_kind: str | None = typer.Option(
        None, "--rubric", help="Scoring kind (exact/contains/similarity/keypoint). Default: auto."
    ),
    output_format: str = typer.Option(
        "markdown", "--format", help="Receipt format: markdown | json | html."
    ),
    out: Path | None = typer.Option(None, "--out", help="Write the receipt here (default: stdout)."),
    no_save: bool = typer.Option(False, "--no-save", help="Do not persist the run to the local DB."),
) -> None:
    """Run a proof headlessly and emit a receipt (the engineer/researcher path)."""
    if output_format not in _FORMAT_RENDERERS:
        typer.echo(f"Unknown --format '{output_format}' (use markdown|json|html).", err=True)
        raise typer.Exit(code=2)

    # Load + parse the dataset by file extension.
    fmt = _EXT_TO_FORMAT.get(dataset.suffix.lower())
    if fmt is None:
        typer.echo(f"Unsupported dataset extension '{dataset.suffix}'.", err=True)
        raise typer.Exit(code=2)
    try:
        parsed = parse_dataset(dataset.read_text(encoding="utf-8"), fmt)
    except (OSError, DatasetParseError) as exc:
        typer.echo(f"Could not read dataset: {exc}", err=True)
        raise typer.Exit(code=1)

    ds = Dataset(id=dataset.stem, name=dataset.stem, examples=parsed.examples)
    candidate_ids = [c.strip() for c in candidates.split(",") if c.strip()]
    brief = ProofBrief(
        task_name=dataset.stem,
        decision_question=f"Which candidate is worth trusting on {dataset.stem}?",
    )
    rubric: Rubric | None = None
    if rubric_kind is not None:
        try:
            rubric = Rubric(kind=cast(RubricKind, rubric_kind))
        except ValidationError:
            typer.echo(
                f"Unknown --rubric '{rubric_kind}' "
                "(use exact/contains/similarity/keypoint/judge).",
                err=True,
            )
            raise typer.Exit(code=2)

    try:
        report = execute_run(dataset=ds, candidate_ids=candidate_ids, brief=brief, rubric=rubric)
    except UnknownCandidateError as exc:
        typer.echo(f"Candidate error: {exc}", err=True)
        raise typer.Exit(code=1)

    if not no_save:
        with _with_conn() as conn:
            save_report(conn, report)

    rendered = _FORMAT_RENDERERS[output_format](report)
    if out is not None:
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"Receipt written to {out}", err=True)
    else:
        typer.echo(rendered)


# ── dataset import|list ────────────────────────────────────────────────────────────────────

dataset_app = typer.Typer(no_args_is_help=True, help="Import and list local datasets.")
app.add_typer(dataset_app, name="dataset")


@dataset_app.command("import")
def dataset_import(
    path: Path = typer.Argument(..., help="Dataset file to import (.jsonl/.csv/.md)."),
    name: str | None = typer.Option(None, "--name", help="Dataset name (default: filename)."),
    description: str = typer.Option("", "--description", help="Optional description."),
    check_hint: str | None = typer.Option(
        None, "--check-hint", help="Scoring hint: exact | contains | numeric | eyeball."
    ),
    source: str = typer.Option("imported", "--source", help="Provenance label for the card."),
    corpus: str | None = typer.Option(
        None, "--corpus", help="Bind a bench dataset to a corpus id (validates citations ⊆ corpus)."
    ),
) -> None:
    """Parse a file and freeze it into a new local dataset (re-parsed as the source of truth)."""
    fmt = _EXT_TO_FORMAT.get(path.suffix.lower())
    if fmt is None:
        typer.echo(f"Unsupported dataset extension '{path.suffix}'.", err=True)
        raise typer.Exit(code=2)
    try:
        parsed = parse_dataset(path.read_text(encoding="utf-8"), fmt)
    except (OSError, DatasetParseError) as exc:
        typer.echo(f"Could not read dataset: {exc}", err=True)
        raise typer.Exit(code=1)

    with _with_conn() as conn:
        if corpus is not None:
            # A bench binding must validate before the row is written: known corpus, cited ids ⊆ it.
            try:
                validate_bench_binding(conn, corpus, parsed.examples)
            except BenchBindingError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(code=2)
        try:
            created = save_dataset(
                conn,
                name or path.stem,
                description,
                parsed.examples,
                source=source,
                check_hint=check_hint,
                created_at=_now_iso(),
                corpus_id=corpus,
            )
        except DuplicateDatasetError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1)
        except ValueError as exc:  # blank name, etc.
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2)

    typer.echo(f"Imported '{created.name}' ({created.id}) — {len(created.examples)} examples.")


@dataset_app.command("list")
def dataset_list() -> None:
    """List local datasets with their example counts and provenance."""
    with _with_conn() as conn:
        rows = list_dataset_rows(conn)
    if not rows:
        typer.echo("No datasets yet. Import one with `orionfold dataset import <file>`.")
        return
    typer.echo(f"{'ID':<24} {'EXAMPLES':>8}  {'HINT':<10} {'SOURCE':<22} NAME")
    for ds, meta in rows:
        marker = " (sample)" if meta.is_sample else ""
        typer.echo(
            f"{ds.id:<24} {len(ds.examples):>8}  {(meta.check_hint or '—'):<10} "
            f"{meta.source[:22]:<22} {ds.name}{marker}"
        )


# ── corpus list|import ─────────────────────────────────────────────────────────────────────

corpus_app = typer.Typer(no_args_is_help=True, help="Manage governed corpora for bench datasets.")
app.add_typer(corpus_app, name="corpus")


@corpus_app.command("list")
def corpus_list() -> None:
    """List local corpora and how many source ids each governs."""
    with _with_conn() as conn:
        corpora = list_corpora(conn)
    if not corpora:
        typer.echo("No corpora yet. Import one with `orionfold corpus import <file.json>`.")
        return
    typer.echo(f"{'ID':<28} {'SOURCES':>8}  NAME")
    for c in corpora:
        typer.echo(f"{c.id:<28} {len(c.source_ids):>8}  {c.name}")


@corpus_app.command("import")
def corpus_import(
    path: Path = typer.Argument(..., help="Corpus manifest JSON: {id, name, description, source_ids}."),
) -> None:
    """Register (or replace) a corpus from a JSON manifest so a bench dataset can bind to it."""
    from orionfold.domain.models import Corpus

    try:
        corpus = Corpus.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        typer.echo(f"Could not read corpus manifest: {exc}", err=True)
        raise typer.Exit(code=1)
    with _with_conn() as conn:
        upsert_corpus(conn, corpus)
    typer.echo(f"Registered corpus '{corpus.name}' ({corpus.id}) — {len(corpus.source_ids)} sources.")


# ── runs list|show ─────────────────────────────────────────────────────────────────────────

runs_app = typer.Typer(no_args_is_help=True, help="Inspect run history.")
app.add_typer(runs_app, name="runs")


@runs_app.command("list")
def runs_list() -> None:
    """List stored runs, newest first, with the recommended winner and pass rate."""
    with _with_conn() as conn:
        reports = list_runs(conn)
    if not reports:
        typer.echo("No runs yet. Run a proof with `orionfold run …`.")
        return
    typer.echo(f"{'RUN ID':<28} {'DATASET':<22} {'RUBRIC':<10} {'WINNER':<18} CREATED")
    for report in sorted(reports, key=lambda r: r.run.created_at, reverse=True):
        winner = _recommended_label(report)
        typer.echo(
            f"{report.run.id:<28} {report.run.dataset_name[:22]:<22} "
            f"{report.run.rubric.kind:<10} {winner[:18]:<18} {report.run.created_at}"
        )


@runs_app.command("show")
def runs_show(
    run_id: str = typer.Argument(..., help="The run id (see `orionfold runs list`)."),
    output_format: str | None = typer.Option(
        None, "--format", help="Dump the full receipt instead: markdown | json | html."
    ),
) -> None:
    """Show a stored run — a verdict summary, or the full receipt with --format."""
    with _with_conn() as conn:
        report = get_report(conn, run_id)
    if report is None:
        typer.echo(f"Unknown run '{run_id}'.", err=True)
        raise typer.Exit(code=1)

    if output_format is not None:
        if output_format not in _FORMAT_RENDERERS:
            typer.echo(f"Unknown --format '{output_format}' (use markdown|json|html).", err=True)
            raise typer.Exit(code=2)
        typer.echo(_FORMAT_RENDERERS[output_format](report))
        return

    run = report.run
    typer.echo(f"{run.id}  ·  {run.dataset_name}  ·  {run.rubric.kind}  ·  {run.created_at}")
    typer.echo(f"Decision: {run.brief.decision_question}")
    typer.echo(f"{'CANDIDATE':<24} {'PASS':>9}  {'AVG':>5}  {'COST':>9}")
    for e in report.leaderboard:
        crown = "★ " if e.recommended else "  "
        pct = f"{e.pass_rate * 100:.0f}% ({e.pass_count}/{e.total})"
        typer.echo(
            f"{crown}{e.label[:22]:<22} {pct:>9}  {e.avg_score:>5.2f}  "
            f"${e.total_estimated_cost_usd:>8.4f}"
        )
    typer.echo(f"Run cost: ${report.cost_summary.total_cost_usd:.4f}")


# ── track-record ───────────────────────────────────────────────────────────────────────────


@app.command("track-record")
def track_record_cmd(
    dataset: str | None = typer.Option(
        None, "--dataset", help="Limit to one dataset id (see `orionfold dataset list`)."
    ),
) -> None:
    """Cross-run standings, grouped per (dataset, rubric kind) — the comparable slices."""
    with _with_conn() as conn:
        reports = list_runs(conn)
    groups = track_record(reports, dataset_id=dataset)
    if not groups:
        typer.echo("No comparable runs yet. Run a few proofs, then re-check.")
        return
    for g in groups:
        typer.echo(f"\n{g.dataset_name}  ({g.rubric_kind})  —  {g.runs} run(s)")
        typer.echo(f"  {'CANDIDATE':<22} {'RUNS':>4} {'PASS%':>6} {'AVG $':>9} {'WON':>4}")
        for e in g.entries:
            typer.echo(
                f"  {e.label[:20]:<22} {e.runs:>4} {e.pass_rate * 100:>5.0f}% "
                f"${e.avg_cost_usd:>8.4f} {e.times_recommended:>4}"
            )


# ── field-note ─────────────────────────────────────────────────────────────────────────────


@app.command("field-note")
def field_note_cmd(
    run_id: str = typer.Argument(..., help="The run id (see `orionfold runs list`)."),
    out: Path | None = typer.Option(
        None, "--out", help="Write the field note here (default: stdout)."
    ),
) -> None:
    """Export a publish-ready field note (receipt evidence + figures + a narrative stub)."""
    with _with_conn() as conn:
        report = get_report(conn, run_id)
    if report is None:
        typer.echo(f"Unknown run '{run_id}'.", err=True)
        raise typer.Exit(code=1)

    note = build_field_note(report)
    if out is not None:
        out.write_text(note, encoding="utf-8")
        typer.echo(f"Field note written to {out}", err=True)
    else:
        typer.echo(note)


# ── pull ───────────────────────────────────────────────────────────────────────────────────


def _overlay_model_for(repo_id: str) -> "CatalogModel":
    """The CatalogModel to record for a pulled ``repo_id``.

    Prefer the curated catalog entry (so a roster model keeps its display name/tier); otherwise
    synthesize a generic local entry. The model ``id`` is the ``hf.co/...`` name Ollama runs it
    under — i.e. equal to ``repo_id`` — so the run path sends it straight to ``/api/chat``.
    """
    from orionfold.catalog import load_catalog
    from orionfold.catalog.models import CatalogModel

    for provider in load_catalog().providers:
        for m in provider.models:
            if m.repo_id == repo_id:
                return m
    name = repo_id.removeprefix("hf.co/").removeprefix("huggingface.co/")
    return CatalogModel(
        id=repo_id,
        display_name=name.rsplit("/", 1)[-1],
        family="hf",
        tier="balanced",
        cost_class="free",
        pricing=None,
        repo_id=repo_id,
    )


def _fmt_bytes(n: int) -> str:
    gb = n / 1e9
    return f"{gb:.1f} GB" if gb >= 1 else f"{n / 1e6:.0f} MB"


@app.command()
def pull(
    repo_id: str = typer.Argument(
        ..., help="HF GGUF repo, e.g. hf.co/Orionfold/Saul-7B-Instruct-v1-GGUF."
    ),
) -> None:
    """Pull an HF/GGUF model into Ollama so it becomes a selectable candidate.

    Streams Ollama's local pull (which fetches the GGUF from HuggingFace); on success records
    the model in ``~/.orionfold/models.json`` so the cockpit and CLI list it as first-class.
    """
    from orionfold.catalog.overlay import add_to_overlay
    from orionfold.providers.http import ProviderError
    from orionfold.providers.ollama_pull import pull_model, resolve_host

    host = resolve_host()
    last = ""
    try:
        for status in pull_model(host, repo_id):
            if status.completed is not None and status.total:
                pct = status.completed / status.total * 100
                line = (
                    f"{status.status} {pct:.0f}% "
                    f"({_fmt_bytes(status.completed)}/{_fmt_bytes(status.total)})"
                )
            else:
                line = status.status
            if line != last:
                typer.echo(line, err=True)
                last = line
    except ProviderError as exc:
        typer.echo(f"Pull failed: {exc}", err=True)
        raise typer.Exit(code=1)

    add_to_overlay(_overlay_model_for(repo_id))
    typer.echo(f"✓ {repo_id} pulled — now a selectable candidate.")


@app.command()
def unlock(
    pack: Path = typer.Argument(..., help="Path to a domain pack (a directory or .zip)."),
    license: Path | None = typer.Option(
        None,
        "--license",
        help="License file (default: ~/.orionfold/license, or $ORIONFOLD_LICENSE).",
    ),
    license_url: str | None = typer.Option(
        None,
        "--license-url",
        help="HTTPS signed-URL to download the license (the one the purchase email sends).",
    ),
) -> None:
    """Install a licensed domain pack offline so its dataset + reference receipt become selectable.

    Verifies the Ed25519-signed license locally (no phone-home), checks it entitles this pack, then
    installs the pack's corpus, dataset, reference receipt, and model pointer into the local store.
    Pass `--license-url` to download the license from the signed URL in your purchase email, or
    `--license` to point at a file you already saved. Re-running is a safe no-op. Every failure exits
    non-zero with a fixable message."""
    from orionfold.licensing.install import install_pack
    from orionfold.licensing.license import (
        LicenseError,
        fetch_license,
        load_license,
        load_license_from_doc,
    )
    from orionfold.licensing.pack import PackError, open_pack

    if license is not None and license_url is not None:
        typer.echo(
            "Pass either --license <file> or --license-url <url>, not both.", err=True
        )
        raise typer.Exit(code=2)

    try:
        if license_url is not None:
            lic = load_license_from_doc(fetch_license(license_url))
        else:
            lic = load_license(license)
    except LicenseError as exc:
        typer.echo(f"License error: {exc}", err=True)
        raise typer.Exit(code=2)

    try:
        opened = open_pack(pack)
    except PackError as exc:
        typer.echo(f"Pack error: {exc}", err=True)
        raise typer.Exit(code=2)

    if not lic.unlocks_pack(opened.manifest.pack_id):
        typer.echo(
            f"License {lic.license_id} does not unlock the '{opened.manifest.pack_id}' pack — "
            "it carries neither product ownership (Orionfold Proof) nor a grant for this pack "
            f"(entitlements: {', '.join(lic.entitlements) or 'none'}).",
            err=True,
        )
        raise typer.Exit(code=3)

    try:
        with _with_conn() as conn:
            result = install_pack(conn, opened)
    except Exception as exc:  # noqa: BLE001 — surface install/binding failures as a clean exit
        typer.echo(f"Install failed: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"✓ Unlocked {result.pack_name}")
    if result.dataset_name:
        verb = "installed" if result.dataset_was_new else "already present"
        typer.echo(f"  dataset: {result.dataset_name} ({verb})")
    if result.model_repo_id:
        typer.echo(f"  model:   {result.model_repo_id} (pull it if not already local)")
    if result.reference_run_id:
        typer.echo("  Select the dataset in the cockpit and rerun the reference receipt.")


def _now_iso() -> str:
    """Wall-clock ISO timestamp for the imported dataset card (display metadata only)."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _recommended_label(report: ProofReport) -> str:
    """The recommended candidate's label for a run, or a calm absence."""
    for e in report.leaderboard:
        if e.recommended:
            return e.label
    return "no clear winner"


gpu_app = typer.Typer(
    no_args_is_help=True,
    help="Enable, check, or disable Apple-Silicon GPU telemetry (macOS).",
)
app.add_typer(gpu_app, name="gpu")


@gpu_app.command("enable")
def gpu_enable() -> None:
    """Set up passwordless GPU telemetry by installing a powermetrics-only sudoers rule.

    macOS never shows a GUI permission prompt for the sampler (the live read is non-interactive
    ``sudo -n``), so GPU utilization stays "unavailable" until a NOPASSWD rule exists. This writes a
    drop-in scoped strictly to ``/usr/bin/powermetrics`` (validated with ``visudo``), prompting for
    your password once. Undo anytime with ``orionfold gpu disable``.
    """
    from orionfold.telemetry import gpu_setup

    if not gpu_setup.is_macos():
        typer.echo("GPU telemetry setup is macOS-only (Linux/NVIDIA needs no sudo).", err=True)
        raise typer.Exit(code=2)
    if not gpu_setup.powermetrics_present():
        typer.echo(f"powermetrics not found at {gpu_setup.POWERMETRICS_BIN}.", err=True)
        raise typer.Exit(code=2)

    typer.echo(f"Installing sudoers rule (scope: {gpu_setup.POWERMETRICS_BIN}) — sudo may prompt once.")
    try:
        gpu_setup.install_sudoers()
    except gpu_setup.GpuSetupError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    with _with_conn() as conn:
        set_powermetrics_optin(conn, True)

    reachable = gpu_setup.probe_powermetrics()
    typer.echo("✓ GPU telemetry enabled.")
    if reachable:
        typer.echo("  The cockpit GPU cell now shows live idle %.")
    else:
        typer.echo("  Rule installed, but the probe did not succeed yet — try `orionfold gpu status`.")


@gpu_app.command("status")
def gpu_status() -> None:
    """Show whether GPU telemetry is set up: the opt-in, the sudoers rule, and live reachability."""
    from orionfold.telemetry import gpu_setup

    with _with_conn() as conn:
        opt_in = get_powermetrics_optin(conn)
    rule = gpu_setup.sudoers_rule_present()
    reachable = gpu_setup.probe_powermetrics()

    typer.echo(f"Opt-in:               {'on' if opt_in else 'off'}")
    typer.echo(f"Sudoers rule:         {'present' if rule else 'absent'}")
    typer.echo(f"powermetrics reachable: {'yes' if reachable else 'no'}")
    if opt_in and not reachable:
        typer.echo("Needs setup — run `orionfold gpu enable` to install passwordless access.")


@gpu_app.command("disable")
def gpu_disable() -> None:
    """Turn GPU telemetry off and remove the powermetrics sudoers rule (idempotent)."""
    from orionfold.telemetry import gpu_setup

    gpu_setup.remove_sudoers()
    with _with_conn() as conn:
        set_powermetrics_optin(conn, False)
    typer.echo("✓ GPU telemetry disabled.")


if __name__ == "__main__":
    app()
