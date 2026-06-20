# Sample screenshots

- **`design-system-empty.png`** — the three-pane cockpit at rest (empty state): quiet left
  rail (Proof Run active; Datasets/Candidates/Receipts marked _soon_), the main workspace with
  the setup card and a guided "No proof run yet" empty state, and the right inspector awaiting a
  run. Keyless mock pair pre-selected.
- **`design-system-populated.png`** — after a keyless mock run: the decision → recommended
  winner band, the leaderboard, and the failure-case list in the main workspace, with run
  config, the Proof Receipt exports, and config hash in the right inspector.
- **`design-system-inspector.png`** — the right inspector with a failure case selected
  (input / expected / output detail). No key material appears anywhere.
- **`real-provider-leaderboard.png`** — the cockpit after a real proof run comparing the two
  deterministic mocks against a live **OpenRouter** cloud candidate
  (`openai/gpt-4o-mini`). Shows the full loop: candidate selection (local + cloud), the
  leaderboard (quality, latency, estimated cost, privacy, failures, recommendation), failure
  cases, and the Proof Receipt export controls. Captured against the embedded build via
  `orionfold up`. No key material appears anywhere in the run or receipt.

Note: a real model legitimately scores `pass=0` here — the bundled rubric is tuned for the
mock demo (similarity ≥ 0.8). The screenshot proves the **integration and the receipt**, not
a given model's rubric score. See [`../../docs/demo-script.md`](../../docs/demo-script.md).
