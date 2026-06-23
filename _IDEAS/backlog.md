# _IDEAS — Backlog (someday / low-priority)

> Long-tail items deliberately **deferred, not fixed**. Each is non-blocking, has a known
> harmless current behavior, and a clear (if minor) future improvement. Promote into a
> `_SPECS/` workstream only when it earns priority. Sibling files: [issues.md](issues.md),
> [feature-opportunities.md](feature-opportunities.md), [design-system.md](design-system.md).

## B1 · Exact rubric shows `≥ 0.8` threshold in the receipt — cosmetic

- **Priority:** Someday / LOW. Cosmetic only; no behavioral impact.
- **Surfaced:** 2026-06-23, during WS-B verification (check-hint → scoring-method mapping).
- **What happens.** When a dataset's check-hint resolves Auto to **Exact** (or the user picks
  the Exact card), the exported receipt prints `Rubric: exact ≥ 0.8 · Scored by: Exact match`.
  The `0.8` is the `Rubric.threshold` *field default* — `"exact"` is intentionally **not** in
  `DEFAULT_THRESHOLDS` (`src/orionfold/scoring/rubric.py`), so `threshold_for("exact")` falls
  back to that field default.
- **Why it's harmless.** Exact is a **binary** check — the scorer returns exactly `1.0` (match)
  or `0.0` (no match). Any threshold in `(0, 1]` yields the *identical* pass/fail partition, so
  `≥ 0.8` and `≥ 1.0` grade the same. (The selectable Exact card already seeds `threshold: 1`;
  only the Auto-resolved path shows `0.8`.) Verified clean in the WS-B e2e run — both candidates
  100% (5/5), zero failures.
- **Possible future polish (pick at most one, only if it earns priority):**
  - Suppress the `≥ N` threshold display in receipts for binary kinds (`exact`/`contains`) —
    print just `Rubric: exact` / `Scored by: Exact match`.
  - Or normalize the Auto-resolved binary-kind threshold to `1.0` so the displayed value reads
    as "must match exactly."
- **⚠ Guardrail if ever touched.** Threshold/numeric-tolerance redesign was **explicitly fenced
  out of WS-B scope** (spec §WS-B "Out of scope"). Any change here must keep the mock matrix
  `config_hash 467ddd96c9a5` unchanged (the mock dataset carries no hint → still keypoint@0.8,
  untouched) and must not alter pass/fail outcomes for existing receipts.
- **Anchors:** `src/orionfold/scoring/rubric.py` (`threshold_for`, `DEFAULT_THRESHOLDS`,
  `default_rubric_for`) · receipt render in `src/orionfold/receipts/export.py` · spec
  `_SPECS/2026-06-22-trustworthy-proof-and-polish.md` §WS-B.

## B2 · Quick→Promote silently drops the prompt — UX seam

- **Priority:** Someday / LOW–MED. Non-blocking; the destination is by-design, only the journey is rough.
- **Surfaced:** 2026-06-23, operator question during WS-C thread. (Previously a one-liner in the
  volatile HANDOFF backlog; persisted here as the durable home.)
- **What happens.** In Quick mode the user types any free-text prompt with **no dataset**. Clicking
  **"Promote to a full scored run →"** runs `onPromote` (`web/src/features/proof/ProofCockpit.tsx:267-270`):
  it `setCompareBy("models")` + `setSelected(...candidates)` — carrying the **2 candidates** but
  **dropping the prompt**, and landing the user in Models mode (dataset-anchored) at an **empty dataset
  picker**. The prompt they cared about vanishes with no explanation or bridge.
