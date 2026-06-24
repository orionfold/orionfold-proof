"""License verifier conformance + signature/term tests.

The conformance test is the anti-drift guard: it asserts Proof's :func:`canonical_bytes` produces
byte-identical signing input to the vendored vector (the same vector fieldkit + the website issuer
conform to). If this ever fails, the canonicalization recipe diverged and a real license signed by
the website would stop verifying — that is the bug the vector exists to catch.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from orionfold.licensing import license as lic

VECTOR_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "licensing" / "license-conformance-v1.json"
)
VECTOR = json.loads(VECTOR_PATH.read_text("utf-8"))
DEV_KEY_ID = VECTOR["dev_key"]["key_id"]
DEV_SEED_B64 = VECTOR["dev_key"]["private_seed_b64"]


def _sign(payload: dict, *, key_id: str = DEV_KEY_ID, seed_b64: str = DEV_SEED_B64) -> dict:
    """Build a signed license doc with the throwaway dev key (test helper / dev-pack signer)."""
    return {
        "payload": payload,
        "signature": {
            "alg": "ed25519",
            "key_id": key_id,
            "value": lic.sign_payload(payload, seed_b64),
        },
    }


def _founding_payload() -> dict:
    """The vector's full-license payload (already founding-25, term 2026→2027)."""
    return dict(VECTOR["cases"][3]["payload"])


# --- conformance: canonicalization is byte-identical to the vector ------------


@pytest.mark.parametrize("case", VECTOR["cases"], ids=[c["name"] for c in VECTOR["cases"]])
def test_canonical_bytes_matches_vector(case: dict) -> None:
    got = lic.canonical_bytes(case["payload"])
    assert got == case["canonical_utf8"].encode("utf-8")
    assert hashlib.sha256(got).hexdigest()[:12] == case["canonical_sha256_12"]


@pytest.mark.parametrize("case", VECTOR["cases"], ids=[c["name"] for c in VECTOR["cases"]])
def test_vector_signatures_verify(case: dict) -> None:
    """Every vector signature (signed by the dev key) verifies via our embedded TRUSTED_KEYS."""
    lic.verify_signature(
        case["payload"], {"alg": "ed25519", "key_id": DEV_KEY_ID, "value": case["signature_b64"]}
    )


def test_dev_pubkey_matches_trusted_keys() -> None:
    assert lic.TRUSTED_KEYS[DEV_KEY_ID] == VECTOR["dev_key"]["public_key_b64"]


# --- verify_signature failure modes ------------------------------------------


def test_tampered_payload_fails() -> None:
    payload = _founding_payload()
    doc = _sign(payload)
    payload["seats"] = 999  # tamper after signing
    with pytest.raises(lic.LicenseError, match="does not verify"):
        lic.verify_signature(payload, doc["signature"])


def test_unknown_key_id_fails() -> None:
    payload = _founding_payload()
    with pytest.raises(lic.LicenseError, match="unknown signing key id"):
        lic.verify_signature(payload, {"alg": "ed25519", "key_id": "nope", "value": "AA=="})


def test_bad_alg_fails() -> None:
    with pytest.raises(lic.LicenseError, match="unsupported signature alg"):
        lic.verify_signature({}, {"alg": "rsa", "key_id": DEV_KEY_ID, "value": "AA=="})


def test_malformed_signature_value_fails() -> None:
    payload = _founding_payload()
    with pytest.raises(lic.LicenseError):
        lic.verify_signature(
            payload, {"alg": "ed25519", "key_id": DEV_KEY_ID, "value": "not-base64!!"}
        )


# --- load_license: schema, signature, term -----------------------------------


def _write(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "license"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def test_load_license_happy_path(tmp_path: Path) -> None:
    payload = _founding_payload()
    path = _write(tmp_path, _sign(payload))
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)  # inside the term
    out = lic.load_license(path, now=now)
    assert out.license_id == payload["license_id"]
    assert out.has_entitlement("proven-matrix-images")


def test_load_license_missing_file(tmp_path: Path) -> None:
    with pytest.raises(lic.LicenseError, match="no license file"):
        lic.load_license(tmp_path / "absent")


def test_load_license_wrong_schema(tmp_path: Path) -> None:
    payload = _founding_payload()
    payload["schema"] = "bogus/v9"
    path = _write(tmp_path, _sign(payload))
    with pytest.raises(lic.LicenseError, match="unexpected license schema"):
        lic.load_license(path, enforce_term=False)


def test_load_license_expired(tmp_path: Path) -> None:
    payload = _founding_payload()
    path = _write(tmp_path, _sign(payload))
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)  # past expires_at
    with pytest.raises(lic.LicenseError, match="expired"):
        lic.load_license(path, now=now)


def test_load_license_not_yet_valid(tmp_path: Path) -> None:
    payload = _founding_payload()
    payload["not_before"] = "2099-01-01T00:00:00Z"
    path = _write(tmp_path, _sign(payload))
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    with pytest.raises(lic.LicenseError, match="not valid until"):
        lic.load_license(path, now=now)


def test_pack_entitlement_helpers() -> None:
    assert lic.pack_entitlement("advisor-field-notes") == "pack:advisor-field-notes"
    payload = _founding_payload()
    payload["entitlements"] = ["pack:advisor-field-notes"]
    parsed = lic.parse_license(payload)
    assert parsed.entitles_pack("advisor-field-notes")
    assert not parsed.entitles_pack("some-other-pack")
