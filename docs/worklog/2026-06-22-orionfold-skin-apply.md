# Worklog — 2026-06-22 — Orionfold design-system skin apply (cyan/green split)

## Summary
Applied the Orionfold visual system (DS `36d1c48`, change package
`orionfold-design-system/apply/proof/change/2026-06-21-234241`) to the `web/` cockpit. Headline:
the single green `--color-accent` (`#34d399`) → Orionfold **cyan** `#14c8c0` (the one interactive
colour), with a **new status-green `--color-ok`** carrying PASS/verified. Plus Geist + Geist Mono
typography, a Linear radius/finish, token-driven status badges, and a skip-to-content link.

Web-only; no backend/Python changes, no receipt-schema change, no `RECEIPT_VERSION` bump (still 6).
All prompt-aware-mocks / #6 / standing invariants untouched.

## What changed (file by file)
- `web/src/styles/index.css` — dropped-in `tokens.orionfold.css` (`@theme` + light override): cyan
  accent, new `--color-ok`/`-warn`/`-danger`/`-accent-soft`/`-ok-soft`, cyan focus, radius tokens,
  `--font-sans`/`--font-mono`; body→`var(--font-sans)`, `code`/`.mono`→`var(--font-mono)`; breathe
  glow recoloured cyan. Dark stays the `@theme` default.
- `web/index.html` — Geist + Geist Mono Google-Fonts links.
- `web/src/app/App.tsx` — "Connected" dot `--color-accent`→`--color-ok` (the core status split);
  unreachable dot rose→`--color-danger`; added the skip-to-content link (first focusable, cyan chip);
  **brand mark** swapped from a plain cyan square placeholder to the real Orionfold **delta-star**
  (cyan disc + white star, path from the DS brand sprite) + "Orion`fold` Proof" wordmark with a cyan
  `fold` (`aria-label` pins the accessible name to "Orionfold Proof"). Added during operator review.
- `web/src/features/proof/ProofCockpit.tsx` — `id="main-content"` + `tabIndex=-1` on the workspace
  `<main>`; `tabular-nums` on verdict metrics; error copy → `--color-danger`.
- `web/src/features/proof/badges.tsx` — de-literalled: provider tags neutral + de-pilled
  (receipt-stub); `StatusBadge` error→`--color-danger`, fail→`--color-warn`; no cyan.
- `web/src/features/proof/badges.test.tsx` — assertions updated from old literal classes to the new
  token contract.
- `web/src/features/proof/formStyles.ts` (new) — shared `inputCls`; `RunSetup.tsx` +
  `PromptVariants.tsx` now import it.
- rose-300→`--color-danger` sweep: `DatasetImportPanel`, `RunSetup`, `KeyEntry`, `Inspector`,
  `ProofCockpit`, `ViewShell`.

## Verification
- `pnpm --dir web test` → **84/84** · `tsc --noEmit` clean · `pnpm --dir web build` clean.
- `bash scripts/build.sh` rebuilt the embed (Geist links + cyan/green tokens confirmed in
  `src/orionfold/server/static`); `pnpm --dir web e2e` → **6/6**.
- Real-browser visual grade in **both themes** (temporary Playwright screenshot spec, since removed):
  verdict = the one full-cyan surface; leaderboard recommended cyan + **neutral squared provider
  tags**; failures = amber `Fail · score` (warn) and red `error:` (danger); engine dot **green**,
  distinct from cyan; skip link reveals as a cyan chip on focus (`toBeFocused()` asserted). AA legible
  on both the dark canvas and light paper.

## Product impact
The accent/status split is now load-bearing in code: cyan = action, green = passed. A PASS/verified
state and the Run button can no longer share a hue, and `badges.tsx` is no longer a literal-colour
island — status is token-driven everywhere. No change to the proof artifact itself.

## Write-back
`orionfold-design-system/apply/proof/aligned/2026-06-22-021521-log.md` (applied/pushback/skipped) and
`…/roadmap/2026-06-22-021521-log.md` (seed verdicts + our DS-informed ideas).

## Risks
- Geist loads from Google Fonts at runtime; offline/blocked networks fall back to the system sans
  stack (tokens already list fallbacks) — acceptable, non-blocking.
- One deliberate deviation from the package prose: `StatusBadge fail` → `--color-warn` (not danger),
  to preserve the product's error-vs-graded-miss severity distinction (logged under Pushback; aligns
  with the component-map's two-token failure-case treatment).

## Next recommended step
Optional polish from the roadmap log: cyan `m-fill` score bars in the leaderboard (effort S) and a
shared token-driven badge/chip kit folding the toggle/radio selected states. Otherwise resume the
non-blocking v0 backlog from HANDOFF (catalog price/source pass; cross-product models×prompts —
brainstorm first; git remote + push).
