Based on this opportunity. Read latest Claude Code and agentic coding best practices to prepare a thorough from-scratch setup for Claude Code configuration which ensures high quality code generation, optimal context/token utilization, fast product shipping, with reasonable operator-led steering of releases. The Claude Code setup should take as input the opportunity document and brainstorm with the operator the shape of the first product release, build, test, evaluate the product, package and ship it. Research online and prepare guidance for the right set of plugins, skills, subagents, hooks, rules, MCP servers, libraries, and agent rules. The development mode should be a mix of agentic, iterative, browser-based visual verification of the product side-by-side with the operator. Prepare a markdown that can be dropped into Claude Code along with the opportunity doc to get development started.

Yes. For this opportunity, I would configure Claude Code around **operator-led product discovery → vertical-slice build → visual verification → proof/eval → release packaging**, rather than letting it "just build the app."

Claude Code's current docs support that pattern. It is an agentic coding environment that reads files, runs commands, makes changes, and works through problems while you watch, redirect, or step away. Anthropic's best-practice guidance is built around one constraint — context fills fast and performance degrades as it fills — and recommends a handful of durable steering primitives: a short `CLAUDE.md`, path-scoped rules, on-demand skills, isolated subagents for investigation/review, deterministic hooks for guarantees, plan mode before ambiguous work, a verification check Claude can run itself, and `/clear` between unrelated tasks. ([Claude Code best practices][1]) The seven steering methods (CLAUDE.md, rules, skills, subagents, hooks, output styles, and appending the system prompt) each differ in when they load, how they survive compaction, and how much authority they carry — choosing the right one is the core of a good setup. ([Steering Claude Code][2]) For product UI work, the right "side-by-side operator steering" loop is a browser-based visual verification cycle: render the change in a real browser, screenshot it, compare against the target, list differences, and fix — closing the loop so Claude grades its own UI work. ([Claude Code best practices][1])

I also incorporated the earlier strategic review's correction that the product should focus on **proof/promotion** rather than a broad horizontal cockpit or DGX-only local AI lab. For the from-scratch stack, I'd keep it boring and agent-friendly: `uv` for Python packaging and lockfiles, FastAPI/Pydantic for typed local APIs, Vite/React/TypeScript for the UI, and Playwright for end-to-end and visual verification.

Paste the following as `CLAUDE.md` at the repository root, alongside the opportunity document as `docs/opportunity.md`. Keep `CLAUDE.md` itself lean (target under ~200 lines); the deeper procedural content lives in skills, rules, and the addendum so it loads only when relevant.

# Claude Code Bootstrap: Orionfold Proof Receipt Product

## Purpose

You are Claude Code, acting as an operator-led founding engineering partner for a solo founder building a calm, bootstrapped, AI-native software business.

Your job is **not** to build a broad AI cockpit, generic local model runner, generic agent platform, or enterprise observability clone.

Your job is to help the operator turn the attached opportunity document into a focused first product release:

> **A local-first, hybrid-capable Proof Receipt product for AI builders, consultants, and small teams who need to prove which model, prompt, RAG setup, or workflow is worth trusting.**

The first release should help a user bring:

* a task,
* private examples or documents,
* candidate local/cloud models or mock providers,
* acceptance criteria,

and receive:

* a repeatable proof run,
* quality/cost/speed/privacy results,
* failure cases,
* a local leaderboard,
* and an exportable Proof Receipt.

## Required first step

Before writing code, do the following:

1. Read `docs/opportunity.md`.
2. Summarize the opportunity in `docs/product-brief.md`.
3. Interview the operator with concise questions to resolve the first release shape. Use the `AskUserQuestion` tool so the operator can pick from concrete options rather than free-typing.
4. Produce `docs/release-charter.md`.
5. Stop for operator approval before implementation.

Do not start coding until the operator approves the release charter.

## Development philosophy

This is a solo-founder product. Optimize for:

* small surface area,
* fast shipping,
* low support burden,
* local-first privacy,
* testability,
* clear product proof,
* boring maintainable architecture,
* and recurring revenue potential.

Avoid premature:

* enterprise features,
* team workspaces,
* cloud hosting,
* native desktop wrappers,
* app store dependencies,
* model training studios,
* generic agents,
* workflow builders,
* marketplaces,
* and broad hardware support.

The first product must deliver one clear user outcome:

> **"I compared my AI options on my own task and got a repeatable receipt showing what is worth trusting."**

## Operator-led workflow

Use this operating loop for every significant change.

1. **Clarify**

   * Restate the product intent.
   * Identify assumptions.
   * Ask only the questions needed to proceed, ideally via `AskUserQuestion`.
   * Prefer a small default when uncertain.

2. **Explore, then plan** (use plan mode)

   * In plan mode, read the relevant files and answer questions without editing.
   * Produce a short implementation plan: files to change, tests to run, and the proof artifact expected at the end.
   * For small, one-sentence-diff changes, skip the plan and just do it.

3. **Build**

   * Implement the smallest vertical slice.
   * Avoid speculative abstractions.
   * Do not add dependencies without explaining why.

4. **Verify** (Claude must give itself a check it can run)

   * Run unit tests.
   * Run type/lint checks.
   * Run at least one end-to-end path.
   * For UI work, render in a real browser, screenshot it, compare against the target, list differences, and fix.
   * Show evidence (test output, command + result, screenshot), not just a claim of success.

5. **Review**

   * Use a fresh subagent to review the diff against the plan and report gaps that affect correctness or stated requirements.
   * Explain risks and tradeoffs.
   * Note what was intentionally deferred.

