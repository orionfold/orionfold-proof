"""The `orionfold.pack/v1` domain pack — manifest schema + reader (dir or .zip).

A domain pack is the unit `orionfold unlock` installs: a manifest plus the bundled corpus / dataset /
reference-receipt files, in the **same JSON formats Proof already bundles** (``data/corpora/*.json``,
``data/datasets/*.json``, a stored :class:`ProofReport`). A pack is therefore "the bundled-dataset
files, shipped as a unit and gated by a license" — :func:`open_pack` reads + validates each referenced
file through the existing domain models, so a malformed pack fails through the same validation the
bundled seeds already pass.

The pack itself is **not** signed — the license is the trust gate (its ``pack:<pack_id>`` entitlement
names this pack). See :mod:`orionfold.licensing.license` and :func:`orionfold.licensing.install`.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from orionfold.domain.models import Corpus, Dataset, ProofReport
from orionfold.recipes.models import Recipe

PACK_SCHEMA = "orionfold.pack/v1"
PACK_PRODUCT = "orionfold-proof"


class PackError(Exception):
    """A pack is missing, has no valid manifest, references a missing file, or targets a wrong product."""


class ModelPointer(BaseModel):
    """The GGUF model a pack expects (recorded into the ~/.orionfold/models.json overlay on install)."""

    repo_id: str
    display_name: str | None = None


class PackManifest(BaseModel):
    """The ``orionfold.pack/v1`` manifest — the spine of a domain pack."""

    schema_: str  # populated from the JSON "schema" field (see open_pack)
    pack_id: str
    name: str
    version: str = "0"
    product: str = PACK_PRODUCT
    corpus: str | None = None
    dataset: str | None = None
    recipe: str | None = None
    reference_receipt: str | None = None
    model: ModelPointer | None = None


@dataclass(frozen=True)
class Pack:
    """A read, structurally-validated pack: its manifest + the parsed artifacts it carries.

    Every artifact is parsed through the existing domain models, so a :class:`Pack` is install-ready.
    ``recipe`` is parsed (validated) when present but **not** installed in slice 1 (see the spec's
    non-goals — recipes are bundle-only today, with no store/overlay to write to)."""

    manifest: PackManifest
    corpus: Corpus | None
    dataset: Dataset | None
    recipe: Recipe | None
    reference_receipt: ProofReport | None


def open_pack(path: Path) -> Pack:
    """Read + validate a domain pack from a directory or a ``.zip``.

    Raises :class:`PackError` (actionable message, never a soft verdict) on a missing manifest, a
    wrong schema/product, a referenced-but-absent file, or a file that fails its domain-model
    validation."""
    read = _dir_reader(path) if path.is_dir() else _zip_reader(path)

    manifest = _read_manifest(read, path)
    if manifest.product != PACK_PRODUCT:
        raise PackError(f"pack targets {manifest.product!r}, not {PACK_PRODUCT}")

    corpus = _read_artifact(read, manifest.corpus, Corpus, "corpus", path)
    dataset = _read_artifact(read, manifest.dataset, Dataset, "dataset", path)
    recipe = _read_artifact(read, manifest.recipe, Recipe, "recipe", path)
    receipt = _read_artifact(
        read, manifest.reference_receipt, ProofReport, "reference_receipt", path
    )
    return Pack(
        manifest=manifest, corpus=corpus, dataset=dataset, recipe=recipe, reference_receipt=receipt
    )


# --- file readers (dir / zip share one (name) -> text | None interface) ------


def _dir_reader(root: Path):
    def read(name: str) -> str | None:
        p = root / name
        return p.read_text("utf-8") if p.is_file() else None

    return read


def _zip_reader(path: Path):
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as err:
        raise PackError(f"pack at {path} is not a readable directory or .zip: {err}") from err
    names = set(zf.namelist())

    def read(name: str) -> str | None:
        return zf.read(name).decode("utf-8") if name in names else None

    return read


# --- manifest + artifact parsing ---------------------------------------------


def _read_manifest(read, path: Path) -> PackManifest:
    raw = read("manifest.json")
    if raw is None:
        raise PackError(f"pack at {path} has no manifest.json")
    try:
        obj: dict[str, Any] = json.loads(raw)
    except ValueError as err:
        raise PackError(f"manifest.json in {path} is not valid JSON: {err}") from err
    schema = str(obj.get("schema", ""))
    if schema != PACK_SCHEMA:
        raise PackError(f"unexpected pack schema {schema!r} (expected {PACK_SCHEMA!r})")
    try:
        # The JSON key is "schema"; the model field is schema_ (schema shadows pydantic internals).
        return PackManifest(schema_=schema, **{k: v for k, v in obj.items() if k != "schema"})
    except ValidationError as err:
        raise PackError(f"manifest.json in {path} is malformed: {err}") from err


def _read_artifact(read, name: str | None, model, label: str, path: Path):
    """Read one optional artifact named by the manifest, parsed through its domain model."""
    if name is None:
        return None
    raw = read(name)
    if raw is None:
        raise PackError(f"manifest references {label} {name!r} but it's not in the pack at {path}")
    try:
        return model.model_validate(json.loads(raw))
    except ValueError as err:
        raise PackError(f"{label} {name!r} in {path} is malformed: {err}") from err
