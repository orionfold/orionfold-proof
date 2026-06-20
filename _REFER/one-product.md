Now imagine Orionfold was starting from scratch today. Based on this customer journey how would you recommend designing one product, the features, the technology stack, the pricing?

If Orionfold started from scratch today, I would **not** start with “Arena as a broad AI lab.” I would start with **one narrow product**:

# **Orionfold Arena**

## Private AI proof runs for local and hybrid models

The product promise:

> **Bring a task, examples, and candidate models. Orionfold tells you what is worth trusting — with a private, repeatable Proof Receipt.**

This incorporates the critique from the strategy review: the strongest path is not a horizontal cockpit or DGX-only tool, but a narrow BYO-hardware **proof/promotion product** with AI Native Business and Field Notes as the audience/trust engine. 

## 1. Product shape

The first product should be **local-first software with a paid local web cockpit**.

Not:

* native Mac App Store app,
* full SaaS where users upload private data,
* generic local chat app,
* general AI agent builder,
* enterprise eval platform,
* DGX Spark-only bundle.

The product is:

> **A local/hybrid evaluation and promotion system for AI workflows.**

The core object is not a model.
The core object is a **Proof Run**.

A Proof Run answers:

> “For this task, with these examples, across these models/workflows, what should I trust?”

## 2. The customer starts with these inputs

The onboarding should ask for five things:

| Input              | Example                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| **Task**           | “Summarize investment memos,” “rewrite landing pages,” “classify support tickets,” “extract obligations from contracts.” |
| **Examples**       | 20–100 prompts, documents, expected answers, notes, PDFs, URLs, transcripts, or CSV rows.                                |
| **Success rubric** | Accuracy, citation quality, tone, cost, speed, privacy, consistency, groundedness.                                       |
| **Candidates**     | Local Qwen/Llama/Mistral, prompt variants, RAG variants, fine-tuned model, Claude/OpenAI/Bedrock fallback.               |
| **Compute**        | Mac, RTX workstation, DGX Spark, local Ollama/LM Studio, or cloud API keys.                                              |

The customer should never start from a blank dashboard. They should start from:

> **Create a Proof Run**

## 3. MVP feature set

Build only the features needed to get the customer to one valuable Proof Receipt.

### P0: must exist at launch

| Feature                       | Why it matters                                                                             |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| **Proof Brief wizard**        | Turns vague customer intent into a structured eval.                                        |
| **Dataset/example loader**    | Folder, CSV, Markdown, JSONL, PDF text, pasted examples.                                   |
| **Candidate model connector** | Ollama, LM Studio OpenAI-compatible endpoint, OpenAI-compatible APIs, maybe Bedrock later. |
| **Rubric builder**            | User defines what “good” means. Start simple.                                              |
| **Frozen eval set**           | Same examples rerun every time. This is the trust primitive.                               |
| **Model/workflow runner**     | Runs candidates against examples.                                                          |
| **Leaderboard**               | Quality, speed, cost, privacy, failure rate.                                               |
| **Failure browser**           | Shows where each candidate failed.                                                         |
| **Proof Receipt export**      | Markdown + HTML + JSON. This is the deliverable.                                           |
| **Local project history**     | Saved runs on the user’s machine.                                                          |

That is enough.

Do **not** build training queue, complex telemetry, model marketplace, team collaboration, agent orchestration, or domain apps in version one.

### P1: after first paying users

| Feature                            | Why                                                               |
| ---------------------------------- | ----------------------------------------------------------------- |
| **Receipt hash / signed manifest** | Makes the proof feel durable and auditable.                       |
| **Cloud spend caps**               | Important for hybrid local/cloud comparison.                      |
| **Rerun button**                   | Re-test when model, prompt, data, or runtime changes.             |
| **Proof Packs**                    | Opinionated templates for marketing, investing, RAG, PKM, AI ops. |
| **Sanitized public proof card**    | Lets users share results without exposing private data.           |
| **Batch runs**                     | Useful for consultants and advanced builders.                     |
| **Branded report export**          | Paid feature for consultants.                                     |

### P2: only after product pull

| Feature                | Build only if users demand it                                               |
| ---------------------- | --------------------------------------------------------------------------- |
| Fine-tuning workflow   | Only if proof runs show people need model improvement, not just comparison. |
| Hardware telemetry     | Useful for DGX/RTX users, but not the core value.                           |
| Hosted receipt gallery | Only for sanitized/shareable receipts.                                      |
| Team workspace         | Only if small teams appear organically.                                     |
| Native desktop wrapper | Only if local web app distribution becomes a blocker.                       |

