"""Bundled data — sample datasets that ship inside the wheel.

Loaded via ``importlib.resources`` so they resolve identically from a source checkout or an
installed wheel (no reliance on the working directory).
"""

from __future__ import annotations

import json
from importlib import resources

from orionfold.domain.models import Corpus, Dataset

_DATASET_FILES = {
    "investment-memo-summarization": "investment_memo_summarization.json",
    "support-ticket-triage": "support_ticket_triage.json",
    "contract-field-extraction": "contract_field_extraction.json",
    "buyer-need-solution-match": "buyer_need_solution_match.json",
}

# Bench datasets ship with a governing corpus and are seeded as samples (corpus first) rather than
# always-on bundled datasets — they require a corpus binding the plain seed path doesn't supply.
_BENCH_DATASET_FILES = {
    "advisor-curveball-v0.2": "advisor_curveball_v0_2.json",
}
_CORPUS_FILES = {
    "ainative-field-notes": "ainative_field_notes.json",
}


def load_dataset(dataset_id: str) -> Dataset:
    """Load a bundled dataset by id (plain or bench), validated into a :class:`Dataset`."""
    filename = _DATASET_FILES.get(dataset_id) or _BENCH_DATASET_FILES[dataset_id]
    raw = (resources.files("orionfold.data.datasets") / filename).read_text("utf-8")
    return Dataset.model_validate(json.loads(raw))


def bundled_datasets() -> list[Dataset]:
    """The always-on datasets that ship and auto-seed with the app (excludes bench samples)."""
    return [load_dataset(dataset_id) for dataset_id in _DATASET_FILES]


def load_corpus(corpus_id: str) -> Corpus:
    """Load a bundled corpus manifest by id, validated into a :class:`Corpus`."""
    filename = _CORPUS_FILES[corpus_id]
    raw = (resources.files("orionfold.data.corpora") / filename).read_text("utf-8")
    return Corpus.model_validate(json.loads(raw))


def bundled_corpora() -> list[Corpus]:
    """All corpus manifests that ship with the app."""
    return [load_corpus(corpus_id) for corpus_id in _CORPUS_FILES]


def bundled_bench_datasets() -> list[Dataset]:
    """Bench sample datasets that ship with the app (each binds a bundled corpus)."""
    return [load_dataset(dataset_id) for dataset_id in _BENCH_DATASET_FILES]
