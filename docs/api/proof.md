# `orionfold.proof` — public API

The proof core. Import from the package root; names not in `__all__` are internal.

## Run a proof headlessly

```python
from orionfold.proof import execute_run
from orionfold.domain.models import Dataset, Example, ProofBrief

dataset = Dataset(id="my-task", name="My task", examples=[
    Example(input_text="ping", expected_text="ping"),
])
report = execute_run(
    dataset=dataset,
    candidate_ids=["mock_good", "mock_bad"],   # or "anthropic:claude-haiku-4-5", etc.
    brief=ProofBrief(task_name="My task", decision_question="Which is worth trusting?"),
)
```

`report` is a `ProofReport` (leaderboard + result rows + cost summary). Render it with
`orionfold.receipts.export.to_markdown(report)` / `to_json` / `to_html`.

## Public surface

| Name | Purpose |
| --- | --- |
| `execute_run(*, dataset, candidate_ids, brief, rubric=None, mode="full")` | Resolve ids+rubric, run the matrix, return the report (the CLI path). |
| `execute_resolved(*, dataset, candidates, rubric, brief, mode="full")` | Run from pre-resolved candidates+rubric (the web route's path). |
| `run_proof`, `run_matrix`, `iter_matrix`, `config_hash`, `build_cost_summary` | Engine primitives. |

The `orionfold run` CLI command is a thin wrapper over `execute_run`.
