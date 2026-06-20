# Product Brief — Orionfold Proof Receipt (v0)

_Compact working context. Derived from `docs/opportunity.md` + the operator interview
(2026-06-19). After this exists, work from this file — do not reload the full opportunity
doc unless revisiting strategy._

## One-line positioning

> Prove what your AI can do before you trust it.

Orionfold runs private proof tests across local and cloud AI workflows, compares quality,
speed, cost, and failure cases, then exports a repeatable **Proof Receipt** you can keep,
rerun, or share.

## Target user (v0 is tuned for #1)

1. **AI consultant / boutique AI studio** — _primary for v0._ Compares local vs hosted
   models for client work, often under NDA. Needs a client-facing artifact to attach to
   proposals and delivery handoffs.
2. Small product team building RAG/agent workflows (served, not optimized for, in v0).
3. Privacy-first solo builder (served via keyless local + mock runs).

## Core pain

- Public benchmarks are "mere curiosity"; the consultant needs **custom evals on the
  client's real task and data**, on their own hardware/accounts.
- No clean, repeatable, **shareable** way to show *which* model/prompt is worth trusting,
  with evidence, cost, and the local/cloud privacy boundary made explicit.
- Existing eval tools skew cloud-first / enterprise-first; runners (Ollama, LM Studio)
  don't produce a trust artifact.

## First release promise

In one local session, a consultant can:

1. Create a Proof Brief (task + decision question + success criteria + privacy boundary).
2. Import a small test dataset (input/expected text pairs).
3. Configure candidates across **mock**, **Ollama (local)**, and **OpenAI-compatible (hosted)** providers.
4. Run a proof matrix.
5. Inspect the leaderboard and failure cases.
6. Export a **Proof Receipt** as Markdown, HTML, and JSON.

## v0 non-goals

Multi-user SaaS · team auth · billing · cloud DB · hosted projects · native desktop
shell · model training / fine-tuning UI · document ingestion & RAG builder (deferred) ·
agent orchestration · scheduled jobs · marketplace · enterprise RBAC · "every provider"
integrations.

## Success metrics (activation-heavy, not vanity)

- **Time to first proof run** (target: minutes, keyless via mock providers).
- **Proof completion rate** and **% of runs that produce a saved receipt**.
- **Repeat proofs per project** (signal of real workflow use).
- A consultant rates an exported receipt as **client-shareable without edits**.

## Strategic frame

Sit **between** runners (Ollama/LM Studio) and enterprise eval/observability (Langfuse,
Braintrust, Promptfoo): a private, local-first **proof-and-receipt** harness. The
product identity is the **Receipt**, not the breadth of provider support.
