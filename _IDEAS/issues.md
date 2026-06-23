# Issues — bugs, broken states, UX breaks

> See [README.md](README.md) for the entry template and legend. Logged, not fixed.

<!-- Entry template:
## <Title>
- **Severity / Effort:** <low|med|high> / <quick-win|deeper>
- **Route / State:** <view> · <empty|loading|error|populated> · <light|dark>
- **Observed:** <what the ICP saw>
- **Evidence:** <screenshot path>
- **Recommendation:** <concrete fix>
- **Reuse source:** <peer path, if any>
-->

## Decision question persists stale across a dataset change
- **Severity / Effort:** med / quick-win
- **Route / State:** Proof Run · Configure · populated · dark
- **Observed:** After switching the dataset from "Investment memo summarization" to my new
  "Support ticket triage v1", the **Task name** auto-updated to the new dataset name, but the
  **Decision question** stayed `"Which model should I trust for client memo summaries?"` — now
  contradicting the task. Since the decision question "headlines the receipt" (per its own
  helper text), a stale question would print a wrong headline on a client-facing proof.
- **Evidence:** ss_4759f9elr (task name synced), ss_4346eki0u (stale question)
- **Recommendation:** When the dataset changes, either re-derive the decision question from
  the dataset (as Task name already does) or clear it and show the recipe placeholder, so the
  two config fields can't disagree. At minimum, flag a mismatch before Run.

## Stale decision question is FROZEN into a saved Quick receipt (artifact-level)
- **Severity / Effort:** med / quick-win
- **Route / State:** Proof Run · Quick ⚡ + Receipts · populated · dark
- **Observed:** In Quick mode I A/B'd a **release-notes** prompt on Haiku 4.5 vs GPT-5.4 nano,
  picked GPT, and saved. The saved Quick receipt's headline Decision is **"Which model should
  I trust for client memo summaries?"** with **Task = "Investment memo summarization"** — both
  inherited from the prior Models run, neither matching the actual release-notes prompt. So a
  three-way mismatch (decision ≠ task ≠ prompt) is now **persisted into the receipt** (verified
  in the exported MD: Decision/Task lines). The decision question "headlines the receipt," so
  this mis-titles a shareable artifact.
- **Evidence:** archive row ss_2198ewv5o ("Which model should I trust for client memo
  summaries?" on a Quick Compare); MD receipt Decision/Task lines (API fetch of
  run_fe0e4584b4a7).
- **Recommendation:** Same fix as the config-time stale-question issue, but it matters more
  here because Quick mode has no dataset to anchor the title. Derive the Quick receipt headline
  from the prompt (or prompt a short title on save), and clear the carried-over decision
  question when entering Quick mode.

## Dataset "check hint" does not drive the run's Scoring method (taxonomy mismatch)
- **Severity / Effort:** med / deeper
- **Route / State:** Proof Run · Configure · populated · dark
- **Observed:** The dataset was frozen with check hint **"Exact match"** (a single-label
  classification set: `billing`, `bug`, `how-to`…). On the run config, **Scoring method →
  Auto** reports it "Picks the best free check — here, **Similarity**." Similarity is the wrong
  check for exact labels ("billing" vs "Billing issue" scores as ~partial, not a clean
  pass/fail). The two vocabularies don't even align: the dataset hint set is {Contains text,
  Numeric match, Exact match, Eyeball/judgment} while the run methods are {Auto, Keypoint,
  Similarity, LLM judge} — there is no "Exact match" run method at all.
