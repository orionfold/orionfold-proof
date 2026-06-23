# 2026-06-22 — ICP-persona end-to-end visual verification (real models)

## Summary

Walked **Orionfold Proof** through the browser (Claude in Chrome) as its ICP — an AI
consultant producing a client proof, then a small product team running a quick A/B — using
**real models, Sandbox OFF** (operator directive; cost not a concern). Keys present in
`.env.local`: Anthropic, OpenAI, OpenRouter. Logged 16 findings into a new top-level
`_IDEAS/` folder (issues · feature-opportunities · design-system + README index). No product
code changed — verification + idea-capture only.

## Verification (evidence)

- App up via live source: API `uv run orionfold dev --port 8790` (health
  `{"status":"ok","service":"orionfold-proof"}`), UI `VITE_DEV_PORT=5174
  VITE_API_PROXY=http://127.0.0.1:8790 pnpm --dir web dev` (`:5174`). Both still running.
- **Sandbox OFF** confirmed in Settings; real vendor candidates (Anthropic claude-haiku-4-5,
  OpenAI gpt-5.4-nano, OpenRouter meta-llama/llama-3.1-8b-instruct) present; mocks hidden from
  the run picker.
- **Pass 1 (consultant):** imported a real pasted dataset ("Support ticket triage v1", 5 ex,
  Exact-match hint) → preview "5 examples parsed" → froze; configured cross-vendor trio; ran
  **two real scored matrix runs** (15 live API calls each) — streaming progress, leaderboard,
  failure-case browser with real outputs; exported receipts MD/HTML/JSON.
- **Pass 2 (product team):** Quick ⚡ A/B (Haiku 4.5 vs GPT-5.4 nano, release-notes prompt) →
  objective bars → picked GPT-5.4 nano → Save as Proof Receipt → verified archive reads
  "Picked OpenAI · gpt-5.4-nano" + in-app receipt detail view.
- **Secret hygiene PASS:** programmatic scan of every exported receipt (md/html/json) and all
  `_IDEAS/*.md` — **no keys/tokens**. 16 runs persisted in `~/.orionfold/proof.db`.
- Swept all 5 routes (Proof Run · Datasets · Candidates · Receipts · Settings) in **dark +
  light**; theme restored to Dark; compared leaderboard/table/badge vs the 2026-06-20 design
  reference. Light theme clean (no FOUC, good contrast).

## Findings (16) → `_IDEAS/`

- **Issues (6):** 3× high — real-model first proof is steered to "NO CLEAR WINNER":
  classification fails for lack of a per-task instruction; flagship summarization fails the
  too-strict 0.80 Similarity default; LLM-judge unavailable to a cloud-only user (picker
  excludes cloud providers, defaults to Mock even with Sandbox OFF). Plus stale decision
  question (config + frozen into a saved Quick receipt) and the check-hint↔scoring taxonomy
  mismatch.
- **Features (5):** per-task instruction/prompt template (HIGH, **quick-win** — `system_prompt`
  is already wired through engine/providers/receipt; UI-only); Pareto cost-vs-quality frontier
  (reuse Arena `FrontierScatter.jsx`); run-level cost ledger (reuse ainative `lib/usage/*` +
  `cost-dashboard.tsx`); Candidates inline add-key affordance; guided first-run.
- **Design-system (5):** dataset metadata inconsistency (bundled vs user); leaderboard not
  sortable + sans (not mono micro-caps) headers vs reference `.tbl`; Mock boundary badge not
  visually distinct from Local/Cloud; inspector column empty on list/settings pages.

## Product impact

The single highest-leverage thread: a cloud ICP's **first real proof currently reads as a
discouraging "no winner."** The fixes are well-scoped and partly already plumbed (the
prompt-template `system_prompt` path exists end-to-end). Landing that UI plus a threshold/judge
default recalibration would convert the out-of-box real-model experience into a clear,
trustworthy proof — directly serving "decide what AI to trust."

## Risks

- Findings are logged, not fixed. The 3 high issues affect the first-impression real-model
  path and should be triaged before any "real models" demo.
- 16 ad-hoc runs (incl. several "no winner") now sit in the local DB; optional cleanup via
  Settings → data management if a clean demo state is wanted.

## Next recommended step

Triage the 3 high issues together (they're one story). Start with feature #1 (per-task
instruction UI — quick-win, plumbing exists) + recalibrating the demo's default scoring so the
bundled dataset yields a clear winner on real models. **Brainstorm scope first** per CLAUDE.md.
