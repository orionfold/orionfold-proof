#!/usr/bin/env bash
# Build the orionfold-proof wheel with the cockpit embedded.
#
# Ordering is a HARD requirement (ADR-0001 §3): compile web/dist -> copy into the package
# -> uv build. Run from the repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STATIC_DIR="src/orionfold/server/static"

echo "==> [1/4] Installing cockpit dependencies (pnpm)"
pnpm --dir web install --frozen-lockfile

echo "==> [2/4] Building cockpit (Vite) -> web/dist"
pnpm --dir web build

echo "==> [3/4] Embedding cockpit -> ${STATIC_DIR}"
rm -rf "$STATIC_DIR"
cp -r web/dist "$STATIC_DIR"
test -f "${STATIC_DIR}/index.html" || { echo "ERROR: cockpit build missing index.html" >&2; exit 1; }

echo "==> [4/4] Building wheel (uv build)"
uv build

echo "==> Done. Wheel(s) in dist/ — cockpit embedded from ${STATIC_DIR}"