- **Why the destination is correct (feature, not bug).** Promote's purpose is to convert a one-off
  eyeball check (`rubric:{kind:"none"}`, `score=None`) into *repeatable scored proof*, which **requires
  a set of examples to score against** — i.e. a dataset. So Promote *must* land somewhere with a
  dataset. The prompt-drop is intentional (was HANDOFF backlog #1, "by design").
- **Why it still feels like a bug.** The transition is silent and lossy: typed prompt → gone; dropped
  into a blank picker; no scaffolding to turn the ad-hoc prompt *into* the proof. Breaks the "calm
  instrument panel" promise at exactly the conversion moment.
- **Possible future improvement (pick when it earns priority):** seed the prompt into a **one-example
  set** so Promote carries candidates **and** prompt, landing on a runnable scored config (prompt =
  example 1) instead of an empty picker. At minimum, a quick honest bridge: a dismissible notice on
  arrival ("Your Quick prompt isn't carried — pick a dataset to score against").
- **⚠ Forks to resolve in a spec before building (two protected invariants).**
  - **Dataset persistence:** ephemeral staged set (like Quick's `Dataset(id="quick-compare")` which
    writes **no** row) vs a written dataset row (then append-only **migration index 6** +
    `is_sample`/metadata handling — see HANDOFF "Datasets metadata" invariant).
  - **Scoring with no expected:** a promoted prompt has no `expected_text`; Quick used `{kind:"none"}`
    but a *scored* run needs a real rubric — prompt the user for the expected answer / keypoint, or
    pick a default. This is the crux that makes it a real product decision, not a mechanical fix.
- **Anchors:** `web/src/features/proof/ProofCockpit.tsx` (`onPromote`, Quick payload ~`:234`) ·
  `QuickCompare.tsx` (promote CTA) · HANDOFF invariants "Quick-Compare" + "Datasets metadata".

## B3 · Brainstorm real-world demo datasets drawn from our own `~/orionfold/` projects

- **Priority:** Someday / MED. Non-blocking — the bundled *Investment memo summarization (5 examples)*
  sample already carries the demo path. This is about **stronger, more credible proof material**, not
  fixing a defect.
- **Surfaced:** 2026-06-23, operator directive during a browser-use watch session.
- **The idea.** Replace/supplement synthetic samples with datasets distilled from **our own lived
  project experience** across the sibling `~/orionfold/` portfolio, so the demo reads as "a real
  builder's actual task" rather than a toy. Each becomes a frozen example set a user can run a proof
  against on first launch.
- **Source projects to mine (study before deciding which earn a dataset):** `~/orionfold/` contains
  `agency`, `ainative`, `books`, `consulting`, `credentials`, `llc`, `marketing`, `self-health`,
  `self-proofs`, `self-wealth`, `spark-mac`, `strategy`, `website`. Candidate task shapes worth a
  look: summarization (consulting/strategy memos), classification (marketing/support intents),
  extraction (credentials/llc structured fields), rewrite (website/marketing copy), judgment-style
  free-text (self-proofs / self-health coaching).
- **⚠ Brainstorm FIRST (operator directive — do not jump to building).** Open questions to resolve in
  a spec before any seeding code:
  - **Privacy / local-first.** Real project data may contain personal or client-sensitive content.
    Bundling it into a shipped sample dataset conflicts with the "private, local-first" promise and
    the secrets-guard posture. Decide: synthesize *representative* examples inspired by real tasks
    (safe to ship) vs. keep real datasets local-only (user-imported, never bundled).
  - **Which decision does each dataset prove?** A dataset only earns its place if it makes a *better
    Proof Receipt* — i.e. it cleanly separates candidates (clear winner, not "NO CLEAR WINNER"). Pick
    task shapes where a real model difference shows.
  - **Scoring fit.** Match each dataset to a rubric that actually discriminates (cf. the
    demo-scorer-default work — paraphrase tasks need the LLM judge, not lexical/keypoint).
  - **Count & licensing.** How many ship vs. import-on-demand; any attribution/licensing on source
    material.
- **Next step when it earns priority:** run a `brainstorming` skill pass over the `~/orionfold/`
  projects → produce a short `_SPECS/` workstream naming the 1–3 datasets, their task shape, expected
  rubric, and the privacy decision (synthesize vs. import-only). **No seeding code until that spec is
  operator-approved.**
- **Anchors:** bundled sample seeding (`insert_sample_dataset` / `seed_sample_data`, `is_sample`
  metadata) · demo-scorer-default work (sample datasets default to LLM judge) · `~/orionfold/`
  sibling projects.

## B4 · Reimagine the "Candidates" screen — naming + purpose + repurpose Arena's models leaderboard

- **Priority:** Someday / MED–HIGH (product direction, not a defect). The screen works and ships;
  the operator is **not happy** with both its **name** and its **value density** for our ICP.
- **Surfaced:** 2026-06-23, operator product critique while walking the live cockpit.
- **The two complaints.**
  1. **Naming.** "Candidates" is abstract jargon. Why not simply **"Models"**? (Caveat to resolve in
     brainstorm: the nav object is broader than models — the cockpit's "Compare by" axis is
     **Models / Prompts / Quick**, and the charter's core objects include *Candidate* as the thing
     being proved, which can be a model *or* a prompt variant. So "Models" is more legible but may
     under-describe prompt candidates. Decide: rename to "Models" and treat prompts elsewhere, vs. a
     different plain-language name, vs. keep "Candidates".)
  2. **Low value / duplicate info.** The screen
     (`web/src/features/proof/CandidatesView.tsx`) is a **read-only mirror** of the per-provider
     candidate list already shown in Proof Run setup — same providers, same model names + ids, same
     "Not configured / add a key" affordance (`getSelection` → `ProviderCard`). It repeats setup
     info with **limited additional value**: no comparison, no history, no decision support. It's an
     inventory list, not a decision instrument — off the charter's "decide what to trust" north star.
- **The operator's reframe (the real ask).** **Reimagine what's valuable here for our ICP** (AI
  builders/consultants/small teams deciding what to trust). Specifically: **revisit Orionfold
  Arena's "models leaderboard" feature and repurpose it here.** Idea: instead of a static
  available-models inventory, this screen could become a **standing, cross-run models leaderboard** —
  "across all my proof runs, how has each model actually performed (pass rate, avg score, $/quality,
  latency, win count)?" — turning a dead inventory page into an evidence-backed model-trust view.
