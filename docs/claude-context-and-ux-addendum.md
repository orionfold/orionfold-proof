# Addendum: Context Engineering, Current Docs, and Product UX Quality Bar

## Purpose

This addendum extends the main bootstrap (`CLAUDE.md`). Its job is to make Claude Code
stay current on the stack, use context efficiently, avoid stale assumptions, keep
product design tasteful and usable, verify UI work visually, and build a product surface
that feels deliberate, premium, and operator-ready.

This product is not allowed to feel like a generic AI dashboard, generic SaaS template,
or developer-tool demo. It must feel like a calm, precise instrument for creating and
inspecting AI Proof Receipts.

## Core principle

Claude Code should not carry all context in chat. It should maintain a small, durable,
navigable context system inside the repo.

> Put stable truth in files. Put volatile work state in the plan. Put current external
> facts behind reference links. Put decisions in ADRs. Put repeated workflows into
> skills. Put cross-cutting constraints into path-scoped rules. Put guarantees into hooks.

## Context hierarchy

```text
1. CLAUDE.md (root)            Durable, always-on operating rules. Keep < 200 lines.
2. .claude/rules/*.md          Path-scoped constraints; load when matching files are touched.
3. docs/opportunity.md         Market/product source. Read once, summarize into product-brief.
4. docs/product-brief.md       Compact product strategy. Main product context after discovery.
5. docs/release-charter.md     Current scope, journey, acceptance criteria, non-goals.
6. docs/adr/*.md               Durable architecture and product decisions.
7. docs/ux/*.md                Visual language, usability, accessibility, visual-verification.
8. docs/tech/reference-index.md Current official docs links and update protocol.
9. docs/worklog/*.md           Session summaries, open questions, next steps.
10. tests, e2e, samples        Executable truth for expected behavior.
11. Current prompt             The operator's immediate instruction.
```

When conflict appears: current operator instruction wins for the current task, then
release charter, then product brief, then ADRs, then CLAUDE.md, then older worklogs. Do
not let old chat context override repo files.

## Automated context engineering protocol

At the start of each substantial session:

1. The root `CLAUDE.md` and unscoped rules load automatically — do not re-read them manually.
2. Read `docs/release-charter.md`.
3. Read only the relevant part of `docs/product-brief.md`.
4. Read relevant ADRs only if changing architecture.
5. Read relevant UX docs only if changing user-facing UI or copy.
6. Read `docs/tech/reference-index.md` before adding dependencies or using framework-specific APIs.
7. Summarize the minimal task context in your plan.
8. Do not reload the full opportunity document unless the operator explicitly asks or
   product strategy is being revisited.

Use focused file reads and `@`-references. Hand large explorations to a subagent so they
do not fill the main window. Run `/clear` between unrelated tasks.

## Context packet format

For each task, produce a compact context packet before implementation:

```markdown
## Context packet

### User outcome
What user-visible outcome this task improves.

### Current release promise
The relevant line from docs/release-charter.md.

### Files likely involved
- file 1
- file 2

### Constraints
- local-first
- no hosted user data
- no enterprise features
- no broad dashboard unless required

### Verification
- tests to run
- browser route + states to inspect (screenshot)
- receipt artifact to export if relevant
```

Keep it short.

## Current-docs protocol

Before using a framework feature, check whether the repo has an up-to-date local reference.

1. Look in `docs/tech/reference-index.md`.
2. If the relevant docs are stale or missing, fetch current guidance (Context7 MCP or web) — scoped, not bulk.
3. Add a short note to `docs/tech/docs-update-log.md` (URL, date checked, version, small repo-relevant notes).
4. Do not copy huge docs into the repo.

## UX north star

> A calm instrument panel for proving AI work, not a noisy dashboard for watching AI theater.

Design adjectives: precise, calm, confident, technical but humane, premium, readable,
private, evidence-first, quietly distinctive.

Avoid: generic SaaS cards everywhere, purple-gradient AI cliché, noisy dashboards,
confetti, giant meaningless hero copy inside the app, terminal-only roughness, fake
"autonomous agent" theatrics, and decorative icons that do not improve scanning.

## Product surface metaphor

> A lab bench plus a signed receipt.

The UI should help the user define the test, run the proof, inspect the evidence, decide
what to trust, and export the receipt. Every screen must support one of those jobs.