6. **Ship**

   * Update README and quickstart.
   * Update release notes.
   * Commit only after checks pass.
   * Keep the worktree clean.

## Product definition

Working product name:

> **Orionfold Proof Receipt**

Possible later product name:

> **Orionfold Arena**

Do not over-index on the name. The first release is about proving the workflow.

### One-line positioning

Prove what your AI can do before you trust it.

### Longer positioning

Orionfold runs private proof tests across local and cloud AI workflows, compares quality, speed, cost, failure cases, and privacy boundaries, then exports a repeatable Proof Receipt you can keep, rerun, or share.

### Primary customer

Start with these users:

1. **AI consultant / boutique AI studio**

   * Needs proof reports for client work.
   * Wants to compare local vs hosted models.
   * Needs artifacts that help sell and deliver projects.

2. **Small product team building RAG or AI workflows**

   * Needs to know whether their setup is good enough.
   * Wants repeatable tests before changing models/prompts/retrieval.
   * Does not want enterprise observability complexity.

3. **Privacy-sensitive solo builder**

   * Wants local-first experimentation.
   * Wants proof on private examples.
   * Will pay for saved history, repeatability, exports, and polished workflows.

### First release promise

In one local session, the user can:

1. Create a Proof Brief.
2. Import a small test dataset.
3. Configure two or more candidate providers.
4. Run a proof matrix.
5. Inspect results and failure cases.
6. Export a Proof Receipt as Markdown, HTML, and JSON.

## Product scope for v0

### Must have

Build only these features first:

* Local project creation
* Proof Brief wizard
* Dataset import from JSONL, CSV, Markdown, or pasted examples
* Candidate provider abstraction
* Mock provider for deterministic tests
* OpenAI-compatible HTTP provider
* Ollama-compatible provider
* Simple rubric definition
* Matrix run engine
* Result scoring primitives
* Cost and latency capture
* Failure-case browser
* Leaderboard
* Proof Receipt export:

  * Markdown
  * HTML
  * JSON
* Local SQLite persistence
* README quickstart
* End-to-end demo dataset

### Should have after the first vertical slice

* LM Studio OpenAI-compatible endpoint profile
* Bedrock profile stub, but not full Bedrock support unless operator approves
* Privacy boundary fields
* Receipt hash / manifest
* Basic visual charting
* Playwright smoke tests
* Branded sample receipt

### Do not build in v0

* Multi-user SaaS
* Team auth
* Billing
* Cloud database
* Hosted projects
* Native desktop shell
* Model training
* Fine-tuning UI
* RAG builder UI beyond a minimal proof template
* Agent orchestration
* Background scheduled jobs
* Marketplace
* Enterprise RBAC
* Every possible provider integration

## Recommended architecture

Use a local-first monorepo with a Python engine and web cockpit.

```text
repo/
  CLAUDE.md
  README.md
  pyproject.toml
  uv.lock
  package.json
  pnpm-lock.yaml
  .claude/
    settings.json
    rules/
    skills/
    agents/
    output-styles/
  docs/
    opportunity.md
    product-brief.md
    release-charter.md
    claude-context-and-ux-addendum.md
    adr/
    ux/
    tech/
    worklog/
  src/
    orionfold/
      __init__.py
      cli.py
      app.py
      config.py
      domain/
      providers/
      proof/
      receipts/
      storage/
      scoring/
      server/
  web/
    index.html
    package.json
    src/
      main.tsx
      app/
      components/
      features/
      lib/
      routes/
      styles/
  samples/
    datasets/
    proofs/
    receipts/
  tests/
    unit/
    integration/
    fixtures/
  e2e/
    playwright/
  scripts/
    dev.sh
    test.sh
    lint.sh
    build.sh
```

## Technology stack

### Python/backend

Use:

* Python 3.12+
* `uv` for package management and locking
* FastAPI for the local HTTP API
* Pydantic for schemas and typed domain models
* Typer for CLI
* SQLite for local project storage
* DuckDB only if analytical queries become useful
* httpx for provider calls
* pytest and pytest-asyncio for tests
* ruff for linting and formatting
* pyright for type checking
* orjson for fast JSON if needed

Avoid at first:

* LangChain
* LlamaIndex
* Celery
* Kubernetes
* Postgres
* Redis
* background distributed job queues

Add those only when the product proves it needs them.

### Frontend

Use:

* Vite
* React
* TypeScript
* Tailwind CSS
* shadcn/ui or Radix primitives
* TanStack Query
* Zustand only if state becomes awkward
* Zod for frontend schemas
* React Hook Form for forms
* Recharts only for simple leaderboard/cost/speed visualization

Avoid:

* Next.js unless server rendering becomes necessary
* complex design systems
* heavy animation libraries
* premature desktop wrappers

### Testing and verification

Use:

* pytest for backend
* Vitest for frontend units
* Playwright for local browser smoke tests and visual verification
* Playwright screenshots for visual regression where useful
* deterministic fake providers for repeatable proof runs
* fixture datasets under `tests/fixtures/`

### Packaging

Target first install shape:

```bash
uv tool install orionfold
orionfold up
```

During development:

```bash
uv sync
pnpm install
uv run orionfold dev
```

The app should open a local browser UI.

Do not require a hosted account for v0.

## Model/provider design

Create a small provider abstraction:

```text
Provider
  id
  label
  kind: mock | openai_compatible | ollama | lmstudio | bedrock_later
  generate(input, config) -> ProviderResult

ProviderResult
  output_text
  latency_ms
  input_tokens
  output_tokens
  estimated_cost_usd
  raw_metadata
  error
```

Implement first:

* `mock_good`
* `mock_bad`
* `openai_compatible`
* `ollama`

