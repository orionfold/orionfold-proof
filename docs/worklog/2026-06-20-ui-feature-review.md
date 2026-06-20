# 2026-06-20 — UI / feature review pass (operator-guided)

> Live punch-list captured while the operator clicks through the app at
> `http://localhost:8799` (fresh build, temp DB). Newest findings appended under each screen.
> Severity: **P0** blocker · **P1** should-fix · **P2** polish · **idea** future.

## How this session ran
- App: `orionfold-proof-claude` rebuilt + embedded, `orionfold up` on port 8799, fresh temp DB.
- Operator drives the browser; Claude observes (screenshots / read_page) and records feedback.

## Findings

| # | Screen | Severity | Finding | Suggested fix |
|---|--------|----------|---------|---------------|
| 1 | Global / rail | P1 (feature) | No light theme; dark-only. Want a light design system + theme switcher in the bottom Settings area. | Add a `light` token set in `index.css` `@theme`, a `data-theme`/class toggle persisted to localStorage, and a switcher in the rail footer (where "Settings · soon" sits). Audit all `--color-*` for both themes. |
| 2 | Rail footer | P1 (bug) | Settings + Connected (engine status) scroll away on a long page — should be sticky/pinned above the fold. | Make the rail a fixed-height flex column with the footer `mt-auto` and the rail itself `sticky`/full-height, so footer stays pinned regardless of main-pane scroll. |
| 3 | Datasets | Q → answer | "When do we add more datasets? Are user-defined datasets in scope post-v0?" | User import (JSONL/CSV/Markdown/paste) is **already v0 scope** (charter must-have); more *bundled* samples are a trivial content add. Verify live that import works end-to-end. |
| 4 | Candidates | idea (design) | What's the most user-friendly way to offer more per-provider model choices? | Hybrid: a small curated "recommended models" dropdown per provider (latest marked) + a free-text "custom model" escape hatch; searchable list for OpenRouter. Avoid one giant stale hardcoded list. |
| 5 | Candidates | idea (strategic) | Why not default each provider to its SOTA model? Or pick defaults by another criterion (comparable tier, same family across OpenRouter/Ollama/LM Studio)? "Most critical feature; room for innovation." | Reframe: ship **named comparison presets** ("decision recipes") that auto-select a *coherent panel* (cost↔quality frontier, local vs cloud, latest vs incumbent, same weights across providers), not one "best" default. Current cheap defaults are intentional (model = subject under test; keeps first-click cheap). Merge with #7. |
| 6 | Candidates | Q → roadmap | When do Candidates expand beyond models — prompts, workflows? | Prompt-variant candidates (same model, different system prompt) are the natural **next** axis (still text-in/text-out, no new provider machinery). Workflows/RAG are explicit post-v0 ("doc ingestion + minimal RAG" is first-after-v0). |
| 7 | Proof Run | P2 (feature) | Offer suggested decision-question cards / options + a default, instead of a blank-ish field. | 3–4 starter question cards that seed both the question and the product's mental model; pairs with the #5 presets (a preset bundles question + panel). A default is already pre-filled. |
| 8 | Receipts | P1 (gap) | The Proof Receipt — the product's key deliverable — isn't previewable/rendered in-app; only exported. | Render the generated **HTML receipt inline** in a Receipt detail view (we already produce HTML) alongside the export buttons. Likely the single highest-value next build. Verify current Receipts view behavior live. |

## Findings discovered while grounding #3 / #8 (live)
| # | Screen | Severity | Finding | Suggested fix |
|---|--------|----------|---------|---------------|
| 9 | Datasets | P1 (gap) | **No dataset-import affordance in the cockpit.** The Datasets view is read-only (lists the one bundled set + expandable Examples). Charter makes import (JSONL/CSV/Markdown/paste) a **v0 must-have** — so this is a v0 acceptance gap *in the UI* (import may exist via CLI/API; confirm). Corrects my first answer to #3. | Add a "New dataset / Import" entry on the Datasets view: paste box + file picker (JSONL/CSV/MD), preview parsed input/expected pairs, freeze. Reuse whatever import the backend already has. |
| 10 | Global routing | P2 | Rail is **state-based, not URL-routed**: clicking Datasets/Receipts keeps the URL at `/`; visiting `/datasets` directly returns a server `{"detail":"Not Found"}` (no SPA fallback). No shareable/deep-linkable views; a refresh always lands on Proof Run. | Decide intent: if deep links are wanted, add a client router + a FastAPI catch-all that serves `index.html` for non-`/api` paths. If not, fine for v0 — just note it. |
| 8 | Receipts | P1 (confirmed) | Verified live: receipts are a **list + Download (MD/HTML/JSON)**; "Open" reopens the run in the cockpit (interactive leaderboard/failure views) — but the **formatted receipt artifact itself is never rendered in-app**. The deliverable can only be judged by downloading it. | Add a Receipt detail view that renders the generated **HTML receipt inline** (iframe/sandbo­xed) with the export buttons beside it. Highest-value next build. |

## Decisions / deferrals
_(to fill in)_

## Synthesis — the big idea (from #5 + #7 + #4)
The most leveraged direction: **"Decision recipes" / comparison presets.** Instead of choosing one
default model, the product ships opinionated, named comparison templates that map to real questions
a consultant asks — each preset auto-selects a *coherent candidate panel* + a starter decision
question (+ optionally a dataset). Examples: _Cost vs quality for client summaries_ · _Local vs
cloud (privacy)_ · _Cheapest model that still passes_ · _Same weights, different providers
(provider arbitrage: llama3.x on Ollama vs OpenRouter vs LM Studio)_. This turns "pick models" (a
blank-canvas chore) into "pick the decision you're making" — which is the product's whole thesis.

## Next steps
_(to fill in at the end — prioritized backlog)_
