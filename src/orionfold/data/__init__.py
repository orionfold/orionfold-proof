"""Bundled data — sample datasets that ship inside the wheel.

Loaded via ``importlib.resources`` so they resolve identically from a source checkout or an
installed wheel (no reliance on the working directory).
"""

from __future__ import annotations

import json
from importlib import resources

from orionfold.domain.models import Dataset

_DATASET_FILES = {
    "investment-memo-summarization": "investment_memo_summarization.json",
    "support-ticket-triage": "support_ticket_triage.json",
    "contract-field-extraction": "contract_field_extraction.json",
    "buyer-need-solution-match": "buyer_need_solution_match.json",
}


def load_dataset(dataset_id: str) -> Dataset:
    """Load a bundled dataset by id, validated into a :class:`Dataset`."""
    filename = _DATASET_FILES[dataset_id]
    raw = (resources.files("orionfold.data.datasets") / filename).read_text("utf-8")
    return Dataset.model_validate(json.loads(raw))


def bundled_datasets() -> list[Dataset]:
    """All datasets that ship with the app."""
    return [load_dataset(dataset_id) for dataset_id in _DATASET_FILES]
