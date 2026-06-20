What does a customer happy path look like with this shape of the business? What inputs do they start with, what do they need to do to use Orionfold, what do they get as a deliverable for doing so?

The customer happy path should **not** start with “I own a DGX Spark” or “I want an AI lab.”

It should start with:

> **“I have an AI workflow or model decision, and I don’t know what to trust.”**

That is the core job. Orionfold helps them go from **uncertainty → repeatable proof → promotion decision**.

The uploaded strategy review is right that the paid surface should be a narrow BYO-hardware **proof and promotion** tool, not a broad horizontal cockpit or a DGX-bound product. It also argues that the audience/education engine is the real funnel and that Arena’s telemetry, leaderboard, and replay features should survive as features inside this narrower product. 

## The clean happy path

### 1. Customer arrives through a Field Note

They find a post like:

> **“I tested 7 local models against GPT-4.1 for patent summarization on a DGX Spark.”**
> **“Can a local model beat Claude for investment memo extraction?”**
> **“Which small model is good enough for private website rewrite tasks?”**

They are not buying yet. They are thinking:

> “This is exactly the kind of thing I need to prove for my own workflow.”

The Field Note shows:

* the task,
* the models tested,
* the eval set,
* cost/speed/quality tradeoffs,
* failure cases,
* the final receipt,
* a “run this in Arena” button.

This is where **AI Native Business** does its job: education, trust, curiosity, proof.

---

### 2. Customer brings one concrete AI decision

The customer starts with a **Proof Brief**, not a blank dashboard.

Their inputs are:

| Input                          | Example                                                                                                                                                             |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Task**                       | “Summarize private investment memos,” “rewrite landing pages,” “extract obligations from contracts,” “classify support tickets,” “generate patent claim summaries.” |
| **Private examples**           | 20–200 documents, prompts, transcripts, emails, notes, pages, PDFs, or task examples.                                                                               |
| **Success criteria**           | Accuracy, tone, citation quality, latency, cost, privacy, consistency, refusal behavior.                                                                            |
| **Candidate models/workflows** | Local Llama/Qwen/Mistral, fine-tuned model, Claude/OpenAI/Bedrock fallback, RAG variant, prompt variant.                                                            |
| **Compute**                    | MacBook, Mac Studio, RTX box, DGX Spark, cloud key, Bedrock/SageMaker/Together/OpenRouter.                                                                          |
| **Decision needed**            | “Which one should I trust?” “Is local good enough?” “Did my fine-tune improve?” “Should I pay for cloud?”                                                           |

The key is: they do **not** start by building an AI system. They start by naming a decision.

---

### 3. Orionfold gives them a starter proof pack

Instead of asking them to configure everything from scratch, Orionfold should offer opinionated packs.

Examples:

| Pack                         | Customer job                                                            |
| ---------------------------- | ----------------------------------------------------------------------- |
| **Model Compare Pack**       | Compare 3–5 local/cloud models on the same private task.                |
| **Fine-Tune Proof Pack**     | Prove whether a fine-tune actually improved the baseline.               |
| **RAG Proof Pack**           | Test whether retrieval improved answer quality or just added noise.     |
| **Cost/Speed Pack**          | Compare local versus cloud cost, latency, throughput, and quality.      |
| **Marketing Copy Pack**      | Test brand-voice consistency, factuality, and conversion-style quality. |
| **Investment Research Pack** | Test extraction, summarization, citation, and hallucination behavior.   |
| **Personal Knowledge Pack**  | Test private recall, groundedness, and source attribution.              |

This is where your many interests become useful without fragmenting the business. They become **proof packs**, not separate products.

---

### 4. Customer installs Fieldkit / opens Arena

The ideal onboarding is:

```bash
pip install fieldkit
fieldkit arena up
```

Then they see:

> **Create your first proof run**

They choose:

* a proof pack,
* local folder or sample dataset,
* models to test,
* success criteria,
* whether to include cloud fallback,
* whether results stay private or can generate a shareable proof card.

The user should not need to understand Fieldkit internals. Fieldkit is the engine. Arena is the cockpit.

---

### 5. Arena runs a baseline

Arena creates a baseline before trying to improve anything.

It measures:

| Dimension       | What Arena records                                             |
| --------------- | -------------------------------------------------------------- |
| **Quality**     | Scores, judge notes, pass/fail checks, rubric results          |
| **Cost**        | Local estimated compute cost, cloud token cost, provider spend |
| **Speed**       | Latency, throughput, tokens/sec                                |
| **Reliability** | Variance across repeated runs                                  |
| **Privacy**     | Which data stayed local, which calls went to cloud             |
| **Hardware**    | GPU/CPU/memory/thermal telemetry where useful                  |
| **Failures**    | Bad examples, hallucinations, refusals, unsupported cases      |

This is the first emotional payoff:

> “I finally know how my current setup behaves.”

---

### 6. Customer improves one thing

Now Arena guides the customer through one improvement path:

* try a better prompt,
* try a smaller/faster model,
* try a bigger local model,
* add retrieval,
* fine-tune using Unsloth-style workflow,
* add a cloud fallback,
* quantize the model,
* change context length,
* rerun frozen evals.

The important rule:

> **Every change must run against the same frozen test set.**

That is the difference between tinkering and proof.

---

### 7. Arena produces the deliverable

The main deliverable should be called a:

