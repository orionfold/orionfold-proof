# Sample datasets

The v0 demo dataset — **Investment memo summarization** — ships *inside the package* so it
is available from a clean wheel install with no extra files:

```
src/orionfold/data/datasets/investment_memo_summarization.json
```

It is loaded at runtime via `orionfold.data.load_dataset(...)` and seeded into the local
SQLite store on first launch (`storage.repository.seed_datasets`). Pick it in the cockpit's
**Dataset** selector and click **Run proof**.

This `samples/datasets/` directory is reserved for *user-facing example datasets* you can
import once dataset import (JSONL/CSV/Markdown/paste) lands — it is intentionally empty in
Gate 5, which uses the bundled dataset above.
