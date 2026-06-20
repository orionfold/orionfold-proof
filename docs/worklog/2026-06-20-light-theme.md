# 2026-06-20 — Light theme + theme switcher (review finding #1)

> The strategic-but-sizable backlog item from the operator review: a calm **light** design
> system and a **System / Light / Dark** switcher, extended to the exported Proof Receipt.
> Built brainstorm → spec → plan → subagent-driven execution (7 TDD tasks, per-task reviews,
> a final Opus whole-branch review). Committed to `main` (not pushed).

## Summary

A three-state theme (default **System**) for the cockpit and the receipt:

- **Mechanism (Tailwind v4, idiomatic).** Dark stays the `@theme` base; a
  `:root[data-theme="light"]` block overrides the 13 `--color-*` tokens (specificity (0,2,0)
  beats `@theme`'s `:root`), so every `bg-(--color-x)` utility re-resolves with no class
  churn. A `@custom-variant dark ([data-theme="dark"] &)` gives the literal-color badges a
  light base + `dark:` override. (`a46b5e3`, `85245d8`, `411dbdd`)
- **State + no-flash.** `web/src/lib/theme.ts` (`useTheme`) persists the choice to
  `localStorage["orionfold-theme"]`, resolves "System" via `matchMedia` and tracks live OS
  changes, and applies `<html data-theme="light|dark">`. A pre-paint inline script in
  `index.html` applies it before first paint. (`a46b5e3`)
- **Switcher.** A `radiogroup` (System/Light/Dark) in the rail footer **replacing** the
  disabled "Settings · soon" marker. (`1a7193c`)
- **Themed receipt.** `export.py` swaps hardcoded hexes for CSS variables: a dark `:root`
  default, an `@media (prefers-color-scheme: light)` block (standalone downloads follow the
  reader's OS), and explicit `:root[data-theme]` overrides (the in-app iframe is pinned to the
  cockpit theme, beating the media query by specificity). `receipt_version` stays **3**
  (presentation-only); `config_hash` untouched. The route validates the reflected `theme` to
  `{light,dark}` at the boundary. (`989fd3a`, `c0dca53`, `acba2b3`)

## Verification (evidence, not claims)

- **pytest 95**, **vitest 26** (8 files), **`pnpm build`** clean, **Playwright e2e 3/3**
  (incl. a new theme toggle+persist spec, run against the rebuilt embed).
- **Real-browser visual/AA gate** (controller): measured every light token. All cleared WCAG
  2.2 AA after darkening `ink-faint` `#67768a → #5f6e80` (panel 4.81 / rail 4.52 / card 5.21,
  still visibly quieter than `ink-muted`); badges 4.65–7.13; accent-as-text 4.90; CTA/ink/muted
  comfortable. Dark theme verified unregressed. Receipt iframe served `<html data-theme="light">`
  with content. No FOUC.
- **Security:** an automated review flagged the reflected `theme` param; hardened at the route
  boundary (normalize to `None` unless light/dark — behavior-preserving, no 400) with a
  regression test that a `"><script>` payload is never pinned or reflected. Defense-in-depth:
  `to_html` keeps its own allowlist; body is `html.escape`d; CSP `sandbox` + `nosniff`; iframe
  `sandbox=""`.

## Process notes / what the reviews caught

- **Task 6 (per-task review):** the backend `data-theme="light"` assertion was a **false green**
  — the string also appears in the `:root[data-theme="light"]` CSS selector, so it passed even
  if the `<html>`-tag injection were reverted. Fixed by scoping to `split("<head>")[0]`.
- **Final whole-branch review (Opus):** caught a real **controller miss** — my `ink-faint` AA
  fix used `replace_all` on a string whose indentation matched only the `@media` light branch
  (6 spaces), not the `:root[data-theme="light"]` branch (4 spaces), so the **iframe** receipt
  still rendered the rejected `#67768a` (4.27:1). Fixed in `0a67af4`, plus value-parity test
  assertions (`count("--rc-case-key: #5f6e80") == 2`) so a single-branch drift now fails loudly.
  Re-review: **Ready to merge: Yes.**

## Product impact

The cockpit now meets users where they are (light or dark, following their OS by default), and
the product's key deliverable — the Proof Receipt — reads correctly in both, whether previewed
in-app or shared as a standalone file. A calm instrument panel in either polarity.

## Risks

- None blocking. Commits on `main` are **not pushed** (today's backlog plus the earlier
  dataset-import work remain unpushed).
- Accepted non-blocking Minors (final review agreed): switcher has no roving-tabindex (ARIA
  radiogroup + Tab/Space works); `setChoice` not memoized / `useTheme` doesn't `applyTheme` on
  mount (pre-paint covers it); mock/local light badge backgrounds are near-identical (text/border
  steps + icons disambiguate).

## Next recommended step

Operator's call on the remaining backlog (priority had **#5 decision recipes** next): named
comparison presets bundling a candidate panel + starter decision question — **needs its own
brainstorm** before any plan. Lower: #6 prompt-variant candidates, #10 URL routing. A push of the
accumulated `main` commits is also pending whenever the operator wants it.
