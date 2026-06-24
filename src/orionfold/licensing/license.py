"""The `orionfold.license/v1` license file — schema, canonical signing bytes, Ed25519 verify.

Vendored from fieldkit's ``field_edition/license.py`` (Apache-2.0, same author) and adapted for
Proof. The two halves of the signing contract MUST stay byte-identical: the website issuer
(``supabase/functions/_shared/license.ts``) signs, this module verifies. That invariant is locked
by ``tests/unit/test_license.py`` against the vendored conformance vector
(``tests/fixtures/licensing/license-conformance-v1.json``) — the same vector fieldkit and the
website both conform to.

A license is a JSON document: a ``payload`` of claims + a detached **Ed25519** ``signature`` over
the payload's canonical bytes. ``orionfold unlock`` verifies the signature locally against a public
key embedded in this module (:data:`TRUSTED_KEYS`); the matching private key is held only by the
issuer (the commerce server), never shipped. No phone-home — the math is the gate.

What the license carries (and why):

* **identity + term** — ``license_id``, ``issued_to``, ``issued_at`` / ``not_before`` /
  ``expires_at`` (the kept-proven window), ``seats``.
* **entitlements** — coarse capability flags. Proof uses ``pack:<pack_id>`` entries to authorize a
  specific domain pack (see :meth:`License.entitles_pack`).

**The signing contract (the issuer must match byte-for-byte):** the signed bytes are
:func:`canonical_bytes` of the ``payload`` object — ``json.dumps(payload, sort_keys=True,
separators=(",", ":"), ensure_ascii=False).encode("utf-8")`` — a compact, recursively key-sorted,
UTF-8 encoding (RFC-8785-style, pinned to this exact recipe). The signature value is **standard
base64** (with padding) of the 64-byte Ed25519 signature; the public key in :data:`TRUSTED_KEYS` is
standard base64 of the 32-byte raw Ed25519 public key. Keep every payload value a
string / int / bool / list / nested object — **no floats** (cross-language float formatting diverges
and would break the signature).

The Ed25519 primitives (``cryptography``) are imported lazily inside :func:`verify_signature` /
:func:`sign_payload` so ``import orionfold.licensing.license`` stays cheap.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import httpx

__all__ = [
    "LICENSE_SCHEMA",
    "DEFAULT_LICENSE_PATH",
    "TRUSTED_KEYS",
    "ACTIVE_KEY_ID",
    "PROD_KEY_PENDING",
    "LicenseError",
    "IssuedTo",
    "License",
    "canonical_bytes",
    "sign_payload",
    "verify_signature",
    "parse_license",
    "load_license",
    "load_license_from_doc",
    "fetch_license",
    "pack_entitlement",
    "PROOF_PRODUCT",
    "PRODUCT_ENTITLEMENT",
]

#: How long to wait for the signed-URL license download before giving up.
_FETCH_TIMEOUT_S = 15.0

_log = logging.getLogger("orionfold.licensing")

#: The schema discriminator every v1 payload carries (shared with the website issuer + fieldkit).
LICENSE_SCHEMA = "orionfold.license/v1"

#: Where a license is dropped by default (Proof already uses ~/.orionfold/ for its store).
DEFAULT_LICENSE_PATH = Path(
    os.environ.get("ORIONFOLD_LICENSE", str(Path.home() / ".orionfold" / "license"))
)

#: Sentinel for a key slot whose real public key the ops keypair hasn't produced yet.
PROD_KEY_PENDING = "PROD_KEY_PENDING"

#: key_id → base64(32-byte raw Ed25519 public key). The verifier trusts any key listed here, so
#: rotation is additive: publish a new key_id, sign new licenses with it, retire the old once
#: outstanding licenses lapse. These values are vendored verbatim from fieldkit's TRUSTED_KEYS so a
#: license signed for either product verifies identically.
#:
#: ``of-license-prod-2026`` is the PRODUCTION slot (private seed lives only in the commerce plane).
#: ``of-license-dev-2026-06`` is a NON-PRODUCTION developer key whose public half is committed so the
#: tests + a dev-signed sample pack self-validate. It must NEVER sign a customer license. Its private
#: seed is the openly-throwaway ``bytes(range(32))`` (00 01 02 … 1f) — published on purpose so tests
#: reproduce it without storing a secret; that is precisely why it is dev-only.
TRUSTED_KEYS: dict[str, str] = {
    "of-license-prod-2026": "LQVkEw+cetZGkstWJSdKoxOF/kuCrCgmGADaFi/yyDc=",
    "of-license-dev-2026-06": "A6EHv/POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg=",
}

#: The key_id the issuer should sign with in production.
ACTIVE_KEY_ID = "of-license-prod-2026"


#: The product a Proof license is sold as. The buying intent is "Orionfold Proof" (the product),
#: not any one pack — so a license carries the product entitlement below and owning it unlocks any
#: pack that ships with the product.
PROOF_PRODUCT = "orionfold-proof"

#: The entitlement string that means "this buyer owns Orionfold Proof". Its presence unlocks every
#: included pack (see :meth:`License.unlocks_pack`). A per-pack ``pack:<id>`` entitlement is still
#: honored for a possible future à-la-carte sale, but product ownership is the primary path.
PRODUCT_ENTITLEMENT = f"product:{PROOF_PRODUCT}"


def pack_entitlement(pack_id: str) -> str:
    """The (optional, à-la-carte) entitlement string authorizing one specific domain pack."""
    return f"pack:{pack_id}"


class LicenseError(Exception):
    """A license is missing, malformed, expired, or fails signature verification."""


@dataclass(frozen=True)
class IssuedTo:
    """Who the license was issued to (provenance — not security-bearing)."""

    name: str
    email: str
    org: str = ""

    @classmethod
    def from_obj(cls, obj: Mapping[str, Any]) -> "IssuedTo":
        return cls(
            name=str(obj.get("name", "")),
            email=str(obj.get("email", "")),
            org=str(obj.get("org", "")),
        )


@dataclass(frozen=True)
class License:
    """A parsed, structurally-validated v1 license payload.

    Signature verification + term enforcement happen in :func:`load_license`; this dataclass is just
    the typed view of a verified payload."""

    license_id: str
    product: str
    issued_to: IssuedTo
    issued_at: str
    not_before: str
    expires_at: str
    seats: int
    entitlements: tuple[str, ...]
    raw: Mapping[str, Any]  # the exact payload object (for round-trip / debugging)

    def has_entitlement(self, name: str) -> bool:
        return name in self.entitlements

    def entitles_pack(self, pack_id: str) -> bool:
        """True iff this license carries the specific ``pack:<pack_id>`` entitlement (à-la-carte)."""
        return pack_entitlement(pack_id) in self.entitlements

    def owns_product(self) -> bool:
        """True iff this license carries the ``product:orionfold-proof`` entitlement."""
        return PRODUCT_ENTITLEMENT in self.entitlements

    def unlocks_pack(self, pack_id: str) -> bool:
        """True iff this license may install the given pack.

        Owning Orionfold Proof (the product entitlement) unlocks any included pack; alternatively a
        specific ``pack:<pack_id>`` entitlement unlocks just that pack. The buying intent is the
        product, so product ownership is the primary path and a per-pack grant is the exception."""
        return self.owns_product() or self.entitles_pack(pack_id)

    def expires_dt(self) -> datetime:
        return _parse_ts(self.expires_at)

    def not_before_dt(self) -> datetime:
        return _parse_ts(self.not_before)

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return self.not_before_dt() <= now < self.expires_dt()


# --- the signing contract ----------------------------------------------------


def canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    """The exact bytes the Ed25519 signature covers (issuer + verifier MUST match).

    Compact, recursively key-sorted, UTF-8 JSON. The JS issuer must produce the identical bytes —
    sort keys at every object level, no inter-token whitespace, UTF-8, and no floats anywhere in the
    payload."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sign_payload(payload: Mapping[str, Any], private_key_b64: str) -> str:
    """Sign a payload with a base64 32-byte Ed25519 private seed → base64 sig.

    The issuer-side reference (the website's ``fulfillLicense`` ports this to TS). Kept here so the
    tests + a dev-signed sample pack sign with the exact verifier recipe; **not** wired to any CLI
    verb (signing is the issuer's job)."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except Exception as err:  # noqa: BLE001 — cryptography missing
        raise LicenseError(
            "the `cryptography` package is required to sign a license "
            f"(pip install cryptography): {err}"
        ) from err
    seed = base64.b64decode(private_key_b64)
    if len(seed) != 32:
        raise LicenseError(f"Ed25519 private seed must be 32 bytes, got {len(seed)}")
    key = Ed25519PrivateKey.from_private_bytes(seed)
    sig = key.sign(canonical_bytes(payload))
    return base64.b64encode(sig).decode("ascii")


def verify_signature(payload: Mapping[str, Any], signature: Mapping[str, Any]) -> None:
    """Verify a detached Ed25519 signature against an embedded trusted key.

    Raises :class:`LicenseError` on an unknown/pending key id, a bad algorithm, malformed signature
    material, or a verification failure — never returns a soft verdict.
    """
    alg = str(signature.get("alg", ""))
    if alg != "ed25519":
        raise LicenseError(f"unsupported signature alg {alg!r} (expected 'ed25519')")
    key_id = str(signature.get("key_id", ""))
    pub_b64 = TRUSTED_KEYS.get(key_id)
    if pub_b64 is None:
        raise LicenseError(f"unknown signing key id {key_id!r} (not in TRUSTED_KEYS)")
    if pub_b64 == PROD_KEY_PENDING:
        raise LicenseError(
            f"signing key {key_id!r} is not provisioned yet (PROD_KEY_PENDING) — "
            "ops must generate the production keypair and embed its public key"
        )
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except Exception as err:  # noqa: BLE001 — cryptography missing
        raise LicenseError(
            "the `cryptography` package is required to verify a license "
            f"(pip install cryptography): {err}"
        ) from err
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(pub_b64))
        sig = base64.b64decode(str(signature["value"]))
    except Exception as err:  # noqa: BLE001 — malformed base64 / key
        raise LicenseError(f"malformed signature or key material: {err}") from err
    try:
        pub.verify(sig, canonical_bytes(payload))
    except InvalidSignature as err:
        raise LicenseError(
            "license signature does not verify against the trusted public key "
            f"({key_id}) — the file was tampered with or signed by the wrong key"
        ) from err


# --- parsing + loading -------------------------------------------------------


def parse_license(payload: Mapping[str, Any]) -> License:
    """Structurally validate a payload into a :class:`License` (no crypto)."""
    schema = str(payload.get("schema", ""))
    if schema != LICENSE_SCHEMA:
        raise LicenseError(f"unexpected license schema {schema!r} (expected {LICENSE_SCHEMA!r})")
    try:
        return License(
            license_id=str(payload["license_id"]),
            product=str(payload.get("product", "")),
            issued_to=IssuedTo.from_obj(payload.get("issued_to") or {}),
            issued_at=str(payload["issued_at"]),
            not_before=str(payload.get("not_before") or payload["issued_at"]),
            expires_at=str(payload["expires_at"]),
            seats=int(payload.get("seats", 1)),
            entitlements=tuple(str(e) for e in (payload.get("entitlements") or [])),
            raw=payload,
        )
    except KeyError as err:
        raise LicenseError(f"license payload missing required field: {err}") from err


def load_license(
    path: Path | None = None,
    *,
    now: datetime | None = None,
    enforce_term: bool = True,
) -> License:
    """Read, **verify**, and term-check a license file → a :class:`License`.

    The full offline gate: parse the JSON, verify the Ed25519 signature against the embedded trusted
    key, then (``enforce_term``) reject a not-yet-valid or expired license. Any failure raises
    :class:`LicenseError` with an actionable message — never a silent pass to an unentitled install."""
    path = path or DEFAULT_LICENSE_PATH
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise LicenseError(
            f"no license file at {path} — pass `--license <file>` (the one ops issued)"
        ) from err
    except json.JSONDecodeError as err:
        raise LicenseError(f"license file at {path} is not valid JSON: {err}") from err

    return load_license_from_doc(doc, now=now, enforce_term=enforce_term)


def load_license_from_doc(
    doc: Any,
    *,
    now: datetime | None = None,
    enforce_term: bool = True,
) -> License:
    """Verify + term-check an already-parsed license document → a :class:`License`.

    The shared gate behind both :func:`load_license` (read from disk) and :func:`fetch_license` +
    this (read over the network for ``--license-url``): a ``{payload, signature}`` object verified
    against the embedded trusted key. Identical verification regardless of where the bytes came
    from — the signature is the only trust boundary."""
    if not isinstance(doc, Mapping):
        raise LicenseError("license must be a JSON object with `payload` and `signature`")
    payload = doc.get("payload")
    signature = doc.get("signature")
    if not isinstance(payload, Mapping) or not isinstance(signature, Mapping):
        raise LicenseError("license must have an object `payload` and `signature`")

    verify_signature(payload, signature)
    lic = parse_license(payload)

    if enforce_term:
        now = now or datetime.now(timezone.utc)
        if now < lic.not_before_dt():
            raise LicenseError(
                f"license {lic.license_id} is not valid until {lic.not_before} "
                f"(now {now.isoformat()})"
            )
        if now >= lic.expires_dt():
            raise LicenseError(
                f"license {lic.license_id} expired {lic.expires_at} — renew to keep the pack"
            )
    return lic


def fetch_license(url: str) -> Any:
    """Download a license document from an HTTPS signed URL → the parsed JSON ``{payload, signature}``.

    Mirrors the storefront delivery contract (``stripe-webhook`` signs a license, uploads the JSON
    to a private bucket, and emails a time-limited **signed URL** — all auth is in the URL token, so
    this is a plain authenticated GET, no headers or body). The returned doc is handed to
    :func:`load_license_from_doc` for the same offline signature + term gate the file path uses.

    HTTPS only — a license must arrive over TLS; ``http://`` / ``file://`` are rejected. Any
    network / HTTP-status / JSON failure becomes a named :class:`LicenseError` (never a soft pass)."""
    if not url.lower().startswith("https://"):
        raise LicenseError(f"license url must be https:// (got {url!r})")
    try:
        response = httpx.get(url, follow_redirects=True, timeout=_FETCH_TIMEOUT_S)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as err:
        raise LicenseError(
            f"couldn't fetch license from {url}: server returned {err.response.status_code}"
        ) from err
    except httpx.HTTPError as err:  # connect / timeout / transport
        raise LicenseError(f"couldn't fetch license from {url}: {err}") from err
    except ValueError as err:  # response.json() on non-JSON
        raise LicenseError(f"couldn't fetch license from {url}: response was not valid JSON: {err}") from err


def _parse_ts(ts: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp (accepting a trailing ``Z``)."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError as err:
        raise LicenseError(f"malformed timestamp {ts!r}: {err}") from err
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