- **⚠ Brainstorm FIRST — open questions before any build.**
  - **Local-first data source.** A cross-run leaderboard aggregates the local SQLite proof history
    (runs/receipts), NOT a hosted/global Arena leaderboard. Define the aggregation: per-model
    rollup across this user's runs (pass rate, avg score, $, latency, #runs, last seen). Honors
    local-first; no network, no shared ranking.
  - **What Arena actually gives us (reuse boundary).** Per memory note
    [[charting-library-recharts.md]]: Arena's `FrontierScatter` is **uPlot/preact — NOT directly
    reusable**; only the **paretoFrontier math** ports. Proof already has its OWN Recharts
    `FrontierScatter` (`web/src/features/proof/FrontierScatter.tsx`, WS-D1) for cost-vs-quality. So
    "repurpose Arena" likely means **port the leaderboard CONCEPT/columns + reuse Proof's existing
    Recharts scatter + paretoFrontier**, not lift Arena's component. Confirm what's worth porting by
    studying the Arena leaderboard's columns/sorting/insight copy.
  - **Cross-run comparability.** Models are only comparable across runs if scored on the **same
    dataset + same rubric/scorer** (cf. demo-scorer-default + config_hash). A naive global average
    mixes incomparable runs. Decide: scope the leaderboard per-dataset, or surface "comparable
    within these runs" groupings, or weight by config. **This is the crux** that makes it honest
    proof vs. a misleading vanity metric.
  - **Empty state.** A fresh install has no run history → the screen must still teach (what it WILL
    show) and not regress the current "what's available + add a key" usefulness. Possibly: leaderboard
    when history exists, inventory/onboarding when it doesn't.
  - **Naming follows function.** Resolve the rename *after* deciding the screen's job — "Models",
    "Model Leaderboard", "Track Record", etc. should describe what it now does.