## Core UX objects

```text
Project · Proof Brief · Dataset · Candidate · Proof Run · Leaderboard · Failure Case · Proof Receipt
```

Do not invent too many nouns. If a feature cannot attach to one of these objects,
reconsider it.

## Primary app layout

```text
Left rail:    Projects · Proof Runs · Datasets · Candidates · Receipts · Settings
Main workspace: the current task — create, run, compare, inspect, export.
Right inspector: context, metadata, config, selected failure case, receipt summary.
```

Rules: the main workspace always has the clearest visual weight; the right inspector is
secondary; the left rail is quiet. Avoid nested sidebars, card mosaics, and more than one
primary CTA per view.

## First-run UX

Do not expose a blank dashboard. Show a guided first-run path:

```text
Create your first Proof Run
  1. Choose a sample or bring your own examples.
  2. Pick two candidates.
  3. Run the proof.
  4. Review the leaderboard.
  5. Export your Proof Receipt.
```

The user should see a working result within minutes, even without API keys, using
deterministic mock providers.

## Empty states

Every empty state must answer: What is this area? Why does it matter? What should I do
next? Can I try a sample?

Bad: "No proof runs yet."

Good: "Proof Runs compare candidates on the same frozen examples so you can decide what
to trust. Start with the sample run or create your own."

## Information hierarchy

1. Decision
2. Winner / recommendation
3. Evidence summary
4. Leaderboard
5. Failure cases
6. Raw run details
7. Export/repro metadata

The user should not have to inspect raw logs to understand the outcome.

## States every interactive view must have

* empty state
* loading state
* error state
* populated state

A `docs/ux/copy-deck.md` standardizes product nouns, button labels, status labels,
recommendation labels, and error-message patterns.

## Error-message standards

Errors must be specific, recoverable, calm, and privacy-safe.

Bad: "Something went wrong."

Good: "Ollama is not reachable at localhost:11434. Start Ollama or switch to the mock provider."

Bad: "Provider failed."

Good: "The OpenAI-compatible provider returned 401 Unauthorized. Check the API key. The
key was not stored in the receipt."

Do not log secrets or expose keys in UI, receipts, screenshots, or worklogs.

## AI-provider UX

* API keys are never shown after entry.
* API keys are never written to receipts.
* Cloud calls are opt-in.
* Estimated cost is visible before run when possible.
* The cloud/local boundary is visible in the candidate list.
* Provider errors are actionable.

Labels: "Local", "Cloud", "Mock", "OpenAI-compatible", "Ollama", "LM Studio", "Bedrock
later". Do not overbuild provider integrations in v0.

## Receipt artifact standards

Markdown: clean headings, tables for the leaderboard, bullets for failure cases, no
app-only UI language.

HTML: self-contained if practical, printable, readable without app CSS, no external
tracking, no secrets, includes timestamp and config hash.

JSON: machine-readable manifest, versioned schema, no secrets, predictable field names.

## Tests as context

Tests are Claude Code's most important compact context. Every product behavior should
eventually have an executable fixture.

Create fixtures for: simple summarization proof, extraction proof, classification proof,
mock provider success, mock provider failure, provider timeout, empty dataset, malformed
row, failed receipt export.

Use test names that describe product behavior:

```text
test_receipt_marks_cloud_cost_as_estimated
test_proof_run_keeps_dataset_examples_frozen
test_provider_key_never_appears_in_receipt
```

Not: `test_utils`, `test_api`, `test_misc`.

## Playwright tests

Create an e2e test for the happy path:

```text
e2e/proof-run.spec.ts
  - opens app
  - starts sample proof run
  - sees leaderboard
  - opens failure case
  - exports receipt
```

Add screenshots only when useful. Do not create brittle screenshot tests for every minor
layout.

## Definition of done for user-facing work

A user-facing change is done only when:

* the behavior works,
* copy is clear,
* empty/loading/error states exist,
* the keyboard path works for the core action,
* the browser route has been inspected with a screenshot,
* tests were added or consciously deferred,
* no secrets are exposed,
* docs or screenshots were updated if needed,
* the diff was reviewed by a fresh subagent,
* product impact is summarized in the worklog.

## Final instruction

> The user is not here to watch AI run.
> The user is here to decide what AI to trust.

Design every workflow, screen, label, and receipt around that decision.