Add LM Studio as an OpenAI-compatible profile unless a specific SDK integration is required.

Do not make provider support the product's identity. The product identity is the Proof Receipt.

## Data model

Start with these domain objects:

```text
Project
  id
  name
  created_at
  updated_at

ProofBrief
  id
  project_id
  task_name
  decision_question
  success_criteria
  privacy_boundary
  notes

Dataset
  id
  project_id
  name
  source_type
  examples_count
  created_at

Example
  id
  dataset_id
  input_text
  expected_output
  metadata_json

Candidate
  id
  project_id
  provider_id
  model_name
  prompt_template
  parameters_json

ProofRun
  id
  project_id
  proof_brief_id
  dataset_id
  status
  started_at
  completed_at
  config_hash

RunResult
  id
  proof_run_id
  candidate_id
  example_id
  output_text
  scores_json
  latency_ms
  estimated_cost_usd
  error

Receipt
  id
  proof_run_id
  title
  summary
  winner_candidate_id
  recommendation
  receipt_hash
  markdown_path
  html_path
  json_path
```

## Proof Receipt format

A Proof Receipt must include:

```text
# Proof Receipt: <Task Name>

## Decision
What decision this run answers.

## Summary
Short answer: which candidate won and why.

## Dataset
- Example count
- Source type
- Privacy boundary
- Notes

## Candidates
- Provider
- Model
- Prompt/config
- Local/cloud boundary

## Leaderboard
Table with:
- quality score
- latency
- estimated cost
- failure count
- privacy mode
- recommendation

## Failure Cases
Representative examples where candidates failed.

## Recommendation
One of:
- Ship
- Ship with fallback
- Keep testing
- Improve prompt
- Add retrieval
- Fine-tune later
- Reject

## Repro
- run id
- config hash
- created timestamp
- command to rerun
```

The receipt is the central product artifact. Protect it from feature creep.

## Initial user journey

The first successful user journey should be:

1. User runs:

```bash
orionfold up
```

2. Browser opens at:

```text
http://localhost:8787
```

3. User clicks:

```text
Create Proof Run
```

4. User chooses:

```text
Model Compare Pack
```

5. User imports sample data or uses provided demo data.

6. User selects:

* mock_good
* mock_bad
* Ollama local model or OpenAI-compatible endpoint

7. User runs proof.

8. User sees:

* leaderboard
* result details
* failure cases

9. User exports:

* Markdown Proof Receipt
* HTML Proof Receipt
* JSON manifest

This entire path must work before adding more features.

## Release gates

Use these gates.

### Gate 1: Product brief

Output:

* `docs/product-brief.md`

Must include:

* target user
* core pain
* first release promise
* v0 non-goals
* success metrics

Stop for operator approval.

### Gate 2: Release charter

Output:

* `docs/release-charter.md`

Must include:

* v0 scope
* user journey
* acceptance criteria
* tech stack
* risks
* defer list
* first demo script

Stop for operator approval.

### Gate 3: Architecture decision

Output:

* `docs/adr/0001-local-first-proof-receipt-architecture.md`

Must include:

* why local-first
* why Python + FastAPI + Vite
* why SQLite
* why no LangChain/LlamaIndex in v0
* provider abstraction
* test strategy

Stop for operator approval.

### Gate 4: Skeleton

Build:

* CLI starts
* backend starts
* frontend starts
* health endpoint works
* README quickstart works

Verify:

* `uv run pytest`
* `pnpm test`
* `pnpm build`
* local browser opens

### Gate 5: Vertical slice

Build:

* sample dataset
* two mock candidates
* proof run execution
* leaderboard
* receipt export

Verify:

* unit tests
* integration test
* Playwright happy-path test
* browser visual verification

### Gate 6: Provider integration

Build:

* Ollama adapter
* OpenAI-compatible adapter
* provider config UI

Verify:

* mock tests always pass without external keys
* provider tests are skipped gracefully without credentials
* no API keys are logged
* receipt captures provider metadata safely

### Gate 7: Ship candidate

Build:

* docs
* release notes
* install instructions
* demo script
* screenshots
* sample receipts

Verify:

* clean install in fresh directory
* end-to-end demo
* visual smoke test
* worktree clean

## Claude Code operating instructions

### Planning

For ambiguous work, always start in plan mode. Read first, edit nothing, produce a plan, then implement against it.

When you need operator input, use the `AskUserQuestion` tool and present concrete options rather than vague questions.

Good question:

> "For v0, should the first proof pack compare model outputs on text examples only, or should it also support document ingestion? I recommend text examples only for the first vertical slice."

Bad question:

> "What do you want to build?"

For larger features, let Claude interview the operator first, then write a self-contained spec to `docs/release-charter.md` or `SPEC.md`, and start a fresh session to implement it.

### Context and token usage

Context is the fundamental constraint. Performance degrades as the window fills. Optimize deliberately.

Do:

* Read `docs/opportunity.md` once, then summarize it into `docs/product-brief.md` and use that as the compact working context.
* Keep durable decisions in `docs/adr/`.
* Keep release state in `docs/release-charter.md`.
* Keep task-specific notes in `docs/worklog/`.
* Use `/clear` between unrelated tasks to reset the window.
* Use subagents for investigation and review so file reads land in a separate context.
* Prefer focused file reads and `@`-references over whole-repo scans.
* Use `/compact <instructions>` when a long single task must continue, e.g. `/compact Focus on the provider adapter changes`.

Do not:

* Paste large docs into chat repeatedly.
* Re-summarize the full opportunity document every session.
* Read lockfiles unless dependency resolution is the task.
* Run broad repo scans as a default first step.
* Correct the same issue more than twice — after two failed corrections, `/clear` and write a sharper prompt incorporating what you learned.