- **What Arena's leaderboard actually IS (studied 2026-06-23 at https://orionfold.com/software/arena/
  — the operator clarified it's "more than the chart… lmarena-like model leaderboard").** It is NOT
  just the Pareto scatter; it's a full LMArena-style **ranked board** PLUS the scatter, side by side.
  Per the product page, "the leaderboard is the Arena's memory" — its concrete elements:
  - **Ranked, grouped board.** Models rank in **groups per test** (a frozen test set), with
    **medals on the top three** of each group. Each new chat or compare **folds into a live section
    as you work** — the board updates continuously from real results, it is not a static snapshot.
  - **"Reads like a product, not a lab log."** The flagship/house group renders **first** with
    **plain-language names** (not raw model ids) and **small pills** per row for (a) the row's
    **role** and (b) the **frozen test** its score came from — while the **raw run id stays printed
    under every name** so a friendly label "can never hide which data it points at." (This is the
    exact integrity discipline Proof already cares about — config_hash / run id provenance.)
  - **Per-row provenance badge** — whether each number came from a **local (Spark)** model or a
    **hosted/cloud** model. (Maps cleanly onto Proof's Local/Cloud/Mock `ProviderTag`.)
  - **Publishable safe-slice.** The board is built from a slice that **exports only scores — never
    prompts or replies** — so it can be published while keeping data private. (Local-first aligned;
    a future Proof "share this board" must inherit this no-private-text rule.)
  - **Paired Pareto chart (screen 05).** Quality-vs-speed, best trade-offs drawn as the **orange
    frontier**, flagship marked with a **violet diamond**. Proof ALREADY has this as the WS-D1
    Recharts `FrontierScatter` (cost-vs-quality) — so this half is largely built; the **ranked board
    above it is the missing piece** the operator wants ported here.
  - **Note for translation to Proof's ICP/data:** Arena ranks *locally-built/quantized model builds*
    on a *Spark* (throughput/memory framing). Proof's ICP ranks *provider models/prompts* across the
    user's *proof runs* (cost/$ + pass-rate framing). Same leaderboard SHAPE (grouped-per-test,
    medals, plain names + run-id provenance, local/cloud badge, publishable safe-slice, paired
    frontier), different metrics. Port the **shape and integrity rules**, swap the **axes**.
