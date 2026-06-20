"""FastAPI application factory for the Orionfold Proof local cockpit.

The API lives under ``/api``. The built Vite/React cockpit, when present, is served as a
single-page app from ``server/static`` (populated by ``scripts/build.sh`` at package-build
time). When the cockpit has not been built — e.g. a fresh dev checkout — a calm placeholder
page is served instead so ``orionfold up`` always responds.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from orionfold import __version__

SERVICE_NAME = "orionfold-proof"


def static_dir() -> Path:
    """Absolute path to the embedded cockpit build directory (may not exist yet)."""
    return Path(__file__).resolve().parent / "static"


def cockpit_is_built() -> bool:
    """True when a built SPA (index.html) is embedded and ready to serve."""
    return (static_dir() / "index.html").is_file()


_PLACEHOLDER_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Orionfold Proof</title>
    <style>
      :root { color-scheme: light dark; }
      body {
        margin: 0; min-height: 100vh; display: grid; place-items: center;
        font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
        background: #0b0f14; color: #e6edf3;
      }
      main { max-width: 34rem; padding: 2rem; text-align: center; }
      h1 { font-size: 1.4rem; letter-spacing: -0.01em; margin: 0 0 0.5rem; }
      p { color: #9fb0c0; margin: 0.5rem 0; }
      code {
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        background: #161b22; padding: 0.15rem 0.4rem; border-radius: 6px; color: #e6edf3;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Orionfold Proof</h1>
      <p>The cockpit has not been built yet.</p>
      <p>Run <code>pnpm --dir web dev</code> for live development, or
         <code>bash scripts/build.sh</code> to embed the built UI.</p>
      <p>The API is live at <code>/api/health</code>.</p>
    </main>
  </body>
</html>
"""


def create_app() -> FastAPI:
    """Build the FastAPI app: ``/api`` routes, then the cockpit (SPA or placeholder)."""
    app = FastAPI(title="Orionfold Proof", version=__version__)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME, "version": __version__}

    # Register API routes BEFORE the catch-all cockpit so they always win.
    if cockpit_is_built():
        # html=True serves index.html for "/" and unknown client-side routes.
        app.mount("/", StaticFiles(directory=static_dir(), html=True), name="cockpit")
    else:

        @app.get("/", response_class=HTMLResponse)
        def placeholder() -> str:
            return _PLACEHOLDER_HTML

    return app