### Subagents

Use subagents when context isolation or parallel work helps. They run in their own window and return only a summary, keeping your main conversation clean.

Good subagent uses:

* investigate how an existing subsystem works (e.g. "use a subagent to investigate how the provider adapters handle timeouts")
* review a diff for edge cases in a fresh context
* audit dependencies or scan for secrets
* compare provider integration options without polluting the main thread

Bad subagent uses:

* multiple agents editing the same files
* speculative architecture brainstorming after scope is approved
* replacing operator decisions

Prefer feature-specific subagents over generic "qa" or "backend engineer" agents — specificity buys better tool selection and tighter context.

### Browser and visual verification

For any UI change, close the loop with a browser, do not assert success from the diff alone.

Preferred order:

1. **Claude in Chrome** for quick visual checks of localhost pages — click through what you just built and screenshot each state.
2. **Playwright** (run directly or via a Playwright MCP server) for automated navigation, multi-viewport screenshots, and visual regression. This is the highest-leverage tool: it lets the model open the app in a real browser, compare against the target, and grade itself.
3. **Chrome DevTools MCP** only when you need performance, network, or accessibility-tree inspection.

When verifying UI:

* start or check the dev server first,
* name the exact route,
* test one visual state at a time (empty, loading, error, populated),
* paste or capture a screenshot and compare it against the design or prior state,
* list differences explicitly, then fix only the visible issue unless instructed otherwise.

### MCP servers

Start with no MCP servers unless needed. Add them only for external context Claude cannot get from the repo or a CLI.

Recommended MCP order:

1. **Context7** (or equivalent docs MCP) for current library documentation.
2. **Playwright MCP** for automated browser verification once UI work begins.
3. **Chrome DevTools MCP** only if performance/accessibility inspection is needed.
4. **GitHub** via the `gh` CLI (preferred) rather than an MCP server, once the repo workflow is active.
5. **Figma MCP** only if design source files become part of the workflow.
6. No Slack/Notion/Drive/Jira until the product workflow requires them.

Prefer CLI tools (`gh`, `uv`, `pnpm`) over MCP servers where one exists — they are the most context-efficient way to interact with external services. Do not add MCP servers just because they are available.

### Rules and permissions

Keep permissions tight by default. Use `/permissions` to allowlist genuinely safe, frequent commands (`uv run pytest`, `pnpm lint`, `git commit`), and consider auto mode or `/sandbox` only once you trust the direction of a task.

Ask before:

* installing new production dependencies,
* running networked commands,
* deleting files,
* modifying lockfiles,
* running migrations,
* changing package manager config,
* pushing to remote,
* creating releases,
* touching secrets or `.env` files.

Never:

* print API keys,
* log secrets,
* commit `.env`,
* disable tests to make a build pass,
* hide failing checks,
* add telemetry without explicit operator approval.

Remember the distinction: an instruction in `CLAUDE.md` is advisory and can be missed under pressure or prompt injection. For anything that absolutely must not happen, use a deterministic guardrail — a `PreToolUse` hook that exits non-zero to block the call, or a permission rule — not a sentence in `CLAUDE.md`.

## Suggested Claude Code local setup

### Install Claude Code

```bash
curl -fsSL https://claude.ai/install.sh | bash
claude
```

Run `/init` once the repo skeleton exists to generate a starter `CLAUDE.md`, then prune it.

### Suggested global guidance

Personal preferences that should apply to every repo go in your user-level file:

```bash
mkdir -p ~/.claude
$EDITOR ~/.claude/CLAUDE.md
```

Suggested `~/.claude/CLAUDE.md`:

```markdown
# Personal working agreements

- Work as an operator-led engineering partner.
- For ambiguous product work, enter plan mode and ask focused questions (AskUserQuestion) before coding.
- Prefer small vertical slices over broad scaffolding.
- Always identify what changed, how it was verified, and what remains risky.
- Ask before adding production dependencies or running destructive commands.
- Never log, print, or commit secrets.
- Use browser/screenshot verification for UI changes.
- Use semantic commit messages.
- Keep summaries concise and evidence-based.
```

### Suggested project settings

Create `.claude/settings.json` once the repo exists and the operator approves. Starter:

```json
{
  "model": "claude-opus-4-8",
  "permissions": {
    "allow": [
      "Bash(uv run pytest:*)",
      "Bash(uv run ruff:*)",
      "Bash(pnpm test:*)",
      "Bash(pnpm lint:*)",
      "Bash(pnpm build:*)",
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(git commit:*)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(uv add:*)",
      "Bash(pnpm add:*)"
    ],
    "deny": [
      "Read(.env)",
      "Read(./**/.env)"
    ]
  }
}
```

Use a stronger model and plan mode for architecture, hard debugging, security review, complex refactors, and release planning. Use lighter prompts and quick iteration for small UI copy changes, simple bug fixes, docs cleanup, and test snapshots. Switch to a faster/cheaper model only for short iterative work once a stable implementation exists.

## Steering primitives: where each instruction belongs

Claude Code offers several ways to steer behavior. Put each instruction in the right place so it loads only when relevant and survives compaction appropriately.

| Need | Use | Location |
| --- | --- | --- |
| Always-on facts: build commands, repo layout, conventions | **CLAUDE.md (root)** | `CLAUDE.md` |
| Conventions specific to a subtree | **CLAUDE.md (subdir)** | e.g. `src/orionfold/providers/CLAUDE.md` |
| Cross-cutting constraint on certain files | **Path-scoped rule** | `.claude/rules/*.md` with `paths:` |
| Procedural workflow (release, review, UX polish) | **Skill** | `.claude/skills/<name>/SKILL.md` |
| Side task that should run isolated and return a summary | **Subagent** | `.claude/agents/<name>.md` |
| Something that must happen deterministically every time | **Hook** | `.claude/settings.json` |

