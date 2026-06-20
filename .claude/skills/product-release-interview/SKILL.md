---
name: product-release-interview
description: Operator-triggered. Use at the start of the project to turn the opportunity doc into a product brief and release charter. Interviews the operator with AskUserQuestion, challenges assumptions, and locks v0 scope and non-goals.
disable-model-invocation: true
---

# Product release interview

Run this once, at project start, before any code. Bias toward a **local-first Proof
Receipt product** — not a broad cockpit, SaaS platform, or generic model runner.

## Steps

1. Read `docs/opportunity.md`.
2. Write `docs/product-brief.md` containing: target user · core pain · first release
   promise · v0 non-goals · success metrics. Keep it compact — this becomes the main
   working context.
3. Interview the operator with `AskUserQuestion`. Always present **concrete options**
   with a recommended default, never open-ended prompts. Cover at least:
   - Which primary persona to optimize v0 for (consultant / small product team / privacy-first solo builder).
   - First proof pack: text-example comparison only, or include light document ingestion. (Recommend text-only for the first slice.)
   - Which providers to ship first beyond the mock pair (Ollama / OpenAI-compatible / both).
   - What "good enough to ship" means for v0 (the acceptance bar).
   - Receipt formats to prioritize (Markdown + JSON first; HTML next).
4. Challenge any assumption that expands scope. For every requested feature, ask: does
   it help the user create a *better Proof Receipt*? If no, push it to the defer list.
5. Write `docs/release-charter.md` containing: v0 scope · user journey · acceptance
   criteria · tech stack · risks · defer list · first demo script.

## Stop condition

Present the brief and charter, then **stop for operator approval**. Do not start coding.
