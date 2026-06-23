# Claude Code + Opus 4.8 Best Practices — Self-Configuration Guide (June 2026)

> **Purpose & audience.** This document is written to be *consumed by Claude Code itself* to configure a project for high-quality, high-speed agentic coding on Claude Opus 4.8. It is also readable by a human maintainer. Sections are ordered so Claude Code can act on them top-to-bottom: model facts → configuration files → skills → workflow → context engineering → prompting → speed/quality. Where an instruction is actionable, it is written as an imperative.
>
> **How to use this file.** Place a condensed version of the "Project configuration" sections into `CLAUDE.md` and `.claude/`. Keep the *reference* sections (model facts, prompting theory) in this file and link to them rather than copying them into `CLAUDE.md` — `CLAUDE.md` must stay lean (see §5).
>
> **Sourcing.** Synthesized from Anthropic's official Claude Code docs, the Anthropic Engineering blog (context engineering, agent skills, managed agents), the Opus 4.8 release notes and API migration docs, the Opus 4.8 / 4.7 prompting pages, and widely-cited community consolidations (Boris Cherny's guidance, the `shanraisshan/claude-code-best-practice` repo, `obra/superpowers`, and practitioner write-ups). Verified against docs as of **June 22, 2026**. Model and feature details change frequently — re-verify against `https://code.claude.com/docs` and `https://platform.claude.com/docs` before relying on any specific number.

---

## 1. Model facts: Claude Opus 4.8 (what changed, what to configure)

Opus 4.8 (`claude-opus-4-8`, released May 28, 2026) is a **reliability and tool-calling release**, not a raw-capability ceiling jump. The practical implications for how you configure and prompt it:

- **Honesty / self-checking.** ~4× less likely than Opus 4.7 to let flaws in its own code pass unremarked; it flags its own uncertainty and catches its own bugs instead of declaring victory early. *Configuration implication:* invite uncertainty explicitly (it surfaces it best when asked) and lean on its self-review rather than only external review.
- **Literal instruction following.** Like 4.7, it executes exactly what you write — no more, no less. Vague prompts get *scoped narrowly*, not generously generalized. *Implication:* state scope fences explicitly ("apply to every section, not just the first"; "don't touch other endpoints").
- **Favors reasoning over tool calls** by default, and **spawns fewer subagents** by default than 4.6/4.7. Raising effort (`high`/`xhigh`) is the lever that increases tool use and parallel fan-out, especially for agentic search and knowledge work.
- **Adaptive thinking** is the only supported thinking-on mode. It triggers reasoning per-turn only when the turn needs it, wasting fewer thinking tokens on simple steps. Thinking is **off** unless explicitly enabled (`thinking: {type: "adaptive"}` on the API).
- **1M-token context window by default** (200k on Microsoft Foundry), **128k max output tokens**, better compaction and long-context quality than 4.7.
- **Effort defaults to `high`** on all surfaces including Claude Code and the API.
- **Strong default "house style"** for design/frontend: warm cream (~#F4F1EA) backgrounds, serif display type, terracotta/amber accent. Great for editorial/portfolio; wrong for dashboards, dev tools, fintech, healthcare, enterprise. Override by *specifying a concrete alternative palette/spec* — generic negations ("don't use cream") just shift it to another fixed palette.

**Effort levels** (Claude Code names): `low`, `medium`, `high` (default), `xhigh`, `max`, plus `ultracode`. Pick by task, not habit — higher is not always better:

| Effort | Use for |
|---|---|
| `low` | Classification, extraction, format conversion, high-volume simple steps. Low-effort 4.8 floors near peak 4.7 on some coding tasks. |
| `medium` | Standard conversation and routine knowledge work. |
| `high` (default) | Most real coding and multi-constraint tasks; the quality/experience balance. |
| `xhigh` | Difficult tasks, long-running async coding/agentic work. Substantially more tool use and fan-out. |
| `max` | The hardest multi-constraint problems where errors are expensive. |
| `ultracode` | Lets Claude trigger **Dynamic Workflows** aggressively without the explicit "workflow" trigger phrase. |

> **Rule of thumb:** if you see shallow reasoning on a complex task, *raise effort before changing the prompt.* That is almost always the correct fix. Conversely, if runs are slow/expensive on simple tasks, *lower effort.* Routing inputs to the right effort dynamically beats one fixed setting.

**Fast mode** (`/fast` in Claude Code; `speed:"fast"` on the API as a research preview): same model, ~2.5× faster output, now 3× cheaper than prior fast tiers ($10/$50 per Mtok vs. standard $5/$25). Use it as the **iteration mode** — exploring, drafting, low-risk loops — not the final-judgment mode.

**Dynamic Workflows** (Claude Code): for very large tasks, Claude writes its own orchestration script, fans out to tens–hundreds of parallel subagents, verifies their work, and iterates until results converge. Because the control flow is *code*, it won't drift across thousands of files. Trigger by saying "workflow", running a workflow command, or enabling `ultracode`. **Gotcha:** the keyword "workflow" auto-triggers this mode (annoying when you mean a GitHub Actions workflow) — disable per-prompt with `opt/alt+w` or turn the keyword trigger off in `/config`.

**API migration notes (if you build on the API, not just the CLI):**
- `temperature`, `top_p`, `top_k`, and assistant **prefill** now return `400` on Opus 4.8 — remove them.
- You may inject `role:"system"` messages mid-conversation (after a user turn) to update instructions without rebuilding history — preserves prompt-cache hits.
- Minimum cacheable prompt length dropped to **1,024 tokens** — shorter prompts now cache.
- Refusals return a `stop_details` object describing the refusal category — route on it.
- Code that runs on 4.7 runs on 4.8 with no breaking changes.

---

## 2. The core mental model

Treat Claude Code as **a capable engineer you delegate to**, not a chatbot you converse with or an autocomplete you babysit. You describe the desired end state; Claude explores, plans, implements, and verifies. Two facts govern everything else:

1. **Context is the scarce resource.** Performance degrades as the context window fills ("context rot"): recall drops well before the hard limit. Accuracy noticeably declines past ~40–50% fill. The entire discipline below is about keeping the *smallest set of high-signal tokens* in context at each step.
2. **Verification closes the loop.** Claude stops when work "looks done." Without a check it can run, *you* are the verification loop and every mistake waits for you. Give it a pass/fail signal and it self-corrects unattended.

The production loop everyone converges on: **research → plan → execute → review → ship**, with the human as oversight at each gate. This is "agentic engineering," as distinct from "vibe coding" (one-shot prompting, no plan/review — fine for prototypes, breaks at production scale).

---

## 3. Project configuration: directory layout

Set up `.claude/` at the project root. This is the actionable scaffold Claude Code should create/maintain:

```
.
├── CLAUDE.md                      # lean, always-loaded project memory (§5)
├── CLAUDE.local.md                # personal, gitignored overrides
├── .claude/
│   ├── settings.json             # harness-enforced behavior: permissions, model, attribution, hooks (§4)
│   ├── skills/
│   │   └── <name>/SKILL.md        # model-invoked domain knowledge & workflows (§6)
│   ├── agents/
│   │   └── <name>.md              # custom subagents w/ own context + tools (§7)
│   ├── commands/
│   │   └── <name>.md              # slash commands for repeated inner-loop workflows
│   └── rules/
│       └── <name>.md              # lazily-loaded rules with `paths:` globs
└── docs/                          # specs (SPEC.md, PLAN.md) and linked reference docs
```

**Decision rule — which mechanism to use:**

- **`settings.json`** for anything deterministic and harness-enforced (permissions, model selection, commit attribution, hooks). *Don't* put "NEVER add Co-Authored-By" in `CLAUDE.md` when `attribution.commit:""` does it deterministically.
- **`CLAUDE.md`** for broadly-applicable, always-true project context Claude can't infer from code.
- **`.claude/rules/*.md` with `paths:` globs** for context that's only relevant to certain files/directories.
- **Skills** for domain knowledge or multi-step workflows relevant *sometimes* — loaded on demand, no always-on context cost.
- **Subagents** for tasks that read many files or need isolated focus.
- **Hooks** for actions that must happen *every* time with zero exceptions.
- **Commands** for inner-loop workflows you run many times a day.
- **MCP servers** for *actions* against external systems (DB, issue tracker, design tool).

> Mnemonic: **Skills are knowledge; MCP is action; hooks are guarantees; rules are scoped knowledge; settings are law.**

---

## 4. `settings.json`: harness-enforced behavior

Put deterministic behavior here so it can't be "forgotten" mid-session like prose instructions can.

- **Model & effort.** Pin the model and default effort for the project where appropriate. Use `xhigh` for coding/agentic-heavy repos; drop to `high`/`medium` for cheaper iteration.
- **Permissions.** Default is conservative — Claude asks before any system-modifying action (file writes, many bash commands, MCP tools). Reduce friction three ways, in order of preference:
  1. **Permission allowlists** (`/permissions`) — permit specific safe commands you trust (`npm run lint`, `git commit`, `npm test`).
  2. **Auto mode** (`--permission-mode auto`) — a classifier reviews each command and blocks only risky ones (scope escalation, unknown infra, hostile-content-driven actions). Best when you trust the task direction but don't want to click through every step. In `-p` non-interactive runs it aborts if the classifier repeatedly blocks (no human to fall back to).
  3. **Sandboxing** (`/sandbox`) — OS-level filesystem/network isolation so Claude works freely within boundaries.
- **Hooks.** Deterministic scripts at lifecycle points. Unlike `CLAUDE.md` (advisory), hooks *guarantee* the action. Claude can write them for you ("write a hook that runs eslint after every file edit"; "block writes to the migrations folder"). The **Stop hook** is the strongest verification gate: it runs your check as a script and blocks the turn from ending until the check passes (Claude overrides after 8 consecutive blocks). Browse with `/hooks`.
- **Attribution.** Set commit attribution deterministically rather than instructing it in prose.

---

## 5. `CLAUDE.md`: the always-loaded memory file

`CLAUDE.md` is read at the start of every conversation, so **every line is a permanent context tax.** Keep it lean. Generate a starter with `/init` (it detects build systems, test frameworks, patterns), then prune relentlessly.

**The single test for every line:** *"Would removing this cause Claude to make a mistake?"* If not, cut it. A bloated `CLAUDE.md` causes Claude to ignore the rules that matter — important rules get lost in noise. Community guidance converges on **≤ ~200 lines.**

| ✅ Include | ❌ Exclude |
|---|---|
| Bash commands Claude can't guess | Anything Claude can derive by reading code |
| Code-style rules that *differ from defaults* | Standard language conventions Claude already knows |
| Testing instructions & preferred test runner | Detailed API docs (link instead) |
| Repo etiquette (branch naming, PR conventions) | Info that changes frequently |
| Architecture decisions specific to this project | Long explanations / tutorials |
| Env quirks (required env vars) | File-by-file codebase descriptions |
| Non-obvious gotchas | Self-evident advice ("write clean code") |

**Mechanics:**
- Press `#` mid-session to append an instruction; Claude writes it to the right `CLAUDE.md`. Commit these so the team benefits — the file compounds in value.
- Tune adherence by adding emphasis (`IMPORTANT`, `YOU MUST`) **sparingly** — see the §9 caution on over-aggressive language.
- Import other files with `@path/to/file` (e.g. `@docs/git-instructions.md`, `@~/.claude/my-overrides.md`).
- **Locations / precedence:** `~/.claude/CLAUDE.md` (all sessions) → `./CLAUDE.md` (team, committed) → `./CLAUDE.local.md` (personal, gitignored) → parent dirs (monorepos) → child dirs (loaded on demand when Claude reads files there).
- Add compaction-survival instructions: e.g. *"When compacting, always preserve the full list of modified files and any test commands."*

**Diagnostics:** If Claude repeatedly ignores a rule, the file is probably too long and the rule is drowning — prune. If Claude asks questions already answered in `CLAUDE.md`, the phrasing is ambiguous — rewrite. Treat `CLAUDE.md` like code: review when things go wrong, test changes by observing whether behavior actually shifts.

---

## 6. Skills: model-invoked domain knowledge & workflows

A **Skill** is a directory with a `SKILL.md` (YAML frontmatter + body). Claude loads it *automatically* when a task matches its description, or you invoke it directly with `/skill-name`. Skills are the right home for knowledge/workflows that are relevant *sometimes* — they cost almost nothing until triggered.

### 6.1 Progressive disclosure (the core design principle)

Skills load in stages, so an agent can be aware of dozens of skills for less context than one activated skill:

1. **Metadata (startup):** only `name` + `description` from frontmatter enter the system prompt (~80 tokens median per skill). This is how Claude decides *whether* to fire the skill.
2. **Body (on trigger):** the full `SKILL.md` is read via bash only when Claude judges the skill relevant (~2,000 tokens median).
3. **Bundled files (on demand):** `reference.md`, `forms.md`, `examples.md`, etc. are read only when that specific path is needed. Unused files cost **zero** tokens.
4. **Scripts (executed, not loaded):** utility scripts run via bash; only their *output* enters context. Use code for deterministic work (sorting, parsing, validation) — far cheaper and more reliable than token generation.

### 6.2 Authoring rules (highest-signal first)

- **The `description` field is a trigger, not a summary.** Write it in third person, packing *what the skill does* **and** *when to fire it* (triggers, contexts, keywords). Claude tends to *under*-trigger skills, so write it slightly "pushy": e.g. *"Use whenever the user mentions dashboards, data visualization, or internal metrics, even if they don't explicitly ask for a dashboard."* Budget: ~1024 chars (open spec) / ~1536 chars combined in Claude Code listings — every sentence competes for space. **Nothing else matters if selection fails.**
- **Keep `SKILL.md` body under ~500 lines (~5k tokens).** Past that, split into reference files and point to them. For reference files > 100 lines, add a table of contents at the top so partial reads still reveal scope.
- **Skills are folders, not files.** Use `reference/`, `scripts/`, `examples/` subdirectories. Keep mutually-exclusive contexts in separate files so they never co-load.
- **Explain the *why*, don't just command.** "Use constructor injection — field injection breaks testability because we can't mock the field without a Spring context" generalizes to unanticipated cases; "MUST use constructor injection, NEVER field injection" does not. Anthropic's own skill-creator flags strings of all-caps `MUST`/`ALWAYS`/`NEVER` as a yellow flag to reframe. (Bare imperatives are still correct for genuinely fragile single steps.)
- **Give goals and constraints, not prescriptive step-by-step railroading** — except where a procedure is fragile and one wrong step breaks everything (match instruction-freedom to task-fragility).
- **Build a "Gotchas" section** in every skill and grow it over time with Claude's observed failure points — this is the highest-signal content.
- **Don't state the obvious.** Focus on what pushes Claude *out of* its default behavior. Anything Claude already does correctly without the instruction is wasted tokens.
- **Include scripts/libraries** so Claude *composes* rather than reconstructs boilerplate. Embed `!command` in `SKILL.md` to inject dynamic shell output at invocation (Claude runs it; only the result enters context).
- **MCP tools in skills:** always use fully-qualified names (`GitHub:create_issue`, `BigQuery:bigquery_schema`) or Claude may fail to locate the tool when multiple servers are connected.
- **Add a validation loop** for quality-critical skills: "run validator → fix errors → repeat" measurably improves output. For code-free skills the "validator" can be a `STYLE_GUIDE.md` Claude checks against.
- **`disable-model-invocation: true`** for workflows with side effects you want to trigger manually only.

### 6.3 Author by evaluation, then iterate with two Claudes

1. **Start from observed gaps.** Run representative tasks, watch where Claude struggles, build the skill to close *that* gap. Don't speculatively over-build.
2. **Two-Claude loop:** Claude A authors/organizes the skill; Claude B (fresh instance, skill loaded) runs it on a *similar* task. Watch whether B finds the right info and applies rules. Feed specific failures back to A ("when Claude used this it forgot to filter by date for Q4 — add a date-filtering section?"). Iterate.

### 6.4 Minimal templates

Knowledge skill:
```markdown
---
name: api-conventions
description: REST API design conventions for our services. Use when designing, reviewing, or adding HTTP endpoints, request/response shapes, or URL paths.
---
# API Conventions
- Use kebab-case for URL paths; camelCase for JSON properties.
- Always paginate list endpoints (we've shipped unbounded responses that OOM'd staging — that's the why).
- Version in the URL path (/v1/, /v2/).
## Gotchas
- (add observed failure points here over time)
```

Workflow skill (manually invoked):
```markdown
---
name: fix-issue
description: Fix a GitHub issue end-to-end.
disable-model-invocation: true
---
Fix GitHub issue: $ARGUMENTS.
1. `gh issue view` to get details.
2. Search the codebase for relevant files.
3. Implement the fix following existing patterns.
4. Write and run tests proving the fix; show the test output as evidence.
5. Pass lint + typecheck.
6. Commit with a descriptive message; push; open a PR.
```

---

## 7. Subagents, commands, and parallelism

### 7.1 Subagents (`.claude/agents/<name>.md`)
Run in their **own context window** with their **own allowed tools**. They are the most powerful context-management tool you have: research that would read dozens of files happens in the subagent and only a *summary* returns to your main conversation.

- Delegate investigation: *"Use subagents to investigate how our auth handles token refresh and whether we have existing OAuth utilities to reuse."*
- Delegate review (fresh context = unbiased): a reviewer subagent sees only the diff + criteria, not the reasoning that produced it.
- **Opus 4.8 spawns fewer subagents by default** — say "use subagents" / "spawn multiple subagents in the same turn" explicitly when you want parallel fan-out across files or items. Raising effort also increases spawning.
- `context: fork` runs a skill in an isolated subagent so the main context sees only the final result.
- Example security-reviewer agent:
```markdown
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Review for injection (SQL/XSS/command),
auth/authz flaws, secrets in code, and insecure data handling.
Give specific line references and suggested fixes. Flag only real issues.
```

### 7.2 Commands (`.claude/commands/<name>.md`)
Turn any inner-loop workflow you run more than once a day into a slash command (`/techdebt`, `/context-dump`, `/fix-issue 1234`). Commit them. They live in `.claude/commands/` (project) or `~/.claude/commands/` (personal, all sessions).

### 7.3 Running multiple Claudes
Pick the coordination level you want:
- **Git worktrees** — isolated checkouts so parallel sessions don't collide on edits.
- **Desktop app sessions** — manage multiple local sessions visually, each in its own worktree.
- **Claude Code on the web** — sessions on Anthropic-managed VMs.
- **Agent teams** — automated coordination with a lead agent assigning subtasks and merging results; keeps a review loop running across many tasks while you spot-check findings.

**Quality patterns from parallelism:**
- **Writer/Reviewer:** Session A implements; Session B (fresh context) reviews for edge cases, race conditions, consistency; feed B's findings back to A.
- **Test-author/Implementer:** one Claude writes tests, another writes code to pass them.
- **Self-critique fan-out:** have Claude build something, then spin up 5–10 subagents to critique, summarize the feedback, and iterate.

---

## 8. Context engineering for optimal token usage

Anthropic frames this as a resource problem: context has **diminishing marginal returns** and the discipline is finding the *smallest set of high-signal tokens* that maximize the odds of the desired outcome. Four strategies — **write, select, compress, isolate** — plus Claude Code's built-ins:

### 8.1 Write (persist outside the window)
- **Scratchpads / notes:** have Claude save plans and state to files (`SPEC.md`, `PLAN.md`, `STATUS.json`). The model is *less likely to rewrite JSON* than Markdown (it treats JSON as "code"), so use JSON to track status/progress that must survive.
- **First-context-window pattern:** use the *first* context window to set up the framework (write tests, create setup scripts), then use later windows to iterate against a todo list. Use a different prompt for that first window.

### 8.2 Select (load only what's needed)
- Reference files with `@` so Claude reads them just-in-time instead of you pasting them.
- Pass **literal paths** (`apps/web/src/app/(home)/page.tsx`), not descriptions ("the homepage file") — saves exploratory tool calls and the model handles paths literally.
- Let progressive disclosure (skills, rules globs) gate what loads.

### 8.3 Compress (shrink what's there)
- `/compact <instructions>` to summarize while preserving what matters (`/compact Focus on the API changes`).
- `Esc Esc` / `/rewind` → pick a checkpoint → **Summarize from here** (condense forward) or **Summarize up to here** (condense earlier, keep recent).
- Auto-compaction triggers near the limit; customize what it preserves via `CLAUDE.md`.

### 8.4 Isolate (separate contexts)
- Subagents (§7.1) — the primary isolation tool.
- Many narrow agents with isolated contexts often outperform one agent, because each window is allocated to a tighter sub-task. **Cost caveat:** multi-agent can use up to ~15× the tokens of a single chat — reserve fan-out for tasks that genuinely parallelize or need isolation.

### 8.5 Manage the session aggressively
- **`/clear` between unrelated tasks** — the #1 hygiene habit. A clean session with a better prompt almost always beats a long polluted one.
- **Course-correct early:** `Esc` to interrupt (context preserved), `"undo that"`, or `Esc Esc`/`/rewind` to restore conversation/code state. After **two failed corrections on the same issue**, `/clear` and rewrite the prompt incorporating what you learned — don't keep correcting into a polluted window.
- **`/btw`** for throwaway questions — the answer appears in a dismissible overlay and never enters history.
- **Checkpoints** snapshot files before each change and persist across sessions — enabling "try something risky, rewind if it fails." (Not a git replacement; only tracks Claude's changes.)
- **Resume/branch sessions:** `claude --continue` (most recent), `claude --resume` (pick from list), `/rename` to name them like branches (`oauth-migration`).

### 8.6 Five failure patterns to recognize early
1. **Kitchen-sink session** (unrelated tasks pile up) → `/clear` between tasks.
2. **Correct-over-and-over** (polluted with failed approaches) → after 2 fails, `/clear` + better prompt.
3. **Over-specified `CLAUDE.md`** (rules lost in noise) → prune ruthlessly; convert deterministic rules to hooks.
4. **Trust-then-verify gap** (plausible code, unhandled edge cases) → always provide a verification signal; if you can't verify it, don't ship it.
5. **Infinite exploration** (unscoped "investigate" reads hundreds of files) → scope narrowly or push into a subagent.

---

## 9. Prompt engineering for Opus 4.8

The golden rule (Anthropic's): *show your prompt to a colleague with minimal context and ask them to follow it.* If they'd be confused, so is Claude. Specific beats verbose — the goal is **fewer ambiguous gaps**, not longer prompts.

### 9.1 Be explicit; the model is literal
- **Request "above and beyond" behavior explicitly** — it won't infer it. "Create a dashboard" yields a literal frame; "create an analytics dashboard with as many relevant features and interactions as possible; implement a fully functional solution, not a basic version" yields the rich result.
- **State scope fences:** "apply to every section, not just the first"; "don't touch any other endpoints."
- **Describe the completed outcome**, not just the action. Underspecified: "add authentication." Specified: "Add auth to `/api/profile`: (1) verify JWT in the Authorization header, (2) return 401 if missing/invalid, (3) attach decoded user to request context, (4) add a test for the 401 case and one for success. Don't touch other endpoints."

### 9.2 Prefer positive instructions; avoid aggressive language
- Tell Claude **what to do**, not a list of don'ts — positive instructions with context outperform negations.
- **Calm, direct instructions beat shouting.** Over-aggressive `CRITICAL!` / `YOU MUST` / `NEVER EVER` can cause over-triggering (the model fixates on avoiding the error and degrades overall quality). Use emphasis sparingly and only where adherence genuinely fails. (Note: Anthropic *internally* does use `IMPORTANT`/`YOU MUST` in `CLAUDE.md` to lift compliance — so this is a dial to tune, not an absolute ban. Reach for emphasis after a rule fails, not preemptively.)
- **Remove anti-laziness scaffolding** carried over from older models ("double-check before returning", forced interim status messages) — 4.8 self-verifies and emits progress updates natively; leftover scaffolding causes over-triggering.

### 9.3 Structure with XML and examples
- Use **XML tags** (`<context>`, `<instructions>`, `<example>`, `<spec>`) when a prompt mixes instructions, source material, examples, and inputs — literalism makes clear structure pay off more. Rule of thumb: if a prompt has > 2 distinct sections, tag them. For simple prompts, skip the ceremony.
- **Examples are powerful and literal.** Positive examples at the length/depth you want outperform abstract length instructions ("don't be verbose"). Ensure every example models the behavior you want — Claude pattern-matches them closely.

### 9.4 Calibrate thinking & response length
- **Effort is the primary depth lever** (§1). For shallow output on hard tasks, raise effort first.
- For finer control, nudge with language: "think carefully / think hard / consider each X before answering" for more depth; "prioritize responding quickly" for less. Don't waste thinking on trivial tasks (no "think step by step" to write a haiku).
- 4.8 calibrates length to perceived complexity — if you need long output, **state the length/depth explicitly.**
- **Invite honesty explicitly** to capture 4.8's signature strength: "If you're uncertain about any part, say so and explain why" / "flag anything you couldn't verify."

### 9.5 Tool-use & subagent steering
- 4.8 favors reasoning over tools by default. To get more tool use, **raise effort** (`high`/`xhigh`) and/or **describe when and why** to use a given tool ("use web search whenever a fact might have changed since your knowledge cutoff").
- Replace blanket defaults ("Default to using [tool]") with targeted guidance ("Use [tool] when it would deepen understanding of the problem"). Avoid "if in doubt, use [tool]" — it over-triggers on modern models.
- To increase parallelism, instruct explicitly: "spawn multiple subagents in the same turn when fanning out across items or reading multiple files."

### 9.6 Let Claude interview you, then execute in a fresh session
For larger features, start minimal and have Claude interview you using the `AskUserQuestion` tool:
```
I want to build [brief description]. Interview me in detail using the AskUserQuestion tool.
Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs. Skip obvious
questions; dig into the hard parts I might not have considered. Keep going until we've covered
everything, then write a complete spec to SPEC.md.
```
The best specs are **self-contained**: they name the files/interfaces involved, state what's out of scope, and end with an **end-to-end verification step** that proves the feature works. Then start a **fresh session** to implement against the written spec — clean context, fully focused.

---

## 10. The agentic coding workflow (end to end)

### 10.1 Explore → Plan → Implement → Commit
1. **Explore (plan mode).** Claude reads files and answers questions without editing. *"Read /src/auth; understand sessions and login. Look at how we manage env vars for secrets. Don't write code yet."*
2. **Plan (plan mode).** *"I want to add Google OAuth. What files change? What's the session flow? Create a plan."* Press `Ctrl+G` to edit the plan in your editor before proceeding.
3. **Implement (default mode).** *"Implement the OAuth flow from your plan. Write tests for the callback handler, run the suite, fix failures."*
4. **Commit.** *"Commit with a descriptive message and open a PR."*

> **Skip planning** when the scope is clear and small (typo, log line, rename) — if you can describe the diff in one sentence, just ask for it. Plan when the approach is uncertain, the change spans multiple files, or you're unfamiliar with the code.

### 10.2 Always give a verification signal
The difference between a session you *watch* and one you *walk away from*. From weakest to strongest gate:
- **In-prompt:** "run the tests and iterate until they pass" in the same message.
- **Across a session:** set a `/goal` condition — a separate evaluator re-checks after every turn until it holds.
- **Deterministic gate:** a **Stop hook** runs your check as a script and blocks the turn from ending until it passes.
- **Second opinion:** a verification subagent or Dynamic Workflow has a *fresh* model try to refute the result, so the doer isn't the grader.

Provide criteria up front ("validateEmail: `user@example.com`→true, `invalid`→false, `user@.com`→false; run the tests"). Verify UI visually (paste a screenshot, have Claude screenshot its result and diff). Demand **evidence** (test output, the command + its result, a screenshot) rather than an assertion of success — reviewing evidence is faster than re-running it yourself.

> **Reviewer caution:** a reviewer asked to find gaps will always find some. Tell it to flag *only* gaps affecting correctness or stated requirements; treat the rest as optional. Chasing every finding → over-engineering (needless abstraction, defensive code, tests for impossible cases).

### 10.3 Spec-driven phasing
- Break PRDs into **vertical slices (tracer bullets)** that cross all layers (DB + service + UI) rather than horizontal phases (all-DB, then all-API, then all-UI) — horizontal phasing delays end-to-end feedback until the last phase.
- Make a **phase-wise gated plan**, each phase with its own tests (unit + integration + automation).

### 10.4 Use the right tools for context efficiency
- **CLI tools are the most context-efficient external interface.** Install `gh` (Claude knows it for issues/PRs/comments; avoids unauthenticated API rate limits); likewise `aws`, `gcloud`, `sentry-cli`. Claude can learn unknown CLIs: "use `foo-cli --help` to learn it, then solve A, B, C."
- **MCP servers** for richer integrations (issue trackers, databases, Figma, monitoring) — query the DB before writing a migration, read the ticket before implementing, check observability before debugging.
- **Code-intelligence plugin** for typed languages → precise symbol navigation + automatic error detection after edits. Browse `/plugin`.

### 10.5 Onboarding & git
- Onboard to a codebase by asking Claude senior-engineer questions directly ("How does logging work?", "What edge cases does `CustomerOnboardingFlowImpl` handle?", "Why `foo()` not `bar()` on line 333?") — no special prompting; it explores to answer.
- Delegate the bulk of git: history spelunking ("what changed in v1.2.3?", "who owns this feature?"), commit messages, PRs.

### 10.6 Automate & scale (non-interactive)
- `claude -p "prompt"` for CI, pre-commit hooks, scripts. `--output-format json` or `stream-json --verbose` to parse results.
- **Fan out across files:** have Claude list all files needing a change, then loop `claude -p` per file with `--allowedTools` scoping permissions. Test on 2–3 files, refine the prompt, then run at scale.
- `claude --permission-mode auto -p "fix all lint errors"` for unattended runs with background safety classification.

---

## 11. Maximizing quality and speed

**Speed levers:**
- `/fast` (fast mode) for iteration, drafting, exploration, low-risk loops — ~2.5× faster, now cheaper. Keep final-judgment passes on standard mode.
- **Lower effort** on simple/high-volume steps; reserve `xhigh`/`max` for genuinely hard tasks. Dynamic effort routing is the biggest cost lever without sacrificing quality where it matters.
- **Literal paths over descriptions** to cut exploratory tool calls.
- **Prompt caching** — mid-conversation system messages (API) and the lower 1,024-token cache minimum preserve cache hits on long sessions = real money saved.
- **Parallelism** (worktrees, agent teams, Dynamic Workflows) for throughput on large jobs.

**Quality levers:**
- **Raise effort** before re-prompting when reasoning looks shallow.
- **Always verify** (§10.2) — the single biggest quality multiplier.
- **Fresh-context review** (Writer/Reviewer, self-critique fan-out) — a fresh model catches what the author can't.
- **Invite uncertainty** to surface 4.8's honesty.
- **Tighten specs** (§9.6) — time on a precise spec pays off more than time watching implementation.
- **Override the design default** explicitly for non-editorial UIs (dashboards/dev-tools/fintech/health/enterprise): specify a concrete palette/spec, don't just negate "no cream."

**Cost/budget discipline:**
- Start `xhigh`/`max` runs at **64k max output tokens** so the model has room to think + fan out without truncation; tune down for short-response use cases.
- Use the cheap model where being wrong is cheap; reserve the expensive model where the cost of being wrong exceeds the cost of tokens.

---

## 12. Quick-start checklist for Claude Code (act on these in order)

1. Run `/init` → generate starter `CLAUDE.md`; prune to ≤ ~200 high-signal lines (§5).
2. Create `.claude/settings.json`: pin model + default effort (`xhigh` for heavy coding); set commit attribution; allowlist safe commands; add a Stop hook running tests/lint (§4, §10.2).
3. Add `.claude/rules/*.md` with `paths:` globs for directory-scoped conventions (§3).
4. Write a skill for any workflow you've repeated twice; description = trigger, body ≤ 500 lines, add a Gotchas section, explain the *why* (§6).
5. Define subagents for review/security/research in `.claude/agents/` (§7.1).
6. Turn daily inner-loop workflows into `.claude/commands/` slash commands (§7.2).
7. Install CLI tools (`gh`, cloud CLIs) and connect needed MCP servers; add a code-intelligence plugin for typed languages (§10.4).
8. Adopt the loop: **explore → plan → implement → verify → commit**, with `/clear` between unrelated tasks and a verification signal on every task (§10).
9. For big features: interview → `SPEC.md` → fresh session to implement (§9.6).
10. Tune effort/fast-mode per task; route dynamically rather than one fixed setting (§1, §11).

---

## 13. Key references (re-verify; details change fast)

- Best practices for Claude Code — `code.claude.com/docs/en/best-practices`
- Extend Claude Code (skills/hooks/MCP/subagents/plugins) — `code.claude.com/docs/en/features-overview`
- CLAUDE.md / memory — `code.claude.com/docs/en/memory`
- What's new in Claude Opus 4.8 / migration — `platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-8`
- Prompting best practices + "Prompting Claude Opus 4.8" — `platform.claude.com/docs/en/build-with-claude/prompt-engineering/`
- Effective context engineering for AI agents — `anthropic.com/engineering/effective-context-engineering-for-ai-agents`
- Equipping agents with Agent Skills — `anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills`
- Skill authoring best practices — `platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`
- Scaling Managed Agents (harnesses) — `anthropic.com/engineering/managed-agents`
- Community consolidations — `github.com/shanraisshan/claude-code-best-practice`, `github.com/obra/superpowers`

> **Maintenance note for Claude Code:** Anthropic ships Claude Code features roughly weekly and models on a ~2-month cadence. Treat every specific number, flag, and feature name here as a snapshot dated 2026-06-22. Before relying on one, confirm against the live docs above. The *principles* (context as scarce resource, verify-the-loop, progressive disclosure, literal prompting, research→plan→execute→review→ship) are stable; the *surfaces* change.
