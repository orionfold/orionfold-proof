"""Typer CLI for Orionfold Proof.

``orionfold up``  — serve the embedded cockpit + API (production-style, no reload).
``orionfold dev`` — run the API with auto-reload for backend development; the cockpit is
                    served separately by Vite (``pnpm --dir web dev``) proxying ``/api``.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer
import uvicorn
from pydantic import ValidationError

from orionfold import __version__
from orionfold.data.importers import DatasetParseError, ImportFormat, parse_dataset
from orionfold.domain.models import Dataset, ProofBrief, Rubric, RubricKind
from orionfold.proof import execute_run
from orionfold.providers.registry import UnknownCandidateError
from orionfold.receipts import export
from orionfold.storage.db import apply_migrations, connect, default_db_path
from orionfold.storage.repository import save_report

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
        # The CLI opens its own connection, so it must ensure the schema exists — the web app
        # applies migrations at startup, but the headless path has no such hook.
        conn = connect(default_db_path())
        try:
            apply_migrations(conn)
            save_report(conn, report)
        finally:
            conn.close()

    rendered = _FORMAT_RENDERERS[output_format](report)
    if out is not None:
        out.write_text(rendered, encoding="utf-8")
        typer.echo(f"Receipt written to {out}", err=True)
    else:
        typer.echo(rendered)


if __name__ == "__main__":
    app()
