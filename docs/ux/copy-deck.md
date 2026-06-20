# Copy Deck

The single source of truth for product nouns, labels, statuses, and message patterns.
Keep UI, receipts, and docs consistent with this. Update it before inventing new terms.

## Product nouns

Project · Proof Brief · Dataset · Example · Candidate · Proof Run · Leaderboard ·
Failure Case · Proof Receipt.

## Primary actions (button labels)

- `Create Proof Run`
- `Import Dataset`
- `Add Candidate`
- `Run Proof`
- `Export Receipt`
- `View Failure Case`
- `Rerun Proof`

## Status labels

- Proof run: `Draft` · `Running` · `Completed` · `Failed`
- Provider/candidate: `Local` · `Cloud` · `Mock` · `OpenAI-compatible` · `Ollama` · `LM Studio` · `Bedrock (later)`
- Result: `Pass` · `Warn` · `Fail`

## Recommendation labels (receipt verdict — pick exactly one)

`Ship` · `Ship with fallback` · `Keep testing` · `Improve prompt` · `Add retrieval` ·
`Fine-tune later` · `Reject`

## Error-message pattern

Specific · recoverable · calm · privacy-safe. Name the cause, then the fix. Never echo
secrets.

- Good: "Ollama is not reachable at localhost:11434. Start Ollama or switch to the mock provider."
- Good: "The OpenAI-compatible provider returned 401 Unauthorized. Check the API key. The key was not stored in the receipt."
- Bad: "Something went wrong." / "Provider failed."

## Empty-state pattern

Answer four questions: what is this area, why it matters, what to do next, can I try a sample.

- Good: "Proof Runs compare candidates on the same frozen examples so you can decide what to trust. Start with the sample run or create your own."
- Bad: "No proof runs yet."
