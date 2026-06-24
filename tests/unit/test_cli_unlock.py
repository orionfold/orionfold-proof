"""`orionfold unlock` end-to-end (headless): dev-sign a license + assemble a pack → install.

Isolates the DB (``ORIONFOLD_DB``) and the model overlay (``ORIONFOLD_MODELS_OVERLAY``) so it never
touches the real ~/.orionfold store. The license is dev-signed with the published throwaway key — no
secret, no network.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from orionfold.cli import app

runner = CliRunner()

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "licensing"
sys.path.insert(0, str(_FIXTURES))
import pack_factory as pf  # noqa: E402

# Key-shaped patterns the receipt/output must never contain (mirrors the repo secrets posture).
_SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"AIza[0-9A-Za-z_\-]{20,}",
    r"ORIONFOLD_LICENSE",
]


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("ORIONFOLD_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ORIONFOLD_MODELS_OVERLAY", str(tmp_path / "models.json"))
    return tmp_path


def test_unlock_installs_and_lists_dataset(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    lic = pf.write_license(tmp_path / "license")

    result = runner.invoke(app, ["unlock", str(pack), "--license", str(lic)])
    assert result.exit_code == 0, result.stdout
    assert "Unlocked" in result.stdout
    assert "rerun the reference receipt" in result.stdout

    # The installed dataset is now selectable via the dataset list verb.
    listed = runner.invoke(app, ["dataset", "list"])
    assert listed.exit_code == 0, listed.stdout
    assert pf.DATASET_NAME in listed.stdout

    # Output is secret-free.
    for pat in _SECRET_PATTERNS:
        assert not re.search(pat, result.stdout), pat


def test_unlock_from_zip(store, tmp_path) -> None:
    zpath = pf.write_pack_zip(tmp_path)
    lic = pf.write_license(tmp_path / "license")
    result = runner.invoke(app, ["unlock", str(zpath), "--license", str(lic)])
    assert result.exit_code == 0, result.stdout


def test_unlock_is_idempotent(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    lic = pf.write_license(tmp_path / "license")
    first = runner.invoke(app, ["unlock", str(pack), "--license", str(lic)])
    second = runner.invoke(app, ["unlock", str(pack), "--license", str(lic)])
    assert first.exit_code == 0 and second.exit_code == 0
    assert "already present" in second.stdout


def test_unlock_with_product_ownership(store, tmp_path) -> None:
    """The real buying intent: own Orionfold Proof → any included pack unlocks (no pack id named)."""
    pack = pf.write_pack_dir(tmp_path)
    # A product-ownership license carrying NO pack:<id> grant for this pack.
    lic = pf.write_license(tmp_path / "license", pack_ids=["unrelated"], own_product=True)
    result = runner.invoke(app, ["unlock", str(pack), "--license", str(lic)])
    assert result.exit_code == 0, result.stdout
    assert "Unlocked" in result.stdout


def test_unlock_rejects_unentitled_license(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    lic = pf.write_license(tmp_path / "license", pack_ids=["some-other-pack"])
    result = runner.invoke(app, ["unlock", str(pack), "--license", str(lic)])
    assert result.exit_code == 3
    assert "does not unlock" in result.stderr


def test_unlock_rejects_expired_license(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    lic = pf.write_license(
        tmp_path / "license",
        not_before="2020-01-01T00:00:00Z",
        expires_at="2020-12-31T00:00:00Z",
    )
    result = runner.invoke(app, ["unlock", str(pack), "--license", str(lic)])
    assert result.exit_code == 2
    assert "expired" in result.stderr


def test_unlock_missing_license(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    result = runner.invoke(app, ["unlock", str(pack), "--license", str(tmp_path / "absent")])
    assert result.exit_code == 2
    assert "no license file" in result.stderr


def test_unlock_rejects_tampered_pack(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    (pack / "manifest.json").write_text("not json", "utf-8")
    lic = pf.write_license(tmp_path / "license")
    result = runner.invoke(app, ["unlock", str(pack), "--license", str(lic)])
    assert result.exit_code == 2
    assert "Pack error" in result.stderr


# --- --license-url (slice 2): fetch the signed-URL license, then the same gate ----


def _serve_license_doc(monkeypatch, doc: dict) -> None:
    """Patch the license module's httpx.get so --license-url fetches `doc` (no real network)."""
    import httpx

    from orionfold.licensing import license as lic

    def fake_get(url, **kwargs):  # noqa: ANN001
        return httpx.Response(200, json=doc, request=httpx.Request("GET", url))

    monkeypatch.setattr(lic.httpx, "get", fake_get)


def _license_doc(tmp_path, **kw) -> dict:
    import json

    path = pf.write_license(tmp_path / "_url_license", **kw)
    return json.loads(path.read_text("utf-8"))


def test_unlock_from_license_url(store, tmp_path, monkeypatch) -> None:
    pack = pf.write_pack_dir(tmp_path)
    _serve_license_doc(monkeypatch, _license_doc(tmp_path))
    result = runner.invoke(
        app, ["unlock", str(pack), "--license-url", "https://example.com/lic.json"]
    )
    assert result.exit_code == 0, result.stdout
    assert "Unlocked" in result.stdout
    for pat in _SECRET_PATTERNS:
        assert not re.search(pat, result.stdout), pat


def test_unlock_license_url_must_be_https(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    result = runner.invoke(
        app, ["unlock", str(pack), "--license-url", "http://example.com/lic.json"]
    )
    assert result.exit_code == 2
    assert "https" in result.stderr


def test_unlock_rejects_both_license_and_url(store, tmp_path) -> None:
    pack = pf.write_pack_dir(tmp_path)
    lic = pf.write_license(tmp_path / "license")
    result = runner.invoke(
        app,
        ["unlock", str(pack), "--license", str(lic), "--license-url", "https://x/lic.json"],
    )
    assert result.exit_code == 2
    assert "both" in result.stderr.lower() or "either" in result.stderr.lower()


def test_unlock_license_url_unentitled(store, tmp_path, monkeypatch) -> None:
    pack = pf.write_pack_dir(tmp_path)
    _serve_license_doc(monkeypatch, _license_doc(tmp_path, pack_ids=["some-other-pack"]))
    result = runner.invoke(
        app, ["unlock", str(pack), "--license-url", "https://example.com/lic.json"]
    )
    assert result.exit_code == 3
    assert "does not unlock" in result.stderr
