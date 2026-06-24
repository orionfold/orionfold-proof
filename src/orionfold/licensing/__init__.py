"""Offline license verification + domain-pack install for `orionfold unlock`."""

from __future__ import annotations

from orionfold.licensing.license import (
    ACTIVE_KEY_ID,
    DEFAULT_LICENSE_PATH,
    LICENSE_SCHEMA,
    TRUSTED_KEYS,
    IssuedTo,
    License,
    LicenseError,
    canonical_bytes,
    load_license,
    pack_entitlement,
    parse_license,
    sign_payload,
    verify_signature,
)

__all__ = [
    "ACTIVE_KEY_ID",
    "DEFAULT_LICENSE_PATH",
    "LICENSE_SCHEMA",
    "TRUSTED_KEYS",
    "IssuedTo",
    "License",
    "LicenseError",
    "canonical_bytes",
    "load_license",
    "pack_entitlement",
    "parse_license",
    "sign_payload",
    "verify_signature",
]