Keep `CLAUDE.md` under ~200 lines and review it like code. If Claude keeps ignoring a rule, the file is probably too long; move procedures into skills and file-specific constraints into rules.

## Rules to create

Path-scoped rules load only when matching files are touched, keeping them out of context during unrelated work.

`.claude/rules/providers.md`:

```markdown
---
paths:
  - "src/orionfold/providers/**"
---
- API keys are never logged, never written to receipts, never printed in UI.
- Every provider returns a ProviderResult, including on error (no raised exceptions across the boundary).
- Cloud calls are opt-in; default to mock/local providers in tests.
- Provider tests must skip gracefully when credentials are absent.
```

`.claude/rules/receipts.md`:

```markdown
---
paths:
  - "src/orionfold/receipts/**"
  - "src/orionfold/scoring/**"
---
- Receipts must never contain secrets, raw API keys, or full provider config.
- Every receipt includes a config hash and timestamp.
- Markdown/HTML/JSON exports must stay schema-stable; bump a version field on change.
```

`.claude/rules/storage.md`:

```markdown
---
paths:
  - "src/orionfold/storage/**"
---
- Migrations are append-only.
- All persistence is local SQLite by default; no cloud database in v0.
```

## Skills to create

Create these as folders with a `SKILL.md` under `.claude/skills/`. Only the name and description load at session start; the body loads when invoked (by `/name` or auto-match). Build the workflow manually once, then package the recurring ones.

```text
.claude/skills/context-refresh/SKILL.md
.claude/skills/product-release-interview/SKILL.md
.claude/skills/proof-receipt-vertical-slice/SKILL.md
.claude/skills/browser-visual-verification/SKILL.md
.claude/skills/receipt-quality-review/SKILL.md
.claude/skills/ux-polish-review/SKILL.md
.claude/skills/release-quality-gate/SKILL.md
.claude/skills/current-docs-check/SKILL.md
.claude/skills/security-secrets-review/SKILL.md
```

### Skill: context-refresh

Use when starting a new session or after a long pause. It should read the release charter, product brief, and relevant ADRs; summarize current state; identify the next best task; and avoid re-reading huge docs unless necessary.

### Skill: product-release-interview

Use at the start of the project. It should interview the operator (via `AskUserQuestion`), challenge assumptions, and turn fuzzy product intent into `docs/product-brief.md` and `docs/release-charter.md` with v0 scope and non-goals. Mark with `disable-model-invocation: true` so it is operator-triggered.

### Skill: proof-receipt-vertical-slice

Use to build or update the core proof path. It should verify sample dataset → run → leaderboard → receipt export end-to-end, with tests and a Playwright smoke run.

### Skill: browser-visual-verification

Use for all UI changes. It should start/check the dev server, open the route, test the target viewport and state, capture a screenshot, compare against the target, and report precise visual findings before fixing.

### Skill: receipt-quality-review

Use when receipt structure, export, or leaderboard changes. It should generate a sample receipt, inspect Markdown and HTML, confirm no secrets, confirm recommendation clarity, and confirm client-shareable quality.

### Skill: ux-polish-review

Use when a route is functionally complete, the UI feels generic, or the operator asks for polish. It should inspect the route in the browser, run the UX quality gate, list top issues, fix scoped issues, and verify again.

### Skill: release-quality-gate

Use before tagging or shipping. It should run tests, lint/type/build, Playwright, export a sample receipt, inspect the worktree, update README and release notes, and list known limitations. Mark with `disable-model-invocation: true`.

### Skill: current-docs-check

Use before adding dependencies, using unfamiliar APIs, or changing framework/build config. It should consult `docs/tech/reference-index.md`, fetch current guidance only as needed, update `docs/tech/docs-update-log.md`, and summarize only the relevant notes.

### Skill: security-secrets-review

Use before releases and after provider changes. It should check for secrets, verify provider key handling, review network access, and inspect logs and artifacts for sensitive data.

Note: Claude Code ships with a built-in `/code-review` skill that reviews the current diff in a fresh subagent — use it as the default correctness check before treating work as done.

## Subagents to create

Define isolated assistants in `.claude/agents/`. They never enter the main conversation until called and return only their final summary.

`.claude/agents/diff-reviewer.md`:

```markdown
---
name: diff-reviewer
description: Reviews the current diff against the plan in a fresh context. Use proactively before treating work as done.
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior reviewer. You see only the diff and the criteria given to you.
Check that every requirement in the plan is implemented, listed edge cases have
tests, and nothing outside the task's scope changed. Report only gaps that affect
correctness or the stated requirements. Do not report style preferences.
```

`.claude/agents/codebase-investigator.md`:

```markdown
---
name: codebase-investigator
description: Explores the codebase to answer a scoped question and reports a summary. Use to avoid filling the main context with file reads.
tools: Read, Grep, Glob
model: sonnet
---
You investigate a single scoped question, read only what is needed, and return a
concise summary with file/line references. Do not edit files.
```

`.claude/agents/security-reviewer.md`:

```markdown
---
name: security-reviewer
description: Reviews code for secret leakage and insecure data handling, especially in providers and receipts.
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Look for API keys or secrets in code, logs,
receipts, or screenshots; insecure data handling; and any path where a provider
key could escape the machine. Provide specific line references and fixes.
```

## Hooks to add later

