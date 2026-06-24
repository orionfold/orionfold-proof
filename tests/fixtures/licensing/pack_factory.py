"""Build a small, valid domain pack + a dev-signed license on disk — shared by pack/install/e2e tests.

Everything is assembled at runtime with the published throwaway dev key (no secret stored, no
network), so the full unlock path is exercised keyless.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, Corpus, ProofBrief, Rubric
from orionfold.licensing import license as lic
from orionfold.proof.engine import run_proof

PACK_ID = "test-field-notes"
CORPUS_ID = "test-corpus"
DATASET_NAME = "Test Field Notes Bench"
MODEL_REPO = "hf.co/Orionfold/Advisor-GGUF"

# The throwaway dev key (published seed = bytes(range(32))) — NEVER signs a real license.
DEV_KEY_ID = "of-license-dev-2026-06"
DEV_SEED_B64 = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="


def _reference_report() -> dict:
    """A real ProofReport (mock_good, keyless) → the pack's reference receipt."""
    report = run_proof(
        run_id="run_packref",
        created_at="2026-06-24T12:00:00Z",
        brief=ProofBrief(task_name="pack ref", decision_question="q"),
        dataset=load_dataset("investment-memo-summarization"),
        candidates=[Candidate(id="mock_good", label="Good", provider_id="mock_good")],
        rubric=Rubric(),
    )
    return json.loads(report.model_dump_json())


def _corpus() -> dict:
    return Corpus(
        id=CORPUS_ID, name="Test corpus", description="for tests", source_ids=["src_a", "src_b"]
    ).model_dump()


def _dataset() -> dict:
    """A tiny bench-shaped dataset bound to the pack corpus, carrying a system prompt."""
    return {
        "id": "test-field-notes-bench",
        "name": DATASET_NAME,
        "description": "a tiny bench for tests",
        "corpus_id": CORPUS_ID,
        "system_prompt": "Cite exactly one source id from the retrieved set.",
        "examples": [
            {"input_text": "q1", "expected_text": "a1"},
            {"input_text": "q2", "expected_text": "a2"},
        ],
    }


def write_pack_dir(
    root: Path,
    *,
    include_receipt: bool = True,
    include_model: bool = True,
    product: str = "orionfold-proof",
    pack_id: str = PACK_ID,
) -> Path:
    """Write a pack as a directory. Returns the pack dir."""
    pack = root / "pack"
    pack.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "orionfold.pack/v1",
        "pack_id": pack_id,
        "name": "Test · field notes",
        "version": "0.1.0",
        "product": product,
        "corpus": "corpus.json",
        "dataset": "dataset.json",
    }
    (pack / "corpus.json").write_text(json.dumps(_corpus()), "utf-8")
    (pack / "dataset.json").write_text(json.dumps(_dataset()), "utf-8")
    if include_receipt:
        manifest["reference_receipt"] = "reference-receipt.json"
        (pack / "reference-receipt.json").write_text(json.dumps(_reference_report()), "utf-8")
    if include_model:
        manifest["model"] = {"repo_id": MODEL_REPO, "display_name": "Advisor (Corpus)"}
    (pack / "manifest.json").write_text(json.dumps(manifest), "utf-8")
    return pack


def write_pack_zip(root: Path, **kw) -> Path:
    """Write a pack as a .zip. Returns the .zip path."""
    src = write_pack_dir(root / "_zsrc", **kw)
    zpath = root / "pack.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for f in src.iterdir():
            zf.write(f, f.name)
    return zpath


def write_license(
    path: Path,
    *,
    pack_ids: list[str] | None = None,
    own_product: bool = False,
    not_before: str = "2026-06-01T00:00:00Z",
    expires_at: str = "2027-06-01T00:00:00Z",
    key_id: str = DEV_KEY_ID,
    seed_b64: str = DEV_SEED_B64,
) -> Path:
    """Write a dev-signed license. Returns the license path.

    ``own_product=True`` writes a product-ownership license (``product:orionfold-proof``) — the real
    buying intent, which unlocks any included pack. Otherwise it writes per-pack ``pack:<id>`` grants
    for ``pack_ids`` (default: the test pack) — the à-la-carte path.
    """
    ents = [lic.pack_entitlement(p) for p in (pack_ids if pack_ids is not None else [PACK_ID])]
    if own_product:
        ents.append(lic.PRODUCT_ENTITLEMENT)
    payload = {
        "schema": "orionfold.license/v1",
        "license_id": "lic_test",
        "product": "orionfold-proof",
        "issued_to": {"name": "Test", "email": "t@example.com", "org": "Acme"},
        "issued_at": not_before,
        "not_before": not_before,
        "expires_at": expires_at,
        "seats": 1,
        "entitlements": ents,
    }
    doc = {
        "payload": payload,
        "signature": {
            "alg": "ed25519",
            "key_id": key_id,
            "value": lic.sign_payload(payload, seed_b64),
        },
    }
    path.write_text(json.dumps(doc), "utf-8")
    return path
