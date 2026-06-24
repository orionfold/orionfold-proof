# `orionfold.receipts` — public API

Receipt and field-note rendering. The receipt is the central, protected artifact; a **field
note** wraps a receipt in a publish-ready trust narrative. Names not in `__all__` are internal
(use `orionfold.receipts.export.to_markdown` / `to_json` / `to_html` directly for the receipt
itself — those are the stable exporter functions, not yet graduated to `__all__`).

## Export a field note

```python
from orionfold.receipts import build_field_note
from orionfold.storage.db import connect, default_db_path
from orionfold.storage.repository import get_report

conn = connect(default_db_path())
report = get_report(conn, "run_…")        # a stored ProofReport
note = build_field_note(report)           # -> Markdown str
```

`build_field_note(report)` returns a single Markdown document:

1. **YAML frontmatter** — the provenance spine (`run_id`, `config_hash`, `decision_question`,
   `dataset`, `rubric`, `recommended`, `fmt_check`, `candidates`, `cost_usd`, `tags`). Every
   value is derived from the report — nothing invented.
2. **Two inline SVG figures** — a cost-vs-quality Pareto scatter and pass-rate bars,
   generated from the run data (pure Python, no browser). They theme with the publishing site
   via `var(--color-*)` and degrade gracefully on quick/no-winner runs.
3. **The receipt evidence body** — reused verbatim from `export.to_markdown` (verdict,
   leaderboard, cost, failure cases, repro), so it never drifts from the receipt.
4. **A narrative stub** — a `## Why this can be trusted` placeholder with
   `<!-- author: … -->` markers. **The package does not author the narrative.**

Secret-free by construction (it reads only a stored report, which already excludes keys and
full provider config). It touches no scoring or hash path and does not bump `RECEIPT_VERSION`
— the field note is a *sibling* of the receipt, not a new receipt schema.

## CLI

```
orionfold field-note <run_id> [--out note.md]
```

A thin shell over `build_field_note` (loads the report, 404s on an unknown id, writes to
stdout or `--out`). Mirrors `orionfold runs show`.

## Public surface

| Name | Purpose |
| --- | --- |
| `build_field_note(report)` | Compose a publish-ready field note (frontmatter + figures + receipt evidence + narrative stub) from a `ProofReport`. |

Figures (`orionfold.receipts.figures.pareto_svg` / `pass_rate_svg`) are pure SVG
string-builders consumed by `build_field_note`; they are not in `__all__`.
