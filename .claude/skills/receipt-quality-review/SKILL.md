---
name: receipt-quality-review
description: Use when receipt structure, export, or leaderboard changes. Generates a sample receipt, inspects Markdown/HTML/JSON, confirms no secrets, and confirms the recommendation is clear and client-shareable.
---

# Receipt quality review

The Proof Receipt is the product. Review it like a deliverable a consultant would hand
to a paying client.

## Steps

1. Generate a sample receipt from the demo dataset and a known proof run.
2. Inspect each format:
   - **Markdown** — clean headings; leaderboard as a table; failure cases as bullets;
     no app-only UI language.
   - **HTML** — self-contained and printable; readable without app CSS; no external
     trackers; includes timestamp and config hash.
   - **JSON** — versioned schema; predictable field names; machine-readable.
3. Confirm the receipt contains all required sections: Decision · Summary · Dataset ·
   Candidates · Leaderboard · Failure Cases · Recommendation · Repro (run id, config
   hash, timestamp, rerun command).
4. Confirm the **recommendation** is one clear verdict (Ship / Ship with fallback /
   Keep testing / Improve prompt / Add retrieval / Fine-tune later / Reject).
5. Confirm **no secrets**, raw API keys, or full provider config appear in any format.
6. Confirm schema stability — if a field changed, the `version` field was bumped.

## Output

List any defect with the exact format and field, then fix scoped issues and re-export.
