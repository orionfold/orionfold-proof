"""open_pack: reads dir + .zip packs, validates the manifest, fails loudly on bad input."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "licensing"
sys.path.insert(0, str(_FIXTURES))
import pack_factory as pf  # noqa: E402

from orionfold.licensing.pack import PackError, open_pack  # noqa: E402


def test_open_pack_dir_reads_all_artifacts(tmp_path: Path) -> None:
    pack = open_pack(pf.write_pack_dir(tmp_path))
    assert pack.manifest.pack_id == pf.PACK_ID
    assert pack.corpus is not None and pack.corpus.id == pf.CORPUS_ID
    assert pack.dataset is not None and pack.dataset.name == pf.DATASET_NAME
    assert pack.dataset.corpus_id == pf.CORPUS_ID
    assert pack.dataset.system_prompt  # carried
    assert pack.reference_receipt is not None
    assert pack.manifest.model is not None and pack.manifest.model.repo_id == pf.MODEL_REPO


def test_open_pack_zip_reads_all_artifacts(tmp_path: Path) -> None:
    pack = open_pack(pf.write_pack_zip(tmp_path))
    assert pack.manifest.pack_id == pf.PACK_ID
    assert pack.corpus is not None and pack.dataset is not None


def test_open_pack_minimal_no_receipt_no_model(tmp_path: Path) -> None:
    pack = open_pack(pf.write_pack_dir(tmp_path, include_receipt=False, include_model=False))
    assert pack.reference_receipt is None
    assert pack.manifest.model is None
    assert pack.corpus is not None and pack.dataset is not None


def test_missing_manifest_raises(tmp_path: Path) -> None:
    d = tmp_path / "empty"
    d.mkdir()
    with pytest.raises(PackError, match="no manifest.json"):
        open_pack(d)


def test_wrong_product_raises(tmp_path: Path) -> None:
    with pytest.raises(PackError, match="not orionfold-proof"):
        open_pack(pf.write_pack_dir(tmp_path, product="someone-else"))


def test_wrong_schema_raises(tmp_path: Path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    m = json.loads((pack / "manifest.json").read_text())
    m["schema"] = "bogus/v9"
    (pack / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(PackError, match="unexpected pack schema"):
        open_pack(pack)


def test_referenced_file_missing_raises(tmp_path: Path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    (pack / "dataset.json").unlink()
    with pytest.raises(PackError, match="references dataset"):
        open_pack(pack)


def test_malformed_artifact_raises(tmp_path: Path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    (pack / "corpus.json").write_text('{"id": 123}')  # missing required name, wrong type
    with pytest.raises(PackError, match="corpus"):
        open_pack(pack)
