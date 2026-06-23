# Feature opportunities — desirability features

> See [README.md](README.md) for the entry template, legend, and peer-project reuse map.
> Each entry should cite a reuse source where one exists and mark quick-win vs deeper.

<!-- Entry template:
## <Title>
- **Severity / Effort:** <low|med|high> / <quick-win|deeper>
- **Route / State:** <view> · <state> · <theme>
- **Observed:** <gap or unmet ICP need>
- **Evidence:** <screenshot path>
- **Recommendation:** <concrete feature>
- **Reuse source:** <peer path>
-->

## Per-task instruction / prompt template (unblocks classification & extraction proofs)
- **Severity / Effort:** high / quick-win  (plumbing already exists — see NOTE below; UI-only add)
- **Route / State:** Proof Run · Configure · populated · dark
- **Observed:** The run sends each dataset Input as the entire prompt; there is no field for a
  task instruction or system prompt. For anything but free-form generation (classification,
  extraction, structured output — squarely in the ICP's wheelhouse) the models don't know the
  task, so they "help the user" instead of producing the expected artifact, and every candidate
  fails (see issues.md "REAL-RUN: …NO CLEAR WINNER"). A consultant can't prove a triage/extraction
  workflow today.
- **Evidence:** ss_6884d83e8 (model help-desk output vs expected `billing`)
- **Recommendation:** Add an optional **Instruction / prompt template** to the Proof Brief
  (with `{input}` interpolation), frozen into `config_hash` so the receipt stays reproducible.
  Bonus: ship 2–3 starter **decision/task blueprints** ("Classify into labels", "Extract a
  field", "Summarize to one line") that pre-fill instruction + scoring + a sample dataset shape.
- **Reuse source:** Orionfold AI Native `src/lib/workflows/` (blueprint templates: YAML +
  form instantiation + variable resolution) — directly maps to a starter-blueprint gallery;
  `src/lib/agents/profiles/` (system-prompt + tool catalog handling).
- **NOTE — plumbing CONFIRMED end-to-end (this is UI-only):** `system_prompt` is already
  threaded through the whole stack and is used today by **Prompts** compare mode (v6
  prompt-variant runs). Verified in source: `providers/anthropic.py:44` (`"system":
  system_prompt_for(candidate)`), `providers/openai_compatible.py:57` (system role message),
  `providers/gemini.py:39` (`systemInstruction`), `proof/engine.py:37-39` (added to config_hash
  **only when set**, so Models-mode runs with no instruction keep byte-identical hashes / the
  mock `config_hash 467ddd96c9a5` invariant), `proof/leaderboard.py:43`, and the receipt
  exporter renders it (`receipts/export.py:329` MD / `:498` HTML). **So Models mode just needs
  one optional "Task instruction" field** that sets the same `system_prompt` on every selected
  candidate. Setting it correctly changes the run's config_hash (different proof) — desired.

## Pareto "cost vs quality" frontier on the leaderboard (visual winner-picking)
- **Severity / Effort:** med / deeper
- **Route / State:** Proof Run · Decide · populated · dark
- **Observed:** The leaderboard is a strong table (pass rate, $/quality, avg score, latency,
  est. cost, failures) but the central decision — "which candidate is the best cost/quality
  trade-off?" — must be read across columns. A scatter would make the trade-off visible at a
  glance and is exactly the "which AI to trust" question rendered as one chart.
- **Evidence:** ss_07963zcfs (leaderboard table)
- **Recommendation:** Add an optional **cost-vs-quality scatter** beneath the leaderboard with
  a Pareto frontier line; points off the frontier are dominated. Reserve the accent for the
  recommended point; keep status colors for pass/fail only (DS accent/status split).
- **Reuse source:** Orionfold Arena
  `arena-app/src/components/arena/FrontierScatter.jsx` (Pareto skyline `paretoFrontier()`,
  group coloring, flagship marker — adapt axes to cost × pass-rate). Quality formatters in
  `arena-app/src/lib/arena/leaderboard-format.mjs`.

## Run-level cost summary / spend ledger (cost is a first-class ICP concern)
- **Severity / Effort:** med / quick-win
- **Route / State:** Proof Run · Decide · populated · dark
- **Observed:** Cost shows per-candidate ("Est. cost") + a one-line run total in the verdict
  banner ("Run cost: candidate $0.0085 · judge $0.0000 · total $0.0085"). For the consultant
  billing a client, a clearer per-provider breakdown + cumulative spend across runs would be
  valuable (and is reusable across receipts).
- **Evidence:** ss_07963zcfs (verdict cost line)
- **Recommendation:** A compact cost panel (per-provider tokens + $, run total, optional
  running total across the project) in the inspector or under the leaderboard.
- **Reuse source:** Orionfold AI Native `src/lib/usage/{ledger.ts,pricing-registry.ts}` +
  `src/components/costs/cost-dashboard.tsx` (same multi-provider model); micro-viz
  `src/components/charts/{sparkline,mini-bar,donut-ring}.tsx`.

## Candidates page: inline "add key / start host" affordance for unconfigured providers
- **Severity / Effort:** med / quick-win
- **Route / State:** Candidates · populated (and the no-keys case) · dark
- **Observed:** Candidates is a flat catalog. Configured cloud providers show because their
  keys resolved; if a provider has no key it simply doesn't appear (and a brand-new user sees
  only the two mocks + local stubs). There's no inline path from "I want to prove with Claude"
  → "add your Anthropic key." The activation step (key entry) lives only in Settings.
- **Evidence:** ss_2366nw53x (Candidates catalog — only configured providers present)
- **Recommendation:** List known providers with a quiet "Add key in Settings →" (or inline
  key field) for unconfigured ones, and a "Start Ollama / LM Studio" hint for local. Turns the
  catalog into an activation surface and explains *why* a provider is/isn't available.
- **Reuse source:** Orionfold Arena `arena-app/src/components/arena/OpenRouterKeySettings.jsx`
  (keyless-default + reveal-on-configure pattern).

## First-run quick-start / guided first proof (reduce time-to-first-real-proof)
- **Severity / Effort:** med / deeper
- **Route / State:** Proof Run · empty/first-run · dark
- **Observed:** The cockpit opens straight into a full Configure form. For the ICP's key
  metric (time to first proof run), a brand-new user with keys still has to assemble dataset +
  candidates + scoring themselves. The decision recipes help, but there's no single "run my
  first real proof" guided path.
- **Evidence:** initial Proof Run ss_71473jkfc (full form on first load)
- **Recommendation:** A one-click "Run the demo proof on real models" CTA on first run
  (bundled dataset + 2 cheap cloud candidates + a sensible scoring default that actually
  passes — see the threshold issue), producing a real winner receipt in ~30s. Pairs with the
  blueprint gallery idea above.
- **Reuse source:** Orionfold AI Native `src/lib/workflows/` blueprint instantiation;
  Arena `BuildSpine.jsx` / `flow` stepper for a guided first-run path.
- **HARD DEPENDENCY (sharpened 2026-06-23 by the WS-D1 real-run demo):** the "run my first real
  proof" CTA is actively *harmful* until the flagship demo's scoring produces a clear winner. A
  fresh 3-tier Anthropic run on the bundled summarization set under the now-shipped Similarity
  default (0.55) STILL returned **0% pass / no winner** (avg 0.06–0.15) — and the new cost scatter
  rendered three failing pink dots with no accent. A one-click CTA that lands a first-time user on
  that screen is a worse first impression than the current blank form. **Block WS-E2 (Task 9) on
  the scorer-default fix in `issues.md` → "REAL-RUN: the flagship demo … NO CLEAR WINNER" (default
  the summarization demo to LLM judge, now reachable post-A3).** This is sequencing, not optional
  polish.