- **Evidence:** dataset hint ss_68120ow5r; run Auto→Similarity ss_4346eki0u
- **Recommendation:** Unify the two taxonomies (or map them explicitly): an "Exact match"
  hint should make Auto resolve to an exact/normalized-equality check, and an exact-match
  scoring method should exist. Surface the resolved check in the Auto card ("from your dataset
  hint: Exact match") so the link is visible. Mis-scoring directly corrupts the leaderboard,
  which is the product's core artifact.

## REAL-RUN: a classification task scores 0/5 on every model → misleading "NO CLEAR WINNER"
- **Severity / Effort:** high / deeper
- **Route / State:** Proof Run · Decide · populated · dark
- **Observed:** A real 3-model × 5-example run (Claude Haiku 4.5 · GPT-5.4 nano · Llama 3.1 8B,
  all Cloud) on the "Support ticket triage" exact-label dataset produced **0% pass / avg score
  0.00 for ALL three** and a top-banner verdict **"NO CLEAR WINNER — No candidate passed the
  rubric."** Inspecting a failure case (Inspector → Failure case · Example 1) shows the real
  cause: Input = the raw ticket "I was charged twice…", Expected = `billing`, **Output =** a
  long help-desk paragraph ("I appreciate you reaching out, but I'm not able to process
  refunds… 1. Contact customer support… 2. Gather documentation…"). The models tried to **help
  the customer**, not **classify** the ticket, because the dataset sends the raw input as the
  whole prompt — there is **nowhere to attach a task instruction / system prompt**. Then
  Similarity@0.8 scores the verbose answer ~0 vs the bare label. Net: a task the models could
  plausibly do well reads as a total failure on a client-facing proof.
- **Evidence:** verdict+leaderboard ss_07963zcfs; failure list ss_8576pnoow; failure detail
  (Input/Expected/Output) ss_6884d83e8 / ss_39451r14x.
- **Recommendation:** (1) Add a **task instruction / prompt template** to the run (or dataset)
  — e.g. a system prompt "Classify the ticket into exactly one of: billing, bug, how-to,
  feature-request, account-access. Reply with only the label." Biggest gap for the
  classification/extraction ICP use cases. (2) Pair with exact/normalized scoring (see the
  taxonomy issue above). (3) Consider an **answer-extraction** step (last line / strip
  markdown) before scoring so a correct label buried in prose still passes.
- **Reuse source:** Orionfold AI Native `src/lib/workflows/` blueprints (prompt templates +
  variable resolution); `lib/agents/profiles/` (system-prompt handling).

## REAL-RUN: the flagship demo dataset also reads "NO CLEAR WINNER" with real models (threshold too strict)
- **Severity / Effort:** high / med
- **Route / State:** Proof Run · Decide · populated · dark
- **Observed:** Re-ran the SAME 3 cloud models on the bundled **"Investment memo
  summarization"** dataset (the product's showcase set, designed for Similarity scoring). Result:
  again **0% pass / NO CLEAR WINNER**, but now with **non-zero** avg scores — OpenAI 0.22,
  OpenRouter 0.12, Anthropic 0.06. The models genuinely summarized; they just don't reach the
  **default Similarity threshold of 0.80**. A good human-quality summary phrased differently
  than the reference scores ~0.2–0.5 on lexical/embedding similarity, not 0.8. So the
  out-of-the-box real-model experience on the FLAGSHIP demo is a discouraging "no winner."
  (The shipped sample receipt likely looks clean only because it was generated by **mocks** —
  mock_good echoes the expected verbatim → similarity 1.0.)
- **Evidence:** ss_0664sxxnm (scores 0.22 / 0.12 / 0.06, all 0% pass at threshold 0.80)
- **Recommendation:** Recalibrate so the first real run is encouraging: (a) lower the default
  Similarity threshold for summarization to a realistic band (~0.45–0.6) OR (b) make the demo
  default to **LLM judge** (grades semantic adequacy, not lexical overlap) OR (c) per-method
  default thresholds. Whatever the choice, the bundled demo should produce a *clear winner* on
  real models, not "NO CLEAR WINNER." Also worth a calibration note in the Similarity card
  ("0.80 is strict; ~0.5 is typical for good paraphrased summaries").
- **Reuse source:** Orionfold Arena `arena-app/src/lib/arena/evals.mjs` (benchmark/check
  calibration patterns); LLM-judge rubric already exists in `src/orionfold/scoring/`.

- **UPDATE 2026-06-23 (post WS-A2/A3; fresh real-run during WS-D1 scatter demo).** Two of the
  three recommended levers have since SHIPPED, and a fresh real run shows option (a) alone is
  **insufficient** — the root cause is the *scorer*, not the threshold:
  - **Option (c) shipped (WS-A2 / Task 2):** per-method `DEFAULT_THRESHOLDS` now exists and the
    Similarity default was lowered from **0.80 → 0.55** (`scoring/rubric.py:23`), user-tunable via
    Settings sliders.
  - **Option (b) is now reachable (WS-A3 / Task 3):** a cloud-only user *can* now select a real
    cloud LLM judge (Sandbox-OFF no longer silently defaults to Mock — see the judge issue below).
    The demo does NOT yet *default* to it, but the path exists.
  - **NEW EVIDENCE the threshold band is a red herring:** re-ran 3 Anthropic tiers (Haiku $0.01 /
    Sonnet $0.03 / Opus $0.05) on this same dataset under the now-shipped **0.55** default. Result
    STILL **0% pass / no winner**, avg scores **0.06 / 0.06 / 0.15** (Auto→Similarity). These
    `difflib`-overlap scores are far below not just 0.55 but even ~0.45 — so lowering the band to a
    "realistic" 0.45–0.6 would NOT have produced passes here. Good paraphrased summaries simply
    don't reach those overlap numbers against a single fixed reference. **Lexical-overlap Similarity
    is the wrong scorer for free-form summarization, at any threshold.**
  - **Revised recommendation (priority order):** (1) **Make the flagship summarization demo default
    to LLM judge** (now that a real cloud judge is reachable post-A3) — semantic adequacy is the
    only honest scorer for paraphrase; threshold tuning can't fix overlap-based scoring of free
    text. (2) Keep Similarity available but add the calibration note AND a gentle inline hint when
    Auto→Similarity yields all-fail with non-trivial avg scores ("these look like real summaries
    scoring low on lexical overlap — try LLM judge"). (3) Consider seeding the bundled dataset with
    multiple acceptable references or keypoints so a free scorer can still find a winner.
  - **Scatter angle (WS-D1, just shipped):** the new cost-vs-quality scatter *correctly* rendered
    this degenerate run — all three at quality 0 in danger-pink, spread across the real cost axis
    ($0.01→$0.05), no accent point (nothing recommended). The scatter is faithful; it's the
    SCORING that produces the discouraging "no winner." This is the strongest visual argument yet
    for fixing the demo default: a first-time user sees three failing dots and an empty frontier.
  - **Ties to:** issue #1 (the same Auto→Similarity taxonomy/heuristic mismatch); _IDEAS feature
    "guided first-run CTA" (WS-E2, Task 9) — a one-click demo CTA is pointless if the demo it runs
    reads "no winner." **Sequence E2 AFTER fixing this scorer default.**
  - **✅ RESOLVED 2026-06-23 (`50155bb`).** The bundled `is_sample` summarization demo now
    **defaults to the LLM judge** (FE-only): new pure `prefersSampleJudge(dataset, judgeCell)` in
    `web/.../scoring.ts` + a latched effect in `ScoringMethod.tsx` auto-select the judge for the
    sample when a *real* (non-mock) judge resolved (reuses A3 `defaultJudgeCell`; Sandbox keeps its
    keyless demo; keyless user stays on Auto, never silent Mock). Real-model verified: the same
    dataset that read "NO CLEAR WINNER" at 0.06–0.15 now yields a **clear winner** (RECOMMENDED
    claude-haiku-4-5, 60% pass, avg 0.71, "Scored by: LLM judge"). **This unblocks WS-E2 / Task 10.**

## LLM-judge is unavailable to a cloud-only user (judge picker excludes cloud providers; defaults to Mock)
- **Severity / Effort:** high / med
- **Route / State:** Proof Run · Configure (LLM judge expanded) · populated · dark
- **Observed:** Selecting **LLM judge** reveals Run-on (Local/Hosted), Optimize
  (Cheapest/Balanced/Best), and a **Judge model** dropdown. With real keys configured and
  Sandbox OFF, the Judge model options are ONLY: `Mock judge — keyless, deterministic`
  (selected by default), `Llama 3.2 (local) · Ollama`, `Loaded LM Studio model · LM Studio`.
  **No cloud judge** (Anthropic/OpenAI/OpenRouter) is offered, even though all three are valid
  candidates with working keys. So a cloud-only consultant (no local Ollama/LM Studio running)
  cannot run an LLM-judge proof at all, and the default judge is a **mock** — contradicting
  Sandbox being off and silently downgrading a "real evaluation" to a simulated grade.
- **Evidence:** judge sub-config ss_8905r7zfi; dropdown options (read_page ref_439): only
  mock + ollama + lmstudio.
- **Recommendation:** Populate the Judge model list from the same key-gated cloud providers
  used for candidates (offer e.g. "GPT-5.4 nano (judge)", "Claude Haiku 4.5 (judge)"). When
  Sandbox is OFF, do NOT default the judge to the mock — default to a real, configured judge
  (or disable LLM judge with a clear "add a provider key or start Ollama" hint). The
  "Hosted" Run-on option implies cloud judging is intended but nothing hosted is selectable.
- **Reuse source:** the candidate registry already key-gates cloud providers
  (`src/orionfold/providers/registry.py`); reuse the same resolution for judges.
