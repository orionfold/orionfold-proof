# Worklog — 2026-06-21 · Scoring-section design polish (operator live review)

## Summary

An operator-led, in-browser review of last release's **Scoring method** section. The operator
gave feedback live while watching the app (HMR loop); each change was applied and re-verified in
the browser. **Frontend-only — no backend, scoring, or receipt change.**

Three changes:

1. **Method cards in one row.** The four scoring methods (Auto / Keypoint / Similarity / LLM
   judge) now sit in a single responsive row (`lg:grid-cols-4`, 2×2 on narrow). Previously the
   LLM judge sat alone under a separate "Costs money · adds latency" header. `MethodCard` became
   `flex h-full flex-col` with the cost chip pinned to the bottom (`mt-auto`), so every card is
   equal width **and** height and the cost chips align. Guidance copy was reworded to ~52 chars
   each and given `text-balance`, so each card wraps to two even lines.
   - The two uppercase group headers were replaced by a single helper line. The free-vs-paid
     guard (the original reason for the split) now lives in each card's cost chip: `Free` vs
     `$ per run · slower`. *(Flagged this tradeoff to the operator; they accepted it.)*

2. **Judge filter is now a single-row stepper.** When LLM judge is selected, the
   Run on / Optimize / Judge model controls used to stack vertically. They now form one
   horizontal stepper that **matches the top `StageStepper`** (Configure · Run · Decide):
   - ①②③ filled-accent number badges (same `h-4 w-4` circle as the top stepper).
   - `h-px w-5 bg-(--color-panel-line)` hairline connectors — **not arrow icons** (the operator
     asked for consistency with the top stepper after first seeing an arrow version).
   - Labels, connector lines, and controls all inline on one row (`flex flex-wrap items-center`),
     hidden connectors once the row wraps.
   - Added `aria-label="Judge model"` to the `<select>`: the redesign dropped the `<label>`
     wrapper, which had been providing the accessible name (and the e2e `getByLabel` hook).
   - Reworded the gated hint to "Pick one once its key is set below." — the old "Add a key…"
     copy duplicated the KeyEntry's `/add a key/` text and made a unit test match two nodes.

3. **`vite.config.ts` dev isolation.** The dev `port` and `/api` proxy target are now
   env-overridable (`VITE_DEV_PORT` / `VITE_API_PROXY`) with the original values as defaults, so
   a second checkout can run on free ports without colliding with the sibling
   `orionfold-proof-codex` servers (8787 / 5173). This review ran on 5180 → 8790.

## Verification

- `pnpm --dir web test --run` → **72/72** unit tests pass.
- `pnpm --dir web build` (`tsc --noEmit && vite build`) → clean.
- `bash scripts/build.sh` (rebuild embed) → `pnpm --dir web e2e` → **5/5** Playwright pass
  (LLM-judge-filter spec exercises the new stepper: Run on / Local / Hosted / Judge model /
  Mock judge default).
- Browser-verified each state live in Chrome on isolated ports (frontend 5180 → backend 8790,
  throwaway review DB). Zoomed screenshots confirmed equal card heights, aligned cost chips, and
  the stepper badges/lines matching the top stepper.

## Product impact

The scoring step reads as one calm, scannable instrument: four comparable method cards, then —
only when a paid judge is chosen — a numbered left-to-right stepper that visually encodes the real
data dependency (Run on → Optimize → Judge model narrows each next choice). Consistent with the
page's top stepper, so the cockpit feels like one designed surface rather than assembled parts.

## Risks

- The free-vs-paid **structural** separation (two labeled sections) is gone; the guard is now
  per-card cost text only. If accidental paid runs ever show up, reconsider emphasizing the LLM
  judge card (a divider or subtle treatment — the palette has no warn token by design).

## Next recommended step

Resume **#6 Prompt-variant candidates** (same model, different system prompt, one run). Creative
work → brainstorm first, then spec → plan → subagent-driven. See HANDOFF.