- **The ACTUAL Arena source (operator pointer: `/Users/manavsehgal/Developer/ainative-business.github.io`).**
  Read the real components — far better than the marketing page for the spec:
  - **Frontend board:** `arena-app/src/components/arena/LiveLeaderboard.jsx` (preact, 250 lines) +
    `arena-app/src/lib/arena/leaderboard-format.mjs` (column formatters) + `SourceBadge.jsx`.
    **NOT directly reusable in Proof** (preact + SSE sidecar + Arena's own CSS vars), but the
    **column schema + grouping + sort + qualifier logic port as concepts.**
  - **Concrete column schema (from the formatters — this is what "lmarena-like" means here):**
    Model name (`laneModel`, openrouter prefix stripped) · **Source badge** local/cloud
    (`SourceBadge`) · **Bench/test** (`benchLabel`) · **Quality %** (`pct`) · **Throughput** tok/s
    (`fmtTok`) · **TTFT** ms (`fmtTtft`) · **Preference %** (`fmtPref`, head-to-head win rate) ·
    **Cost** (`fmtCost`) · **Cost-per-quality** (`fmtCostPerQuality`). Grouped by bench
    (`bench-group`), medals on top 3, **live SSE refresh on `leaderboard_rev`** (no rebuild).
  - **⭐ Steal this — the `fmt` score qualifier (AF-27, `LiveLeaderboard.jsx:37-45`).** Arena flags
    scores from **format-only rubrics** (regex/substring, e.g. `generic-correctness`, `mcq_letter`)
    with a `fmt` qualifier so "a wrong-but-well-formatted answer can't read as 100% quality." This is
    the SAME trap Proof's demo-scorer-default work fought (lexical/keypoint scoring paraphrase ~0).
    Porting this qualifier convention into Proof's leaderboard/receipt is a concrete high-value
    integrity win, independent of the bigger reimagining.
  - **Backend safe-slice:** `fieldkit/src/fieldkit/arena/mirror.py` (the score-only export) +
    `store.py`, guarded by `fieldkit/tests/arena/test_mirror_does_not_leak.py` — the executable spec
    for the "publish the board, never the prompts/replies" invariant if Proof ever adds sharing.
- **Next step when it earns priority:** `brainstorming` skill pass → re-walk the Arena leaderboard
  (now captured above) + Proof's existing `Leaderboard.tsx` (per-run, sortable, WS-F) and
  `FrontierScatter.tsx` (WS-D1) → produce a `_SPECS/` workstream defining the screen's new job
  (cross-run grouped board + paired frontier), data rollup (local SQLite), the **comparability rule**
  (group per dataset+rubric, the crux), naming, publishable safe-slice, and empty state. **No code
  until that spec is operator-approved.**
- **Anchors:** PROOF side — `web/src/features/proof/CandidatesView.tsx` (today's inventory mirror) ·
  `getSelection`/`ProviderCard` · existing `web/src/features/proof/FrontierScatter.tsx` +
  `paretoFrontier.ts` (WS-D1, Recharts) · `Leaderboard.tsx` (per-run leaderboard, sortable, WS-F) ·
  charter core objects (Candidate = model *or* prompt) ·
  `docs/superpowers/specs/2026-06-22-leaderboard-presentation-design.md`.
  ARENA side (source at `/Users/manavsehgal/Developer/ainative-business.github.io`) —
  `arena-app/src/components/arena/LiveLeaderboard.jsx` · `.../lib/arena/leaderboard-format.mjs` ·
  `SourceBadge.jsx` · `fieldkit/src/fieldkit/arena/mirror.py` + `store.py` +
  `tests/arena/test_mirror_does_not_leak.py`. Public page:
  https://orionfold.com/software/arena/ (screens 04 board + 05 frontier). Memory
  [[charting-library-recharts.md]] (Recharts/uPlot reuse boundary).

## B5 · Make "Quick Compare" more whole — mine Arena's CompareDuel for ideas

- **Priority:** Someday / MED–HIGH (feature depth, not a defect). Proof's Quick Compare ships and
  works; the operator wants it to feel **more whole / complete** for our ICP.
- **Surfaced:** 2026-06-23, operator product critique while walking the live cockpit; directed to
  study Arena's compare feature (source + marketing) for ideas.
- **What Proof's Quick Compare is today** (`web/src/features/proof/QuickCompare.tsx`, 147 lines):
  an **unscored head-to-head** — two outputs side by side, **objective bars** (latency / cost /
  tokens) in neutral ink, the **operator's pick** (`patchWinner`), and a **"Promote to a full scored
  run"** CTA (the B2 seam). Static: both outputs already computed, rendered at once. No streaming, no
  inline scoring, fixed candidate pair, plain-text outputs.
- **What Arena's CompareDuel is** (studied 2026-06-23, source
  `…/ainative-business.github.io/arena-app/src/components/arena/CompareDuel.jsx`, ~1300 lines +
  marketing screens 08/11 + "Try and test in one place"). A much fuller instrument. Ideas worth
  mining (each is a candidate, not a commitment — Proof is cloud-provider/dataset framed, not
  Spark/GPU framed, so translate, don't lift):
  1. **Live streaming duel.** A streams first, then B, then the score — `POST /api/compare/stream`
     SSE (`start_a → token_a* → done_a → start_b → token_b* → done_b → score`). Per-side card
     **pulses** while streaming. Proof renders all-at-once; streaming makes the compare feel alive
     and shows TTFT/tok-s honestly. (Proof's providers already stream-capable? confirm.)
  2. **Any-vs-any lane selection.** Pick either side from grouped pickers (Local · Frontier · Open ·
     Project bases / full catalog). Proof's Quick mode is a fixed pair — letting the user choose both
     sides (any candidate vs any) is the obvious "whole" upgrade.
  3. **Rich per-side answer cards.** Markdown render, a **reasoning fold** (💭 collapsible), a
     **Local/Cloud provenance badge** (Arena: "Spark GPU" vs "OpenRouter"; Proof: reuse Local/Cloud/
     **Mock** `ProviderTag`), and a **perf chip row** (TTFT · tok/s · ≈tokens · cost). Proof's
     outputs are plain text today.
  4. **⭐ Inline optional scoring — bridges the B2 seam.** Arena's free-prompt duel **can score
     deterministically inline** (pick a rubric → per-check ✓/✗ + why under each side), turning an
     eyeball compare into a scored one **without leaving the screen**. This is a direct answer to
     [[B2]] (Quick→Promote drops the prompt): instead of promoting away, offer "score this compare"
     in place. Resolves the same "unscored → scored" gap from the other direction.
  5. **⭐ The `fmt` "format check — not correctness" qualifier (AF-27).** Same integrity guard seen
     in B4: a format-scope rubric (regex/substring) is labelled "Format check — not correctness," and
     the winner banner says "passes more format checks," never "wins on quality." Directly relevant
     to Proof's scorer-honesty work (demo-scorer-default). Port this labelling wherever Proof shows a
     compare/score verdict.
  6. **Human preference as a SEPARATE signal.** 👍A / 👍B / ↔ Tie vote that **POSTs to /api/prefs and
     NEVER mutates the displayed rubric score** ("Operator pick (separate signal — does not change
     the score above)"); folds into the leaderboard only at **≥5 prefs**. Proof already has a "pick"
     (`patchWinner`) — but Arena's discipline of **keeping subjective pick vs objective score
     visibly separate** is the lesson (and ties into B4's leaderboard: a `Preference %` column).
  7. **Head-to-head MetricCards.** Quality/Format · tok/s · TTFT · Tokens · Cost as paired
     **magnitude bars on a shared scale** (longer bar = larger value, winner ✓, loser dimmed,
     lower-better honored for TTFT/Cost) + a **session-history sparkline** per metric. Proof's three
     objective bars are the seed; Arena's "bar length = the real value, directly comparable" + the
     winner mark is the more legible pattern.
  8. **Eval mode (pull a real test + gold).** Open a drawer, pull the exact bench row a model was
     measured on, score both sides **against the gold reference** (deterministic or judge). For Proof
     this = "compare on one of my dataset's examples, scored against its expected answer" — a natural
     fusion of Quick Compare with the dataset/rubric the product already owns.
  9. **Cost legibility.** Every side shows metered cloud spend OR an explicit **"$0 · local"** so a
     free local lane reads as free, not blank; a "~" prefix marks heuristic (estimated-token) cost.
     Small, high-trust detail Proof should match.
  10. **(Arena-specific, likely OUT for Proof):** ±Cortex grounding ablation (RAG on/off, same
      question); on-demand GPU model load with teardown→warming progress; single-memory-slot guard.
      These are Spark/local-serving concerns; note as out-of-scope unless Proof grows a RAG/local
      story.
- **⚠ Brainstorm FIRST — scope + invariant questions before any build.**
  - **Quick stays QUICK.** The whole point of Quick mode is a fast, no-dataset eyeball check. Don't
    rebuild CompareDuel wholesale and lose that. Pick the few ideas that deepen *without* adding
    setup friction (likely: streaming, any-vs-any lanes, richer cards, cost legibility, the `fmt`
    label) and defer the heavy ones (eval mode, full metric history) to the scored path.
  - **Relationship to B2 + B4.** Inline scoring (#4) overlaps B2's "promote drops the prompt" seam —
    decide if B5#4 *supersedes* B2 (score in place instead of promoting away). The preference signal
    (#6) feeds B4's leaderboard (`Preference %`). Sequence these three together in one spec.
  - **Streaming feasibility.** Confirm Proof's provider abstraction + run engine can stream per-side
    (Arena uses an SSE sidecar). If not, streaming is a bigger lift than the UI suggests.
  - **Don't double-count the pick.** Arena's hard rule: subjective pick and objective score are
    separate and the pick never edits the score. Preserve that if inline scoring lands.
- **Next step when it earns priority:** `brainstorming` pass over ideas 1–9 → choose the "keep it
  quick" subset → one `_SPECS/` workstream that also resolves the B2/B4 overlap (inline-score vs
  promote; preference→leaderboard) → operator approval before code.
- **Anchors:** PROOF — `web/src/features/proof/QuickCompare.tsx` · `quickCompareFormat.ts`
  (`objectiveBar`/`totalTokens`) · `patchWinner` · `ProviderTag` · [[B2]] (promote seam) · [[B4]]
  (leaderboard / preference column). ARENA (`/Users/manavsehgal/Developer/ainative-business.github.io`)
  — `arena-app/src/components/arena/CompareDuel.jsx` (the duel) · `EvalScore.jsx` /
  `EvalPromptDrawer.jsx` (eval mode) · `lib/arena/leaderboard-format.mjs`. Public page:
  https://orionfold.com/software/arena/ (screens 08 chat, 11 head-to-head).
