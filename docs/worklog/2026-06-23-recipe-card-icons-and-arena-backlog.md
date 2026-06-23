# 2026-06-23 · Recipe-card icons + compact layout, and B3–B5 Arena-grounded backlog

Browser-use watch session (operator drove the live cockpit; I observed, made one small UI
change, and logged three brainstorm-first backlog items grounded in the Arena source).

## Summary

**Setup.** `localhost:8787` (Orionfold's target port) was occupied by an *unrelated* project —
`/Users/manavsehgal/orionfold/self-wealth` running its own `dashboard/scripts/server.py` (PID
80825). Non-destructive sidestep: launched Orionfold Proof on **`--port 8799`** (`uv run orionfold
dev --port 8799`) rather than killing another project's server. Cockpit verified live and correct
(the Proof Run / Configure screen, not the wealth app).

**Shipped — decision-recipe cards (`web/src/features/proof/RecipeRow.tsx`, FE-only).** Three
operator asks, iterated in-browser:
1. **Icons.** Per-recipe lucide icon keyed by **stable `recipe.id`** (`cost-vs-quality`→Scale,
   `local-vs-cloud`→Server, `cheapest-that-passes`→Tag, `provider-arbitrage`→Shuffle), `Sparkles`
   fallback for any future recipe. Accent-tinted (`--color-accent`) when the card is selected,
   neutral (`--color-ink-muted`) at rest. Differentiate by **shape, not color** — color stays
   reserved for state, honoring the DS token contract (cyan=action, no per-category palette).
2. **Compact layout.** Card went from a 4-row vertical stack to a media-object: icon inline with
   the title; subtitle + model-count below. `p-4`→`p-3`. Model count became a **rounded pill**;
   "N need a key" a separate **warn-tinted pill** (status-vs-accent split per WS-F).
3. **Alignment.** Equal-height cards (`items-stretch`) with pills **bottom-aligned** (`mt-auto`),
   and subtitle + pills **left-aligned flush with the icon** (vertical stack, only icon+title share
   the top row). Side benefit: the wider subtitle column unwrapped "Cost vs quality" to one line, so
   all four cards equalized in height.
   - Operator confirmed "leave as is" on the question of per-recipe brand colors (DS contract
     forbids a categorical palette; would mint new non-functional accents).

**Logged — three brainstorm-first backlog items (`_IDEAS/backlog.md`, no code).** Each grounded in
the real Arena source the operator pointed at (`/Users/manavsehgal/Developer/ainative-business.github.io`):
- **B3** · real-world demo datasets mined from the `~/orionfold/` sibling projects (privacy
  synthesize-vs-import fork; scoring-fit per demo-scorer-default).
- **B4** · reimagine the "Candidates" screen (today a low-value read-only mirror of run setup) as a
  **cross-run models leaderboard**, repurposing Arena's LMArena-style board. Captured the real
  column schema (`LiveLeaderboard.jsx` + `leaderboard-format.mjs`: model · source badge · bench ·
  quality% · tok/s · TTFT · preference% · cost · cost/quality), grouped-per-test + medals + live
  refresh, the publishable score-only safe-slice (`mirror.py` + `test_mirror_does_not_leak.py`), and
  the `fmt` correctness qualifier. Naming gripe ("Candidates"→"Models"?) noted with the
  prompt-candidate caveat.
- **B5** · make Quick Compare more whole, mining Arena's **CompareDuel** (~1300 lines vs Proof's
  147): live streaming duel, any-vs-any lane selection, rich per-side cards, **inline optional
  scoring** (which may *supersede* the B2 promote seam), separated 👍/👍/Tie preference vote (feeds
  B4's `Preference %`), head-to-head metric cards, eval-against-gold mode. Hard guardrail recorded:
  **"Quick stays QUICK."**

**Cross-cutting finding:** the `fmt` "format check — not correctness" qualifier (Arena AF-27)
surfaced on **three** independent surfaces (B4 leaderboard, B5 compare verdict, Proof's own
demo-scorer-default work) — a candidate for a shared Proof-wide convention.

## Verification

- `tsc --noEmit` → exit 0 (clean); the transient `CostLedger`/Playwright LSP diagnostics were
  editor-server noise, not compiler errors (confirmed by stash + re-run + explicit exit code).
- `vitest run RecipeRow` → 5/5 pass at every iteration.
- Vite build + re-embed into the gitignored `src/orionfold/server/static` after each change (the
  cockpit serves a pre-built bundle; source edits need the re-embed to show on 8799).
- **Browser-verified (`browser-visual-verification`)**, light theme, zoom-graded: icons render with
  correct glyphs/semantics; pills bottom-aligned across all four cards; subtitle+pills left-aligned
  with the icon; selected-state cyan accent (border + bg + icon) intact after each restructure.
- Studied Arena source directly (read `CompareDuel.jsx`, `LiveLeaderboard.jsx`,
  `leaderboard-format.mjs`) + the public product page — backlog items grounded, not guessed.

## Product impact

- Decision recipes are more scannable and take less vertical space — calmer Configure screen,
  on the "calm instrument panel" north star.
- B3–B5 give the next product-direction passes concrete, source-anchored starting points (the
  "Candidates" screen and Quick Compare are the two weakest spots for our ICP today).

## Risks

- None shipped. The recipe-card change is FE-only, no backend/migration/`config_hash` touch; mock
  matrix untouched.
- B4/B5 carry the real product risk (cross-run comparability = honest proof vs. vanity metric;
  "Quick stays quick") — both fenced as brainstorm-first, no code until an operator-approved spec.

## Commits

- `9a092da` — feat(proof): recipe-card icons + compact left-aligned layout
- `26e7c89` — docs(backlog): B3–B5 (datasets, candidates→leaderboard, quick-compare)

Also updated the `charting-library-recharts` memory note with the Arena leaderboard-source pointer
(lives in `~/.claude/`, outside the repo).

## Next recommended step

Point queue is still empty (deferred backlog only). When a product-direction pass earns priority,
**B4 (candidates→leaderboard) and B5 (quick-compare) should be specced together** — they overlap
B2 (the promote seam) and share the preference→leaderboard signal. Run a `brainstorming` pass →
one `_SPECS/` workstream resolving the B2/B4/B5 relationship → operator approval before code.
Packaging·licensing·distribution remains the other deferred track (brainstorm first; git
remote+push stay queued LAST).