Hooks are deterministic and bypass compaction — use them for guarantees, not advice. Do not add hooks until workflows are stable. Claude can write them for you (e.g. "write a hook that runs ruff after every Python edit"). Configure in `.claude/settings.json`.

Potential hooks:

* **PostToolUse (Edit) — formatter/linter:** run `ruff` after Python edits and `eslint`/`prettier` after frontend edits, deterministically.
* **PreToolUse — secret guard:** inspect Bash calls and exit code 2 to block anything that would print `.env`, shell history, or provider config.
* **PreToolUse — protect migrations:** block writes to the migrations folder unless explicitly intended.
* **Stop — verification gate:** run the test suite or the receipt-export check and block the turn from ending until it passes.
* **PreCompact — worklog backup:** save key session context to `docs/worklog/` before compaction.

## Plugins

Run `/plugin` to browse the marketplace. Plugins bundle skills, subagents, hooks, and MCP servers into one installable unit. Useful early:

* A **code-intelligence plugin** for typed languages, giving precise symbol navigation and automatic error detection after edits.
* A **frontend/design plugin** that pairs a design-review skill with Playwright-driven screenshot capture for visual regression.

Once your own skills, subagents, and hooks are stable, bundle them as an internal plugin so the whole setup is portable across machines.

## UX quality bar

The detailed product-design, accessibility, and visual-verification standards live in `docs/claude-context-and-ux-addendum.md` (below). In brief, this product surface should feel like:

> A calm instrument panel for proving AI work, not a noisy dashboard for watching AI theater.

Design adjectives: precise, calm, confident, technical but humane, premium, readable, private, evidence-first, quietly distinctive. Avoid generic SaaS cards everywhere, purple-gradient AI cliché, noisy dashboards, confetti, fake "autonomous agent" theatrics, and decorative icons that do not aid scanning.

## Suggested operator prompts

### Start from opportunity doc

```text
Read docs/opportunity.md. Do not code yet.

Interview me using the AskUserQuestion tool to clarify the first release of this
product. Challenge assumptions. Your goal is to produce docs/product-brief.md and
docs/release-charter.md for a v0 a solo founder can build quickly.

Bias toward a local-first Proof Receipt product, not a broad cockpit, SaaS
platform, or generic local model runner.
```

### Approve product brief and plan architecture

```text
I approve the product brief. In plan mode, create an architecture decision record
for the smallest v0 implementation. Recommend a boring stack, repo layout, data
model, test strategy, and first vertical slice. Do not implement until I approve
the ADR.
```

### Build skeleton

```text
Implement the approved skeleton only:
- Python package and CLI
- local FastAPI server
- Vite React frontend
- health check
- README quickstart
- basic tests

Do not implement proof runs yet. Run tests and show the diff summary with evidence.
```

### Build first vertical slice

```text
Build the first proof-run vertical slice:
- sample dataset
- two deterministic mock providers
- proof execution
- leaderboard
- Markdown/HTML/JSON receipt export
- local persistence

Add tests and a Playwright smoke test. Verify in the browser and show screenshots.
Then use the diff-reviewer subagent to check the diff against the plan.
```

### Visual review

```text
Use Claude in Chrome (or Playwright) to open the local app. Review the Create
Proof Run path. Focus only on empty state, form clarity, leaderboard readability,
and receipt export confirmation. Screenshot each state, list differences from the
target, fix scoped issues, and rerun the visual smoke test.
```

### Release candidate

```text
Prepare a v0 release candidate. Run all checks, verify a fresh demo run, export a
sample receipt, run the security-reviewer subagent, update README, update release
notes, and list known limitations. Do not push or tag until I approve.
```

## Acceptance criteria for v0

The release is acceptable only if all are true:

* A new user can run the app locally.
* A sample proof run completes without external API keys.
* The user can compare at least two candidates.
* The leaderboard is visible in the UI.
* The user can inspect at least one failure case.
* The user can export a Markdown receipt.
* The user can export a JSON manifest.
* Tests pass.
* Playwright smoke test passes.
* README quickstart works from a fresh checkout.
* No secrets are logged or committed.
* The product has clear non-goals documented.

## Demo script

The demo should show:

1. Start app:

```bash
orionfold up
```

2. Create Proof Run.

3. Select sample dataset:

```text
Investment memo summarization sample
```

4. Select candidates:

```text
mock_good
mock_bad
```

5. Run proof.

6. View leaderboard.

7. Open failure case.

8. Export Proof Receipt.

9. Show receipt file.

10. Explain:

> "This is the core product: private, repeatable proof of which AI workflow is worth trusting."

## Revenue-aware product constraints

The product must eventually support paid tiers, but do not implement billing in v0.

Design for future gating around: saved project history, branded report export, batch runs, cloud provider comparisons, signed receipts, reusable proof packs, and consultant/client reports.

Do not gate the local proof core too early. The free product should create trust and distribution.

## Product strategy guardrails

When tempted to add a feature, ask:

1. Does this help a user create a better Proof Receipt?
2. Does this improve trust, repeatability, privacy, cost clarity, or failure visibility?
3. Can it be tested in the first vertical slice?
4. Will it increase support burden across machines?
5. Can it wait until a user asks for it twice?

If the answer to 1 is no, defer it.

## What to produce after each session

Append a worklog entry to `docs/worklog/` with:

```text
## Summary
- What changed
- Why it changed

## Verification
- Commands run (with evidence)
- Browser routes checked / screenshots
- Tests passed/failed

## Product impact
- What user journey improved
- What Proof Receipt capability improved

## Risks
- Known issues
- Deferred decisions

## Next recommended step
- One focused next task
```

## Common failure patterns to avoid