## 4. The deliverable

The customer should end with a **Proof Receipt**.

Example:

> **Proof Receipt: Investment Memo Summarization**
> Tested 50 private memos across Qwen local, Llama local, Claude cloud, and a custom prompt variant.
> Winner: Qwen local for privacy/cost; Claude cloud fallback for complex edge cases.
> Recommendation: Ship hybrid route. Keep private memos local by default. Use cloud fallback only above complexity threshold.

The receipt contains:

| Section                | Contents                                           |
| ---------------------- | -------------------------------------------------- |
| **Decision**           | What question was being answered.                  |
| **Task**               | What workflow was tested.                          |
| **Dataset summary**    | Number/type of examples, privacy boundary.         |
| **Candidates**         | Models, prompts, RAG variants, cloud providers.    |
| **Leaderboard**        | Quality, cost, speed, reliability, privacy.        |
| **Failures**           | Where each candidate broke.                        |
| **Winner**             | Best tradeoff.                                     |
| **Promotion decision** | Ship, improve, fine-tune, add fallback, or reject. |
| **Repro info**         | Run ID, config, timestamp, versions.               |
| **Exports**            | HTML, Markdown, JSON, sanitized card.              |

That receipt is the product’s emotional center.

## 5. Technology stack

I would keep it boring, local-first, Python-first.

### Core

| Layer                    | Recommendation                                                      |
| ------------------------ | ------------------------------------------------------------------- |
| **Language**             | Python                                                              |
| **Package manager**      | `uv`                                                                |
| **CLI**                  | Typer + Rich                                                        |
| **Local API**            | FastAPI                                                             |
| **Local UI**             | Vite + React + TypeScript                                           |
| **UI components**        | shadcn/ui + Tailwind                                                |
| **State/query**          | TanStack Query                                                      |
| **Storage**              | SQLite for projects/runs; local file system for artifacts           |
| **Analytics inside app** | DuckDB for run summaries and leaderboard queries                    |
| **Schemas**              | Pydantic                                                            |
| **Eval format**          | JSONL + YAML/JSON config                                            |
| **Exports**              | Markdown, HTML, JSON; PDF later                                     |
| **Model connectors**     | OpenAI-compatible API first; Ollama; LM Studio; Bedrock later       |
| **Packaging**            | `pipx install orionfold-arena` or `uv tool install orionfold-arena` |
| **Command**              | `orionfold arena up`                                                |

The app should open a local browser UI at something like:

```bash
orionfold arena up
```

Do not start with Electron.
Do not start with App Store.
Do not start with Kubernetes.
Do not start with a hosted SaaS backend.

### Hosted backend

Keep the hosted backend tiny:

| Hosted function              | Needed?            |
| ---------------------------- | ------------------ |
| License activation           | Yes                |
| Product updates              | Yes                |
| Docs/templates registry      | Yes                |
| Sanitized public proof cards | Later              |
| User data upload             | No, not by default |
| Team SaaS workspace          | Not at launch      |

Use whatever is fastest for you: Supabase + Stripe/Lemon Squeezy/Paddle + Cloudflare/Vercel. Since tax/VAT can become annoying for a solo founder, Paddle or Lemon Squeezy may be simpler than raw Stripe for digital product sales.

## 6. Product packaging

I would ship one product with three visible surfaces:

### A. Free open core

Name: **Fieldkit**

Purpose: credibility, adoption, trust.

Includes:

* CLI proof runner,
* local eval primitives,
* receipt schema,
* sample proof packs,
* open examples from Field Notes.

Command:

```bash
fieldkit proof run
```

This should be open source.

### B. Paid local cockpit

Name: **Orionfold Arena**

Purpose: recurring revenue.

Includes:

* local UI,
* project history,
* proof run wizard,
* leaderboard,
* failure browser,
* exportable receipts,
* cloud/local comparison,
* paid proof packs.

Command:

```bash
orionfold arena up
```

This can be source-available or closed paid software powered by the open Fieldkit core.

### C. Field Notes / AI Native Business

Purpose: audience and education.

Every Field Note should have:

> **Run this proof in Fieldkit**
> **Open this proof in Arena**
> **Download the receipt template**

## 7. Pricing

I would not make the main offer one-time only. You need recurring revenue.

### Recommended pricing

