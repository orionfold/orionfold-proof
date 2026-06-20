# Orionfold Proof — demo script

A 3-minute walkthrough that proves the one outcome v0 delivers:

> "I compared my AI options on my own task and got a repeatable receipt showing what is
> worth trusting."

There are two passes: a **keyless pass** that anyone can run with no credentials, and a
**real-provider pass** that adds a live cloud or local model.

---

## Setup

```bash
bash scripts/build.sh      # build + embed the cockpit, build the wheel
uv run orionfold up        # serve the cockpit + API
```

Open **http://localhost:8787**. (If 8787 is taken, `uv run orionfold up --port 8790`.)

The cockpit is one calm panel: a **Run setup** card (dataset, candidates, Proof Brief, and a
**Run proof** button). Leaderboard, failure cases, and receipt export appear *after* a run.

---

## Pass 1 — keyless (no credentials)

1. **Dataset.** The bundled **Investment memo summarization** dataset is selected by default.
2. **Candidates.** The two deterministic mocks — **`mock_good`** and **`mock_bad`** — are
   pre-selected. They need no keys and run instantly, so the first click never fires a paid
   call.
3. **Proof Brief.** The task name and decision question are pre-filled
   ("Which model should I trust for client memo summaries?"). Optionally add a success
   criterion.
4. **Run proof.** Click it. The matrix (candidates × examples) runs locally in well under a
   second.
5. **Leaderboard.** `mock_good` ranks above `mock_bad` on quality, with latency, estimated
   cost, failure count, privacy mode, and a plain-language **recommendation**.
6. **Failure case.** Open a failing example to see the input, expected text, the candidate's
   output, and why it missed — including a surfaced provider error if one occurred.
7. **Export the receipt.** Export in **Markdown, HTML, and JSON**. Each carries a
   `config_hash`, timestamp, and `receipt_version: 3`. Compare with the committed samples in
   [`samples/receipts/`](../samples/receipts/) — they're byte-stable for the demo run.

That is a complete, private, repeatable Proof Receipt with **zero credentials**.

---

## Pass 2 — a real provider (optional, needs a key)

1. **Add a key.** Put one in repo-root `.env.local` (git-ignored) — see
   [README → Configure providers](../README.md#configure-providers). For example
   `OPENROUTER_API_KEY=sk-or-...` (or a local Ollama / LM Studio server, which needs no key).
2. **Restart** `orionfold up`. The matching candidate — e.g. **OpenRouter ·
   openai/gpt-4o-mini** — now appears as a checkbox. Keyless mocks stay the default; cloud
   candidates are opt-in.
3. **Select it** alongside the mocks and **Run proof** again. The real model is called
   through the same `ProviderResult` boundary: real output, real latency, estimated cost.
4. **Read the receipt.** The candidate's `model` is part of its identity and feeds the
   `config_hash`, so a real-model run produces a distinct, traceable receipt — with **no key
   material anywhere** in it.

> A real-model run can score `pass=0` against the bundled rubric (tuned for the mock demo at
> similarity ≥ 0.8) — verbose real output doesn't match the terse expected text. That's
> expected: the demo proves the **integration and the receipt**, not a given model's score.
> Point the tool at your own dataset and rubric to get a meaningful comparison.

A captured screenshot of a real-provider run lives at
[`samples/screenshots/`](../samples/screenshots/) (see that folder's README for the exact
file).

---

## Tagline

> Private, repeatable proof of which AI workflow is worth trusting.
