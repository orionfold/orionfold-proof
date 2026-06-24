"""Build the Advisor domain pack from a real stored Proof run (dev tooling, not shipped).

The Advisor pack is the first shippable paid pack: it lets a buyer **rerun the proven 18/21
governance-bench receipt** offline. The corpus (`ainative-field-notes`) and the bench dataset
(`advisor-curveball-v0.2`) already ship *bundled and auto-seeded* inside Proof, so the pack carries
ONLY the reference receipt + the Advisor-GGUF model pointer — the paid artifact is "rerun MY
receipt," not a re-shipment of the free seed.

Usage (operator, against the real local store)::

    uv run python scripts/build_advisor_pack.py --run run_0ff7975480e2

writes ``_packs/advisor-field-notes/`` (a pack dir) + ``_packs/advisor-field-notes.zip``. The
output dir is gitignored — a pack is a build artifact, like a field-note bundle.

This lives in ``scripts/`` (NOT the wheel): it imports the package to read a stored ``ProofReport``
and reuses the same pack shape ``open_pack`` validates. ``build_pack(report, out_dir, …)`` is the
testable core (takes a report, no DB) so ``tests/unit/test_build_advisor_pack.py`` can round-trip a
fixture report through ``open_pack`` + ``unlock`` without the real store.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from orionfold.domain.models import ProofReport

# The pack's identity. The pack_id is what a license entitlement (`pack:advisor-field-notes`) names;
# keep it stable — changing it would orphan every issued license.
PACK_ID = "advisor-field-notes"
PACK_NAME = "Advisor · ainative field-notes governance bench"
PACK_VERSION = "0.2.0"
MODEL_REPO_ID = "hf.co/Orionfold/Advisor-GGUF"
MODEL_DISPLAY_NAME = "Advisor (Corpus)"

# The reference run to ship by default (the M3 Max 18/21 governance-bench receipt).
DEFAULT_RUN_ID = "run_0ff7975480e2"
DEFAULT_OUT = Path("_packs")


@dataclass(frozen=True)
class BuildResult:
    pack_dir: Path
    zip_path: Path
    reference_run_id: str


def build_pack(
    report: ProofReport,
    out_dir: Path,
    *,
    pack_id: str = PACK_ID,
    name: str = PACK_NAME,
    version: str = PACK_VERSION,
    model_repo_id: str = MODEL_REPO_ID,
    model_display_name: str = MODEL_DISPLAY_NAME,
) -> BuildResult:
    """Assemble a receipt-only pack (manifest + reference-receipt.json) + its .zip.

    No corpus/dataset keys: those auto-seed for free. The reference receipt is the RAW ProofReport
    (``model_dump_json``) — NOT ``orionfold runs show --format json`` (that emits a wrapped receipt
    ``open_pack`` would reject)."""
    pack_dir = out_dir / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    (pack_dir / "reference-receipt.json").write_text(report.model_dump_json(), "utf-8")

    manifest = {
        "schema": "orionfold.pack/v1",
        "pack_id": pack_id,
        "name": name,
        "version": version,
        "product": "orionfold-proof",
        "reference_receipt": "reference-receipt.json",
        "model": {"repo_id": model_repo_id, "display_name": model_display_name},
    }
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), "utf-8")

    zip_path = out_dir / f"{pack_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(pack_dir.iterdir()):
            zf.write(f, f.name)

    return BuildResult(pack_dir=pack_dir, zip_path=zip_path, reference_run_id=report.run.id)


def _load_report(run_id: str) -> ProofReport:
    """Read a stored ProofReport from the real local store (main path, not used by tests)."""
    from orionfold.storage.db import apply_migrations, connect, default_db_path
    from orionfold.storage.repository import get_report

    conn = connect(default_db_path())
    try:
        apply_migrations(conn)
        report = get_report(conn, run_id)
    finally:
        conn.close()
    if report is None:
        raise SystemExit(f"no stored run {run_id!r} in {default_db_path()} — run the bench first")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Advisor domain pack from a stored run.")
    parser.add_argument("--run", default=DEFAULT_RUN_ID, help="stored run id to ship as the receipt")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output dir (gitignored)")
    args = parser.parse_args()

    report = _load_report(args.run)
    lb = report.leaderboard[0] if report.leaderboard else None
    result = build_pack(report, args.out)

    print(f"✓ Built {PACK_ID} pack")
    print(f"  dir: {result.pack_dir}")
    print(f"  zip: {result.zip_path}")
    print(f"  reference receipt: run {result.reference_run_id}", end="")
    if lb is not None:
        print(f" — {lb.pass_count}/{lb.total} ({lb.label})")
    else:
        print()
    print(f"  sign a license entitling 'pack:{PACK_ID}' (website), then `orionfold unlock`.")


if __name__ == "__main__":
    main()