| Tier                    |                                 Price | Buyer                          | Includes                                                                             |
| ----------------------- | ------------------------------------: | ------------------------------ | ------------------------------------------------------------------------------------ |
| **Free**                |                                    $0 | Learners, OSS users            | Fieldkit CLI, sample packs, single-run receipts, local-only basics                   |
| **Arena Pro**           |            **$249/year** or $29/month | Solo builders                  | Local UI, saved projects, unlimited receipts, leaderboard, exports, model comparison |
| **Arena Lab**           |                         **$999/year** | Consultants, serious builders  | Client projects, branded reports, batch runs, cloud cost caps, custom proof packs    |
| **Arena Field Edition** | **$799 one-time + $199/year updates** | DGX Spark / workstation owners | Reference setup, hardware-specific templates, proven local stack, priority guides    |
| **Proof Sprint**        |            **$1,500–$3,000 one-time** | Early high-intent users        | You help them create their first proof receipt; credit toward Lab                    |

The key paid trigger:

> “I created a proof that is valuable enough to save, rerun, export, automate, or show someone.”

That is when they pay.

## 8. What I would launch first

The first public version should have only one killer workflow:

# **Compare local vs cloud on your own task**

That is understandable, timely, and useful.

Launch promise:

> **In 30 minutes, compare three AI options on your own private examples and get a Proof Receipt showing which one is worth trusting.**

Supported candidates at launch:

* Ollama local model
* LM Studio local OpenAI-compatible endpoint
* OpenAI-compatible cloud endpoint
* maybe Bedrock shortly after, given your AWS credibility

Supported tasks:

* summarization,
* extraction,
* classification,
* rewrite,
* Q&A with citations.

Avoid agentic workflows at first. They add too much variance. Start with tasks where proof is easy to understand.

## 9. The first proof packs

Start with three packs, not ten.

### 1. Model Compare Pack

For any user.

> “Which model should I use for this task?”

### 2. RAG Proof Pack

For AI builders and consultants.

> “Did retrieval actually improve answer quality?”

### 3. Cost/Privacy Tradeoff Pack

For local/hybrid users.

> “Is local good enough, or do I need cloud fallback?”

Your domain interests become examples inside these packs:

* marketing rewrite example,
* investment memo example,
* personal knowledge example,
* website copy example.

But they are not separate apps.

## 10. What I would avoid for 12 months

Do not build:

* marketing agent,
* investing agent,
* PKM app,
* website builder,
* AI coworker suite,
* general-purpose agent harness,
* native desktop app,
* multi-user enterprise workspace,
* marketplace,
* complex training studio,
* full observability platform,
* every hardware target.

Those are all expansion paths after the proof product works.

## 11. Brand and site if starting fresh

I would use one main commercial domain:

# **orionfold.com**

Primary nav:

* Arena
* Fieldkit
* Field Notes
* Pricing
* About

AI Native Business becomes a section or sub-brand:

> **AI Native Business by Orionfold**
> The field manual behind Arena.

I would not start with two equal domains. The two-property setup can work, but from scratch I would keep authority and buyer attention concentrated.

## 12. The homepage message

The homepage should say:

# **Prove what your AI can do before you trust it.**

Subhead:

> Orionfold Arena runs private proof tests across local and cloud models, compares cost, speed, quality, and failure cases, then gives you a repeatable receipt for what is worth shipping.

Primary CTA:

> **Create your first proof run**

Secondary CTA:

> **Read the Field Notes**

## 13. The 90-day build plan

### Days 0–30

Build:

* Fieldkit CLI proof runner,
* JSONL examples,
* OpenAI-compatible connector,
* Ollama/LM Studio connector,
* Markdown/HTML receipt export.

Launch:

* 3 Field Notes using your own workflows.
* 1 landing page.
* 1 waitlist/preorder.

### Days 31–60

Build:

* local Arena UI,
* proof brief wizard,
* leaderboard,
* failure browser,
* saved project history.

Launch:

* Arena Pro preorder,
* 10 concierge Proof Sprints,
* first paid users.

### Days 61–90

Build:

* paid license unlock,
* branded report export,
* cloud/local comparison,
* first three proof packs.

Launch:

* public demo video,
* Field Notes newsletter,
* Arena Pro annual plan.

## The final product definition

If starting from zero, I would define Orionfold like this:

> **Orionfold Arena is a local-first proof system for AI builders. It turns your examples, models, prompts, and cloud keys into repeatable proof receipts so you can decide what to trust, improve, or ship.**

That is focused enough for a solo founder.

It still lets you tinker.
It still leverages DGX Spark.
It still uses Fieldkit.
It still feeds Field Notes.
It still supports education.
But the product itself has one clear job:

# **Prove the AI works.**