* **The kitchen-sink session.** Unrelated tasks pile into one context. Fix: `/clear` between them.
* **Correcting over and over.** After two failed corrections, `/clear` and write a sharper prompt.
* **The over-specified CLAUDE.md.** If it is too long, important rules get ignored. Prune ruthlessly; move procedures to skills and "must never" rules to hooks/permissions.
* **The trust-then-verify gap.** Plausible code that misses edge cases. Always give Claude a check it can run; if you cannot verify it, do not ship it.
* **The infinite exploration.** Unscoped "investigate" reads hundreds of files. Scope it, or hand it to a subagent.

## Current mission

Start by reading `docs/opportunity.md`.

Then produce:

* `docs/product-brief.md`
* `docs/release-charter.md`

Before coding, interview the operator and wait for approval. Remember:

> The user is not here to watch AI run.
> The user is here to decide what AI to trust.

Design every workflow, screen, label, and receipt around that decision.

[1]: https://code.claude.com/docs/en/best-practices "Best practices for Claude Code"
[2]: https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more "Steering Claude Code: skills, hooks, subagents and more"

---

The following is a pasteable addendum. Drop it into the repo as `docs/claude-context-and-ux-addendum.md`. It extends the bootstrap with context-engineering protocol, a current-docs reference index for the stack, and the product UX quality bar.

# Addendum: Context Engineering, Current Docs, and Product UX Quality Bar

## Purpose

This addendum extends the main bootstrap. Its job is to make Claude Code stay current on the stack, use context efficiently, avoid stale assumptions, keep product design tasteful and usable, verify UI work visually, and build a product surface that feels deliberate, premium, and operator-ready.

This product is not allowed to feel like a generic AI dashboard, generic SaaS template, or developer-tool demo. It must feel like a calm, precise instrument for creating and inspecting AI Proof Receipts.

## Core principle

Claude Code should not carry all context in chat. It should maintain a small, durable, navigable context system inside the repo.

> Put stable truth in files. Put volatile work state in the plan. Put current external facts behind reference links. Put decisions in ADRs. Put repeated workflows into skills. Put cross-cutting constraints into path-scoped rules. Put guarantees into hooks.

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

When conflict appears: current operator instruction wins for the current task, then release charter, then product brief, then ADRs, then CLAUDE.md, then older worklogs. Do not let old chat context override repo files.

## Required context files

```text
docs/
  product-brief.md
  release-charter.md
  tech/
    reference-index.md
    docs-update-log.md
    dependency-policy.md
  ux/
    product-design-system.md
    usability-checklist.md
    accessibility-checklist.md
    visual-verification-checklist.md
  adr/
    0001-local-first-proof-receipt-architecture.md
  worklog/
    YYYY-MM-DD-session-summary.md
```

## Automated context engineering protocol

At the start of each substantial session:

1. The root `CLAUDE.md` and unscoped rules load automatically — do not re-read them manually.
2. Read `docs/release-charter.md`.
3. Read only the relevant part of `docs/product-brief.md`.
4. Read relevant ADRs only if changing architecture.
5. Read relevant UX docs only if changing user-facing UI or copy.
6. Read `docs/tech/reference-index.md` before adding dependencies or using framework-specific APIs.
7. Summarize the minimal task context in your plan.
8. Do not reload the full opportunity document unless the operator explicitly asks or product strategy is being revisited.

Use focused file reads and `@`-references. Hand large explorations to a subagent so they do not fill the main window. Run `/clear` between unrelated tasks.

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

## Reference documentation index

Create `docs/tech/reference-index.md` with the following structure.

```markdown
# Technical Reference Index

Last updated: YYYY-MM-DD

## Claude Code

- Best practices
  - URL: https://code.claude.com/docs/en/best-practices
  - Use for: CLAUDE.md, plan mode, verification loops, subagents, /clear, scaling.

- Steering methods (CLAUDE.md, rules, skills, subagents, hooks, output styles)
  - URL: https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
  - Use for: deciding where each instruction belongs and its compaction behavior.

- Claude Code overview & docs map
  - URL: https://code.claude.com/docs/en/overview
  - Use for: navigating skills, hooks, subagents, MCP, plugins, permissions, sessions.

- Skills
  - URL: https://code.claude.com/docs/en/skills
  - Use for: SKILL.md format, invocation, disable-model-invocation.

- Subagents
  - URL: https://code.claude.com/docs/en/sub-agents
  - Use for: agent frontmatter, tool scoping, isolation, review patterns.

- Hooks
  - URL: https://code.claude.com/docs/en/hooks-guide
  - Use for: deterministic automation, PreToolUse/PostToolUse/Stop/PreCompact events.

- Rules / memory
  - URL: https://code.claude.com/docs/en/memory
  - Use for: path-scoped rules and CLAUDE.md placement.

- Permissions & sandboxing
  - URL: https://code.claude.com/docs/en/permissions
  - Use for: allowlists, auto mode, OS-level isolation.

- Claude in Chrome
  - URL: https://claude.com/claude-for-chrome
  - Use for: quick localhost visual checks.

## Python and backend

- uv — https://docs.astral.sh/uv/
- FastAPI — https://fastapi.tiangolo.com/
- Pydantic — https://docs.pydantic.dev/latest/
- Typer — https://typer.tiangolo.com/
- SQLite — https://www.sqlite.org/docs.html
- Python sqlite3 — https://docs.python.org/3/library/sqlite3.html
- Ruff — https://docs.astral.sh/ruff/
- pytest — https://docs.pytest.org/

## Frontend

- React — https://react.dev/learn
- Vite — https://vite.dev/guide/
- Tailwind CSS (Vite) — https://tailwindcss.com/docs/installation/using-vite
- shadcn/ui — https://ui.shadcn.com/docs
- Radix UI — https://www.radix-ui.com/primitives/docs/overview/introduction
- TanStack Query — https://tanstack.com/query/latest/docs/framework/react/overview
- React Hook Form — https://react-hook-form.com/get-started
- Zod — https://zod.dev/

## Testing

- Playwright — https://playwright.dev/docs/intro
- Vitest — https://vitest.dev/guide/

## UX, accessibility, product polish

- WCAG 2.2 quick reference — https://www.w3.org/WAI/WCAG22/quickref/
- Nielsen Norman usability heuristics — https://www.nngroup.com/articles/ten-usability-heuristics/
- Apple Human Interface Guidelines — https://developer.apple.com/design/human-interface-guidelines
- GOV.UK Design System — https://design-system.service.gov.uk/
```

