# Usability Checklist

Run this against any route before calling user-facing work done. Based on Nielsen
Norman's heuristics, scoped to this product.

## Per route

- [ ] One clear primary action; secondary actions are visually subordinate.
- [ ] Information hierarchy follows: decision → recommendation → evidence → leaderboard → failures → details → repro.
- [ ] All four states exist and are reachable: empty, loading, error, populated.
- [ ] Empty state answers: what is this, why it matters, what to do next, can I try a sample.
- [ ] Copy matches `copy-deck.md` (nouns, button labels, status labels, recommendations).
- [ ] Errors are specific, recoverable, calm, and privacy-safe (no secrets shown).
- [ ] The user can recover from mistakes (cancel, back, undo where relevant).
- [ ] System status is visible during long operations (a proof run shows progress).
- [ ] No dead ends: every state offers a next step.

## First-run

- [ ] No blank dashboard; a guided "Create your first Proof Run" path is shown.
- [ ] A working result is reachable within minutes with mock providers and no API keys.

## Provider UX

- [ ] Cloud/local/mock boundary is visible in the candidate list.
- [ ] Estimated cost is visible before a run when possible.
- [ ] API keys are never shown after entry and never appear in UI or receipts.
- [ ] Provider errors name the cause and the fix (e.g. "start Ollama or switch to mock").
