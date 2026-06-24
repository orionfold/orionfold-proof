"""The Advisor-pack builder: a receipt-only pack round-trips through open_pack + unlock.

Drives ``scripts/build_advisor_pack.build_pack`` with a fixture ``ProofReport`` (no real DB), then
verifies the assembled pack opens, carries only the reference receipt (corpus/dataset auto-seed for
free), and installs via the entitlement-gated CLI with a dev-signed license — secret-free.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from typer.testing import CliRunner

from orionfold.cli import app
from orionfold.domain.models import Candidate, ProofBrief, Rubric
from orionfold.licensing.pack import open_pack
from orionfold.proof.engine import run_proof

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import build_advisor_pack as bap  # noqa: E402

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "licensing"
sys.path.insert(0, str(_FIXTURES))
import pack_factory as pf  # noqa: E402

runner = CliRunner()

_SECRET_PATTERNS = [r"sk-[A-Za-z0-9]{20,}", r"AIza[0-9A-Za-z_\-]{20,}", r"ORIONFOLD_LICENSE"]


def _fixture_report():
    """A real (keyless, mock_good) ProofReport standing in for the stored Advisor run."""
    from orionfold.data import load_dataset

    return run_proof(
        run_id="run_packref_test",
        created_at="2026-06-24T12:00:00Z",
        brief=ProofBrief(task_name="advisor pack ref", decision_question="q"),
        dataset=load_dataset("investment-memo-summarization"),
        candidates=[Candidate(id="mock_good", label="Good", provider_id="mock_good")],
        rubric=Rubric(),
    )


def test_build_pack_writes_receipt_only(tmp_path) -> None:
    report = _fixture_report()
    result = bap.build_pack(report, tmp_path)

    manifest = json.loads((result.pack_dir / "manifest.json").read_text("utf-8"))
    assert manifest["pack_id"] == bap.PACK_ID
    assert manifest["product"] == "orionfold-proof"
    assert manifest["reference_receipt"] == "reference-receipt.json"
    assert manifest["model"]["repo_id"] == bap.MODEL_REPO_ID
    # Receipt-only: corpus/dataset auto-seed for free, so the pack must NOT re-ship them.
    assert "corpus" not in manifest
    assert "dataset" not in manifest
    assert (result.pack_dir / "reference-receipt.json").is_file()
    assert result.zip_path.is_file()


def test_built_pack_opens_and_carries_the_receipt(tmp_path) -> None:
    report = _fixture_report()
    result = bap.build_pack(report, tmp_path)

    opened = open_pack(result.pack_dir)
    assert opened.manifest.pack_id == bap.PACK_ID
    assert opened.corpus is None and opened.dataset is None
    assert opened.reference_receipt is not None
    assert opened.reference_receipt.run.id == report.run.id


def test_built_zip_opens_too(tmp_path) -> None:
    result = bap.build_pack(_fixture_report(), tmp_path)
    opened = open_pack(result.zip_path)
    assert opened.reference_receipt is not None


def test_unlock_installs_the_built_pack(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))

    result = bap.build_pack(_fixture_report(), tmp_path)
    lic = pf.write_license(tmp_path / "license", pack_ids=[bap.PACK_ID])

    out = runner.invoke(app, ["unlock", str(result.pack_dir), "--license", str(lic)])
    assert out.exit_code == 0, out.stdout
    assert "Unlocked" in out.stdout
    assert "rerun the reference receipt" in out.stdout
    assert bap.MODEL_REPO_ID in out.stdout  # the model pointer is reported
    for pat in _SECRET_PATTERNS:
        assert not re.search(pat, out.stdout), pat


def test_built_pack_needs_the_matching_entitlement(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))

    result = bap.build_pack(_fixture_report(), tmp_path)
    lic = pf.write_license(tmp_path / "license", pack_ids=["some-other-pack"])
    out = runner.invoke(app, ["unlock", str(result.pack_dir), "--license", str(lic)])
    assert out.exit_code == 3
    assert "does not entitle" in out.stderr
