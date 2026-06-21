# HANDOFF

> Current cross-session pointer. **Overwritten each handoff** — this is "what to do next,"
> not history. History lives append-only in `docs/worklog/`.
>
> To resume: in a fresh session say **"read from handoff"** (or "continue from last
> session"), or `/clear` and paste the prompt below.

_Last updated: 2026-06-20 · **Leaderboard recommendation fix (live-review Finding 1 + Finding 3)
SHIPPED & merge-ready.** The leaderboard no longer recommends a candidate that produced nothing. An
errored candidate reports 0ms/$0.00 and used to win the 0%-pass latency/cost tiebreak, then got
crowned RECOMMENDED unconditionally (verified live: a model 404-ing on every example was
"recommended"). Fixed in three layers: ranking adds `error_count` + sorts
`(all_errored, -pass_rate, -avg_score, latency, cost)` so a fully-errored candidate ranks LAST and
any real output beats it even at a 0.00 tie; `recommended` is set ONLY when `entries[0].pass_count>0`;
and when nobody passes, the cockpit + all 3 receipt formats show a calm NEUTRAL "No clear winner"
state ("No candidate passed the rubric (threshold N)") with errored rows annotated "errored, no
output". The receipt gains the additive `error_count` field → **RECEIPT_VERSION 3 → 4**
(`config_hash` + run provenance byte-for-byte UNCHANGED). Bundled Finding 3: removed `claude-fable-5`
from catalog.json (not available; made the cost-vs-quality "Frontier" arm resolve to an unavailable
model) → Frontier now resolves to `claude-opus-4-8` (flagged ★ latest); anthropic default
(`claude-haiku-4-5`) unchanged. Built brainstorm → spec → plan → subagent-driven (5 TDD tasks,
per-task reviews, Task 2 fix loop for a vacuous test, Opus whole-branch review: Ready-to-merge with
one fix = stale fable-5 in pricing.py, fixed). pytest 157 · vitest 46 · ruff clean · build clean ·
e2e 4/4 · receipt-quality-review clean (no secrets, 3 formats) · live browser check (no-winner card
neutral, error-vs-fail distinction, catalog change live). Commits on `main` (NOT pushed — no remote):
5b899c6 bbb3d21 4145b66 b56dc38 45c7772 67ee30c 0c0de7e (+ spec/plan/worklog docs)._
>
> **NEXT SESSION — QUEUED: brainstorm Finding 2 (the similarity-rubric weakness) FIRST.** The very
> first action is to invoke the **`superpowers:brainstorming`** skill on the rubric redesign — do NOT
> write a plan or code until a design is approved (it's a scoring-semantics decision, see the weigh-
> points below). It is the last of the three live-review findings. The v0 default rubric is
> **string-similarity @ threshold 0.8** against the expected
> prose, so a **correct** summary in a different FORMAT scores low (live: Haiku produced a clean,
> factually complete Markdown table — arguably better than the terse expected prose — and scored
> 0.12 / Fail). The rubric rewards matching phrasing/format, not meaning. Real fix points to an
> **LLM-as-judge / semantic rubric** (the charter flagged LLM-as-judge as "optional, later" — this
> run is the evidence it's needed). Lower-effort interim: lower the default threshold and/or document
> that similarity scoring is format-sensitive. **BRAINSTORM this before plan/code** — it's a scoring-
> semantics decision (touches `proof/` scoring + possibly a new provider-backed judge, so weigh
> keyless-default + cost + determinism-in-tests). Details in
> docs/worklog/2026-06-20-decision-recipes.md §"Finding 2" and
> docs/worklog/2026-06-20-leaderboard-recommendation-fix.md §Risks.
>
> THEN **#6 prompt-variant candidates** (same model, different system prompt — the next candidate
> axis; composes with the picker + recipes; still text-in/text-out, no new provider machinery), and
> the CATALOG PRICE/SOURCE accuracy pass. Full creative/feature work → brainstorm → spec → plan →
> subagent-driven, same loop._

## Paste prompt for the next session

```text
Use the context-refresh skill to load current state from docs/ (release charter, ADR-0001 +
ADR-0002 + ADR-0003, and the latest worklogs: 2026-06-20-leaderboard-recommendation-fix,
2026-06-20-decision-recipes).

RECENT WORK (committed to main, not pushed — no git remote configured):
- (this session) LEADERBOARD RECOMMENDATION FIX (live-review Finding 1 + Finding 3), merge-ready.
  proof/leaderboard.py: LeaderboardEntry gains error_count (= rows where r.error is not None);
  build_leaderboard sorts (all_errored, -pass_rate, -avg_score, avg_latency_ms, total_cost) where
  all_errored = total>0 and error_count==total (fully-errored ranks LAST; real output beats it even
  at 0.00 tie); recommended set ONLY when entries[0].pass_count>0. receipts/export.py:
  RECEIPT_VERSION 4; build_receipt computes has_winner = top and top.pass_count>0 → verdict
  "No clear winner" + "No candidate passed the rubric (threshold {rubric.threshold:.2f})." when no
  winner; _failures_label() annotates "errored, no output" rows in MD + HTML; _verdict/_recommendation_line
  unchanged (no-winner branch in the CALLER). Frontend: api.ts leaderboardEntrySchema += error_count;
  DecisionSummary (ProofCockpit.tsx, now EXPORTED) + ReceiptsView.winnerOf use find(recommended) ??
  null/undefined → calm NEUTRAL no-winner card (panel colors, NOT --color-accent); Leaderboard.tsx
  marks rows where error_count===total && total>0. catalog.json: claude-fable-5 REMOVED;
  claude-opus-4-8 is sole frontier claude + latest:true (anthropic default still claude-haiku-4-5,
  drift-guard green). pricing.py: stale claude-fable-5 entry removed (catalog parity). Samples
  regenerated (mock_good err=0 winner stays; mock_bad err=1). config_hash + run provenance UNTOUCHED.
- (prior) DECISION RECIPES (#5): recipes/ package, GET /api/recipes + POST /api/credentials, inline
  .env.local key entry. MODEL-PER-CANDIDATE PICKER (#4). MODEL CATALOG (#1). DATASET IMPORT (#9).

THE DECISION-RECIPES THREAD (operator's strategic bet). Done: #1 catalog, #4 picker, #5 recipes.
LIVE-REVIEW FINDINGS: #1 leaderboard bug DONE, #3 fable-5 removal DONE. #2 similarity rubric NEXT.

>> START HERE — FIRST ACTION: invoke the `superpowers:brainstorming` skill for FINDING 2:
   SIMILARITY-RUBRIC WEAKNESS (last of the three live-review findings). Brainstorm BEFORE any
   plan/code — present a design and get operator approval first.
   The v0 rubric is string-similarity @ threshold 0.8 vs the expected prose, so a CORRECT summary in
   a different FORMAT scores low (live: a clean Markdown table scored 0.12/Fail). It rewards matching
   phrasing/format, not meaning. Points to an LLM-as-judge / semantic rubric (charter "optional,
   later" — this run is the evidence). Interim option: lower default threshold / document format-
   sensitivity. Brainstorm weigh-points (scoring-semantics decision): keyless-mock default (an
   LLM judge needs a provider → how do keyless tests/CI stay deterministic? a fake/mock judge?),
   cost, and whether the receipt should record the rubric kind + judge model in provenance
   (config_hash). Touches proof/ scoring (rubric application in engine/scoring) + domain Rubric model
   (already has kind/threshold/case_sensitive) + possibly a new judge provider. Details in
   docs/worklog/2026-06-20-decision-recipes.md §"Finding 2".
   THEN #6 PROMPT-VARIANT CANDIDATES (same model, different system prompt; composes with picker +
   recipes), and the CATALOG PRICE/SOURCE pass. Workflows/RAG remain post-v0.

OTHER (non-blocking — do NOT gate Finding 2 on these):
- CATALOG PRICE/SOURCE accuracy is a ROADMAP item (a few values approximate/UNVERIFIED). A measured
  receipt cost always outranks a catalog list price downstream, so it never blocks the proof loop.
- A general prices⊆catalog drift-guard test was deliberately NOT added (pricing.py keeps legacy/test
  ids + OpenRouter uses a different id format → a naive guard false-fails). Revisit only if a non-
  fragile shape emerges. Cosmetic minors (final review): winnerOf redundant `?? undefined`; no
  dedicated HTML test for the errored-row annotation (MD is tested; _failures_label is shared);
  _all_errored defined per-call. CLOUD_KEY_NAMES Py/TS dup (from the recipes session) still open.
- Set up a git remote + PUSH (none configured; ALL main commits are local only).

Do NOT regress: leaderboard NEVER recommends a 0-pass / all-errored candidate (recommended requires
pass_count>0; all_errored ranks last); the no-winner state is calm + NEUTRAL (panel colors, no
accent, no badge) across cockpit + all 3 receipt formats; errored rows say "errored, no output";
RECEIPT_VERSION stays 4 (bump again on ANY further receipt-schema change); config_hash + run
provenance UNTOUCHED (error_count is the only additive leaderboard field; default_model_for single
source of truth; ORIONFOLD_<P>_MODEL override precedence; catalog drift-guard anthropic=claude-haiku-
4-5). Keyless mock default (mocks pre-selected, bare-id, model=None); Proof Run is the DEFAULT view;
the 3-format receipt; both run endpoints route through build_candidates; /api/selection + /api/catalog
+ /api/recipes leak NO secrets; /api/credentials NEVER echoes/logs a key + writes ONLY whitelisted
cloud providers to a 0o600 .env.local; the global 422 input-stripping handler stays. Test-contract
strings (heading "Orionfold Proof", "Connected", button /Run proof/ — lowercase p, regions Leaderboard
/ Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)", "Failure cases
(5)", "simulated provider failure"). Verdict vocabulary now ALSO includes "No clear winner". Tailwind
v4: CSS vars use the PARENTHESIS shorthand bg-(--color-x), never bg-[--color-x].

NOTES (non-blocking):
- A sibling orionfold-proof-codex checkout runs its own servers; leave its processes/tabs alone and
  bind a PROVABLY-FREE port (assert the listener PID is yours). uvicorn does NOT hot-reload backend
  code OR the @cache load_catalog()/load_recipes() data — RESTART `orionfold up` after backend/catalog/
  recipe changes. The embedded cockpit is served from src/orionfold/server/static (gitignored; rebuilt
  by `bash scripts/build.sh` — REBUILD before any e2e or browser check). catalog.json + recipes.json
  ship in the wheel automatically.
- The harness emits STALE TS "cannot find module / @playwright/test" diagnostics mid-edit — false
  alarms; this session one mid-edit snapshot even claimed `error_count` / `DecisionSummary` errors that
  were ALREADY fixed. Trust `pnpm --dir web build` (tsc --noEmit && vite build) + the actual e2e run.
- create-dataset route field is `text` (not `content`): POST /api/datasets {name, format, text}.
- Regenerate sample receipts after ANY receipt change: `uv run python scripts/gen_samples.py` (the
  bundled sample keeps mock_good as a 5/5 winner; mock_bad shows a non-zero error_count).
Start in plan mode for anything substantial; brainstorm creative/feature work first. Verify with
uv run pytest, uv run ruff check src tests, pnpm --dir web test, the Playwright e2e (rebuild embed
first), and a real browser/server check on a free port. Open review-bound markdown in Obsidian one at
a time. Append a docs/worklog entry and overwrite HANDOFF.md.
```

## Where to look (durable context)

- `docs/worklog/2026-06-20-leaderboard-recommendation-fix.md` — this session's evidence (latest).
- `docs/superpowers/specs/2026-06-20-leaderboard-recommendation-fix-design.md` ·
  `docs/superpowers/plans/2026-06-20-leaderboard-recommendation-fix.md` — design + 5-task plan.
- `docs/worklog/2026-06-20-decision-recipes.md` — recipes (#5) + the §Findings that scoped this work
  (incl. the still-open Finding 2 details).
- `docs/ux/product-design-system.md` — the three-pane target + Theming subsection.
- `docs/adr/0001-…-architecture.md` · `0002-provider-integration-and-credentials.md` ·
  `0003-streaming-run-progress.md` — Accepted.
- `docs/release-charter.md` — v0 scope, journey, acceptance criteria (Accepted; all met).
- `CHANGELOG.md` ([Unreleased] now covers the leaderboard fix + fable-5 removal) · `docs/demo-script.md`.
- `.claude/rules/{providers,receipts,storage}.md` — enforced constraints.
- `CLAUDE.md` — operating guide and release gates.

## Ship-candidate quick reference

- Build wheel: `bash scripts/build.sh` → `dist/orionfold_proof-0.1.0-py3-none-any.whl`
  (cockpit + dataset embedded, RECEIPT_VERSION=4, catalog.json + recipes.json bundled). dist/ and
  src/orionfold/server/static are gitignored.
- Clean-install check: `uv venv /tmp/x && uv pip install --python /tmp/x/bin/python dist/*.whl`
  then `/tmp/x/bin/orionfold up --port <free>` — bind a PROVABLY-FREE port; confirm the listener
  PID is yours.
- Dev: `uv run orionfold dev` + `pnpm --dir web dev`. Tests: `uv run pytest` · `uv run ruff check
  src tests` · `pnpm --dir web test` · `pnpm --dir web e2e` (rebuild embed first). Frontend build:
  `pnpm --dir web build`.
- Regenerate sample receipts after any receipt change: `uv run python scripts/gen_samples.py`.
- Inspect recipes live: `curl -s localhost:<port>/api/recipes | python -m json.tool`. Picker panel:
  `curl -s localhost:<port>/api/selection | python -m json.tool`.
- Env knobs: `OPENAI_API_KEY` `OPENROUTER_API_KEY` `GEMINI_API_KEY` `ANTHROPIC_API_KEY` (also
  settable in-app via POST /api/credentials → .env.local); `OLLAMA_HOST` `OPENAI_BASE_URL`
  `OPENROUTER_BASE_URL` `LMSTUDIO_BASE_URL`;
  `ORIONFOLD_{OLLAMA,OPENAI,OPENROUTER,GEMINI,ANTHROPIC,LMSTUDIO}_MODEL` (override catalog default);
  `ORIONFOLD_MAX_TOKENS` (2048) `ORIONFOLD_TIMEOUT_S` (120) `ORIONFOLD_ENV_FILE` `ORIONFOLD_DB`.
