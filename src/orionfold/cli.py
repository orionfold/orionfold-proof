"""Typer CLI for Orionfold Proof.

``orionfold up``  — serve the embedded cockpit + API (production-style, no reload).
``orionfold dev`` — run the API with auto-reload for backend development; the cockpit is
                    served separately by Vite (``pnpm --dir web dev``) proxying ``/api``.
"""

from __future__ import annotations

import typer
import uvicorn

from orionfold import __version__

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


if __name__ == "__main__":
    app()