## Dependency policy

Before adding a dependency, answer:

```markdown
## Dependency request
Package:
Purpose:
Official docs:
Why standard library / existing dependency is insufficient:
Runtime cost:
Bundle size impact:
Security/privacy risk:
Alternatives considered:
Removal plan if it proves unnecessary:
```

Prefer the Python standard library, small focused libraries, explicit adapters, copy-owned UI components, and deterministic test fixtures. Avoid heavy orchestration frameworks, generic agent frameworks, broad UI kits that dictate product feel, and analytics libraries that phone home.

## UX north star

> A calm instrument panel for proving AI work, not a noisy dashboard for watching AI theater.

Design adjectives: precise, calm, confident, technical but humane, premium, readable, private, evidence-first, quietly distinctive.

Avoid: generic SaaS cards everywhere, purple-gradient AI cliché, noisy dashboards, confetti, giant meaningless hero copy inside the app, terminal-only roughness, fake "autonomous agent" theatrics, and decorative icons that do not improve scanning.

## Product surface metaphor

> A lab bench plus a signed receipt.

The UI should help the user define the test, run the proof, inspect the evidence, decide what to trust, and export the receipt. Every screen must support one of those jobs.

## Core UX objects

```text
Project · Proof Brief · Dataset · Candidate · Proof Run · Leaderboard · Failure Case · Proof Receipt
```

Do not invent too many nouns. If a feature cannot attach to one of these objects, reconsider it.

## Primary app layout

```text
Left rail:    Projects · Proof Runs · Datasets · Candidates · Receipts · Settings
Main workspace: the current task — create, run, compare, inspect, export.
Right inspector: context, metadata, config, selected failure case, receipt summary.
```

Rules: the main workspace always has the clearest visual weight; the right inspector is secondary; the left rail is quiet. Avoid nested sidebars, card mosaics, and more than one primary CTA per view.

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

The user should see a working result within minutes, even without API keys, using deterministic mock providers.

## Empty states

Every empty state must answer: What is this area? Why does it matter? What should I do next? Can I try a sample?

Bad: "No proof runs yet."

Good: "Proof Runs compare candidates on the same frozen examples so you can decide what to trust. Start with the sample run or create your own."

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

A `copy-deck.md` should standardize product nouns, button labels, status labels, recommendation labels, and error-message patterns.

## Error-message standards

Errors must be specific, recoverable, calm, and privacy-safe.

Bad: "Something went wrong."

Good: "Ollama is not reachable at localhost:11434. Start Ollama or switch to the mock provider."

Bad: "Provider failed."

Good: "The OpenAI-compatible provider returned 401 Unauthorized. Check the API key. The key was not stored in the receipt."

Do not log secrets or expose keys in UI, receipts, screenshots, or worklogs.

## AI-provider UX

* API keys are never shown after entry.
* API keys are never written to receipts.
* Cloud calls are opt-in.
* Estimated cost is visible before run when possible.
* The cloud/local boundary is visible in the candidate list.
* Provider errors are actionable.

Labels: "Local", "Cloud", "Mock", "OpenAI-compatible", "Ollama", "LM Studio", "Bedrock later". Do not overbuild provider integrations in v0.

## Receipt artifact standards

Markdown: clean headings, tables for the leaderboard, bullets for failure cases, no app-only UI language.

HTML: self-contained if practical, printable, readable without app CSS, no external tracking, no secrets, includes timestamp and config hash.

JSON: machine-readable manifest, versioned schema, no secrets, predictable field names.

## Tests as context

Tests are Claude Code's most important compact context. Every product behavior should eventually have an executable fixture.

Create fixtures for: simple summarization proof, extraction proof, classification proof, mock provider success, mock provider failure, provider timeout, empty dataset, malformed row, failed receipt export.

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

Add screenshots only when useful. Do not create brittle screenshot tests for every minor layout.

## Visual verification checklist

For each UI change, before declaring done:

* dev server is running and the exact route is named,
* each state (empty, loading, error, populated) is rendered and screenshotted,
* the screenshot is compared against the design or prior state and differences are listed,
* keyboard path works for the core action,
* color contrast meets WCAG 2.2 AA,
* no secrets appear anywhere on screen.

Use Claude in Chrome for quick checks and Playwright (directly or via MCP) for multi-viewport, self-grading verification.

## Design review cadence

```text
Every feature:        functional review (+ /code-review subagent)
Every route:          UX polish review
Every receipt change: receipt quality review
Every release:        full visual sweep + security-secrets review
Every two weeks:      design-system cleanup
```

Do not let the UI accumulate one-off styles.

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

When building this product, remember:

> The user is not here to watch AI run.
> The user is here to decide what AI to trust.

Design every workflow, screen, label, and receipt around that decision.