# **Proof Receipt**

This is the artifact the customer gets.

It should be exportable as HTML, Markdown, JSON, and eventually PDF.

A good Proof Receipt contains:

| Section                     | Contents                                                                       |
| --------------------------- | ------------------------------------------------------------------------------ |
| **Decision**                | “Should I use Qwen local, Claude cloud, or my fine-tuned model for this task?” |
| **Task brief**              | What was tested and why                                                        |
| **Dataset summary**         | Number of examples, source type, privacy status                                |
| **Models/workflows tested** | Model names, versions, quantization, provider, prompt/RAG/fine-tune variants   |
| **Scores**                  | Quality, speed, cost, reliability, privacy                                     |
| **Leaderboard**             | Ranked candidates with tradeoff view                                           |
| **Failure cases**           | Where each model failed                                                        |
| **Winner**                  | Recommended model/workflow                                                     |
| **Promotion decision**      | Ship / keep testing / use cloud fallback / not good enough                     |
| **Repro command**           | How to rerun the test                                                          |
| **Receipt hash/version**    | Frozen test version, run ID, timestamp                                         |
| **Private/shareable mode**  | Full private receipt or sanitized public proof card                            |

The customer walks away with something concrete:

> **“For this workflow, on this machine, with this test set, this model is the best tradeoff. Here is the proof.”**

That is the product.

---

## Three customer happy paths

### Path A: the solo AI builder

**Starts with:**
“I built a local AI workflow, but I don’t know if it is good enough.”

**Inputs:**
A folder of documents, 20–50 test prompts, 3 candidate models, one local machine.

**Does:**
Installs Fieldkit, opens Arena, chooses Model Compare Pack, runs baseline, improves prompt, reruns frozen eval.

**Gets:**
A private leaderboard and Proof Receipt showing which model wins, where it fails, and whether local is good enough.

**Likely paid tier:**
Arena Pro, $199–$399/year.

---

### Path B: the AI consultant / fractional CTO

**Starts with:**
“I need to show a client whether a local/private model can handle their workflow.”

**Inputs:**
Client sample documents, business rubric, local machine or cloud key, 2–3 candidate architectures.

**Does:**
Runs a proof pack, compares local vs cloud, exports sanitized report.

**Gets:**
Client-ready proof report:

* recommended architecture,
* cost estimate,
* risks,
* failure examples,
* next-step plan.

**Likely paid tier:**
Arena Lab, $999–$1,999/year.

This is a very attractive segment because the deliverable helps them sell their own services.

---

### Path C: the learner / AI Native Business customer

**Starts with:**
“I want to learn how to build AI-native systems, not just read theory.”

**Inputs:**
A laptop, sample datasets, course exercises.

**Does:**
Takes a course or workshop, runs Field Notes examples locally, uses Arena to inspect results.

**Gets:**
Learning artifacts:

* completed proof exercises,
* model comparison receipts,
* reusable templates,
* certificate or portfolio-style proof cards.

**Likely paid tier:**
Course/cohort first; Arena Pro later.

This is where education becomes the top of funnel and cash engine.

---

## The “first 15 minutes” should feel like this

The customer should be able to do this quickly:

1. Read a Field Note.
2. Click **Run this proof locally**.
3. Install Fieldkit.
4. Open Arena.
5. Choose a sample proof pack.
6. Run two local models and one cloud model.
7. See a leaderboard.
8. Export a Proof Receipt.

The first win is not training.
The first win is not a beautiful dashboard.
The first win is:

> **“I compared three options on a real task and got a credible answer.”**

## What the customer should not have to do

They should not have to:

* understand all of Fieldkit,
* configure a complex eval framework,
* write YAML from scratch,
* know MLOps terminology,
* set up enterprise observability,
* use DGX Spark specifically,
* trust a generic benchmark,
* upload private data to Orionfold by default.

The magic is that their **private task** becomes a **repeatable test**.

---

## The best customer promise

I would make this the core promise:

> **Bring a task, examples, and candidate models. Orionfold turns them into a private proof run and gives you a receipt that says what is worth trusting.**

That is a happy path people can understand.

## The deliverable stack

At the end of a successful use, the customer gets five things:

1. **Private leaderboard**
   Which model/workflow won and why.

2. **Proof Receipt**
   Repeatable evidence of cost, speed, quality, failures, and privacy boundary.

3. **Promotion recommendation**
   Ship, improve, fine-tune, route to cloud, or reject.

4. **Reusable proof pack**
   Their task becomes a test they can rerun every time the model/prompt/data changes.

5. **Optional public proof card**
   A sanitized shareable artifact for clients, blog posts, internal stakeholders, or community credibility.

That is the compounding asset. Every user creates their own private benchmark. Every benchmark can become a recurring reason to use Arena.

## The business happy path

The clean commercial sequence is:

```text
Free Field Note
   ↓
Run sample proof with Fieldkit
   ↓
Activate in Arena
   ↓
Create first private Proof Receipt
   ↓
Pay for saved history / automation / export / packs
   ↓
Rerun receipts as models and workflows change
   ↓
Upgrade for Lab features or education
```

The paid trigger is not “I want more features.”

The paid trigger is:

> **“This proof is now valuable enough that I want to keep it, rerun it, export it, automate it, or show it to someone.”**

That is the moment Orionfold becomes a business.
