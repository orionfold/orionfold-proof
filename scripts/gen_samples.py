"""Regenerate the bundled sample receipts deterministically.

Run after any change to the receipt schema, leaderboard shape, or candidate identity:

    uv run python scripts/gen_samples.py

The fixed ``run_id`` / ``created_at`` keep the output stable so a diff shows only real changes.
Uses the keyless mock candidates, so it needs no network and no credentials.
"""

from __future__ import annotations

from pathlib import Path

from orionfold.data import load_dataset
from orionfold.domain.models import Candidate, ProofBrief, Rubric
from orionfold.proof.engine import run_proof
from orionfold.receipts import export

_OUT = Path(__file__).resolve().parent.parent / "samples" / "receipts"


def main() -> None:
    report = run_proof(
        run_id="run_sampledemo01",
        created_at="2026-06-19T12:00:00Z",
        brief=ProofBrief(
            task_name="Investment memo summarization",
            decision_question="Which model should I trust for client memos?",
            success_criteria="At least 80% similarity to the analyst summary.",
        ),
        dataset=load_dataset("investment-memo-summarization"),
        candidates=[
            Candidate(id="mock_good", label="Mock · good", provider_id="mock_good"),
            Candidate(id="mock_bad", label="Mock · bad", provider_id="mock_bad"),
        ],
        rubric=Rubric(),
    )
    _OUT.mkdir(parents=True, exist_ok=True)
    (_OUT / "sample-proof-receipt.json").write_text(export.to_json(report), encoding="utf-8")
    (_OUT / "sample-proof-receipt.md").write_text(export.to_markdown(report), encoding="utf-8")
    (_OUT / "sample-proof-receipt.html").write_text(export.to_html(report), encoding="utf-8")
    print(f"Wrote sample receipts to {_OUT} (config_hash={report.run.config_hash})")


if __name__ == "__main__":
    main()
