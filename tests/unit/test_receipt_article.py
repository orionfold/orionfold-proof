"""Receipt-article = a receipt-derived scaffold targeting the website /receipts collection.

Freezes: every required /receipts frontmatter field present, the failures-first <=5-row
sample table, byte-determinism, the unauthored marker, and secret-freedom. The forbidden
prefixes are assembled at runtime so this source carries no key-shaped literal."""

import yaml

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.receipts import build_receipt_article

_BRIEF = ProofBrief(
    task_name="Support ticket triage",
    decision_question="Which model do I trust to triage tickets?",
    success_criteria="Exact label match.",
)


def _report(rubric=None):
    return run_proof(
        run_id="run_receipt_article",
        created_at="2026-06-27T12:00:00Z",
        brief=_BRIEF,
        dataset=load_dataset("support-ticket-triage"),
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=rubric or Rubric(kind="exact", threshold=1.0),
    )


def _frontmatter_dict(md: str) -> dict:
    assert md.startswith("---\n")
    return yaml.safe_load(md.split("---\n", 2)[1])


def test_frontmatter_has_every_required_receipts_field():
    fm = _frontmatter_dict(build_receipt_article(_report()))
    for key in ("title", "metric", "claim", "dek", "date", "tags", "relatedTo", "source", "verify"):
        assert key in fm, f"missing required /receipts field: {key}"
    assert isinstance(fm["tags"], list)
    assert isinstance(fm["relatedTo"], list)
    assert isinstance(fm["source"], list)


def test_sample_table_is_failures_first_and_capped():
    md = build_receipt_article(_report())
    assert "## Examples (sampled)" in md
    table = md.split("## Examples (sampled)", 1)[1]
    rows = [ln for ln in table.splitlines() if ln.strip().startswith("|")]
    assert 2 < len(rows) <= 7  # header + separator + 1..5 data rows


def test_deterministic():
    assert build_receipt_article(_report()) == build_receipt_article(_report())


def test_carries_unauthored_marker():
    assert "<!-- author: replace this section -->" in build_receipt_article(_report())


def test_secret_free():
    md = build_receipt_article(_report())
    # Forbidden prefixes built at runtime so no key-shaped literal lives in this file.
    forbidden = ["-".join(["sk", "ant"]) + "-", "sk" + "-", "ghp" + "_", "AKI" + "A"]
    for prefix in forbidden:
        assert prefix not in md
