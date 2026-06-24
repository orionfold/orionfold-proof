"""install_pack: lands a pack's artifacts, is idempotent, and never moves a frozen config_hash."""

from __future__ import annotations

import sys
from pathlib import Path

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, ProofBrief, Rubric
from orionfold.licensing.install import install_pack
from orionfold.licensing.pack import open_pack
from orionfold.proof.engine import run_proof
from orionfold.storage.db import apply_migrations, connect
from orionfold.storage.repository import (
    get_corpus,
    get_dataset,
    get_report,
    list_dataset_rows,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "licensing"
sys.path.insert(0, str(_FIXTURES))
import pack_factory as pf  # noqa: E402


def _conn():
    conn = connect(":memory:")
    apply_migrations(conn)
    return conn


def _mock_matrix_hash() -> str:
    """The canonical mock-matrix config_hash (467ddd96c9a5 family) — recomputed, not hardcoded."""
    report = run_proof(
        run_id="run_h",
        created_at="2026-06-24T00:00:00Z",
        brief=ProofBrief(task_name="t", decision_question="q"),
        dataset=load_dataset("investment-memo-summarization"),
        candidates=[Candidate(id="mock_good", label="g", provider_id="mock_good")],
        rubric=Rubric(threshold=0.8),
    )
    return report.run.config_hash


def test_install_lands_corpus_dataset_receipt_and_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))
    conn = _conn()
    pack = open_pack(pf.write_pack_dir(tmp_path))
    result = install_pack(conn, pack)

    assert result.pack_id == pf.PACK_ID
    assert result.dataset_was_new is True
    # corpus + dataset + reference receipt are all in the store and selectable
    assert get_corpus(conn, pf.CORPUS_ID) is not None
    ds = get_dataset(conn, "test-field-notes-bench")
    assert ds is not None and ds.corpus_id == pf.CORPUS_ID and ds.system_prompt
    assert any(d.id == "test-field-notes-bench" for d, _ in list_dataset_rows(conn))
    assert result.reference_run_id is not None
    assert get_report(conn, result.reference_run_id) is not None
    # model pointer recorded in the overlay
    from orionfold.catalog.overlay import load_overlay

    assert any(m.repo_id == pf.MODEL_REPO for m in load_overlay())


def test_install_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))
    conn = _conn()
    pack = open_pack(pf.write_pack_dir(tmp_path))

    first = install_pack(conn, pack)
    second = install_pack(conn, pack)
    assert first.dataset_was_new is True
    assert second.dataset_was_new is False  # re-unlock is a no-op
    # exactly one dataset row, one corpus, one overlay entry
    rows = [d for d, _ in list_dataset_rows(conn) if d.id == "test-field-notes-bench"]
    assert len(rows) == 1
    from orionfold.catalog.overlay import load_overlay

    assert len([m for m in load_overlay() if m.repo_id == pf.MODEL_REPO]) == 1


def test_install_does_not_move_mock_matrix_hash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))
    before = _mock_matrix_hash()
    conn = _conn()
    install_pack(conn, open_pack(pf.write_pack_dir(tmp_path)))
    after = _mock_matrix_hash()
    assert before == after  # install writes rows only — never on a config_hash path


def test_minimal_pack_installs_without_receipt_or_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))
    conn = _conn()
    pack = open_pack(pf.write_pack_dir(tmp_path, include_receipt=False, include_model=False))
    result = install_pack(conn, pack)
    assert result.reference_run_id is None
    assert result.model_repo_id is None
    assert get_dataset(conn, "test-field-notes-bench") is not None
