# Design — Light theme + theme switcher (review finding #1)

- **Date:** 2026-06-20
- **Status:** Approved (operator, 2026-06-20)
- **Source:** `docs/worklog/2026-06-20-ui-feature-review.md` finding #1 (P1 feature).
- **Scope owner:** the cockpit (`web/`) plus the receipt export (`src/orionfold/`).

## Problem

The cockpit ships dark-only. The operator wants a calm **light** design system and a
**theme switcher**, honoring the "calm instrument panel / lab bench + signed receipt"
aesthetic in both themes. The Proof Receipt — the product's key artifact — must read well
in light too, including when downloaded and opened standalone.

## Decisions (locked with operator)

1. **Three-state model:** `System / Light / Dark`. Default = **System** (follow
   `prefers-color-scheme`); an explicit Light or Dark choice overrides and **persists**.
2. **Receipt is themed too** (not just the cockpit chrome).
3. **Standalone downloaded receipt follows the reader's OS** via `@media
   (prefers-color-scheme)`, dark as fallback — fully self-contained, no app state baked in.
   The **in-app iframe preview matches the cockpit's resolved theme** via an explicit
   override.
4. The disabled **"Settings · soon" rail marker is replaced** by the live theme switcher
   (Settings is otherwise still out of scope).
5. **`receipt_version` stays 3** — this is a presentation-only change; the structured data
   (JSON/MD content) and `config_hash` (computed over run inputs, not styling) are
   unchanged.

## Architecture — theming mechanism (hybrid, idiomatic Tailwind v4)

The UI gets its color two ways; the theme system covers both:

1. **Design tokens (the bulk).** Today's `@theme` block in `web/src/styles/index.css`
   stays as the **dark base**. Add a sibling override block:

   ```css
   :root[data-theme="light"] {
     --color-panel: …;  /* every token from @theme, light values */
     …
   }
   ```

   Specificity: `@theme` emits to `:root` (0,1,0); `:root[data-theme="light"]` is (0,2,0)
   and reliably wins. Every `bg-(--color-x)` / `text-(--color-x)` utility re-resolves with
   no class changes.

2. **Literal color utilities (the few).** `badges.tsx` uses hardcoded Tailwind colors
   (`zinc/slate/sky/rose/amber`) tuned for dark. Register a custom dark variant so these can
   carry both forms:

   ```css
   @custom-variant dark ([data-theme="dark"] &);
   ```

   Then base classes = light-legible, `dark:` = today's values (see §Badges).

**"System" is always resolved to a concrete `data-theme`** of `light` or `dark` on
`<html>` before the app reads it, so `[data-theme="dark"]` covers System-dark transparently.

## Components

### 1. Theme state — `web/src/lib/theme.ts` (+ a `useTheme` hook)

- **Choice** persisted to `localStorage["orionfold-theme"]` ∈ `{system, light, dark}`
  (default `system` when unset/invalid).
- **Resolve** to `light|dark`: if choice is `system`, read
  `matchMedia("(prefers-color-scheme: dark)")`; else the choice itself.
- **Apply** by setting `document.documentElement.dataset.theme = resolved`.
- **Subscribe** to the media query while choice is `system`; re-apply on OS flip.
- Hook returns `{ choice, resolved, setChoice }`. One module = one responsibility (theme
  resolution + persistence); the switcher and the receipt iframe both consume it.

### 2. No-flash pre-paint script — `web/index.html`

A tiny inline `<script>` in `<head>`, before the module bundle, that reads the stored choice
and sets `documentElement.dataset.theme` synchronously (resolving `system` via `matchMedia`).
Prevents a dark→light flash on load. Kept minimal and dependency-free; the React `useTheme`
hook re-attaches listeners after hydration but does not re-flash.

### 3. Switcher UI — in `web/src/app/App.tsx` `LeftRail` footer

Replaces the `Settings · soon` `<span>`. A compact 3-segment **radiogroup**
(`role="radiogroup"`, each segment `role="radio"` + `aria-checked`, arrow-key navigable,
visible focus ring from the existing `:focus-visible` rule):

```
◐ System    ☀ Light    ☾ Dark
```

Icons: lucide `MonitorCog`/`Monitor`, `Sun`, `Moon`. Active segment uses the existing raised
`--color-panel-card` treatment. Calls `setChoice` on select. The engine-status pill stays
below it; both stay pinned (footer is already sticky as of `030b9db`).

### 4. Light palette — `web/src/styles/index.css`

Intent: **paper, not glare.** App background a soft cool-gray; **cards become white**
(raised surface lifts off the gray bg — the inverse of the dark relationship); ink a soft
near-black (not pure `#000`). The single emerald accent **deepens** so accent-as-text and
the filled CTA pass **WCAG 2.2 AA** on white. Provider/status hues get darker light-mode
variants. Starting values (implementation measures and tunes each to ≥ AA):

| Token | Dark (current) | Light (proposed) | Notes |
|---|---|---|---|
| `--color-panel` | `#0b0f14` | `#f4f6f8` | app background (soft gray) |
| `--color-rail` | `#0c1016` | `#eceff3` | quietest plane (recessed) |
| `--color-inspector` | `#0e131a` | `#f0f2f5` | secondary plane |
| `--color-panel-card` | `#161b22` | `#ffffff` | raised: cards, inputs (white) |
| `--color-panel-line` | `#232b36` | `#dde3ea` | hairline border |
| `--color-panel-line-strong` | `#313c4a` | `#c3ccd6` | emphasized border |
| `--color-ink` | `#e6edf3` | `#1b2430` | primary text |
| `--color-ink-muted` | `#9fb0c0` | `#51616f` | secondary text (≥ AA) |
| `--color-ink-faint` | `#7c8b9b` | `#67768a` | hints (≥ AA on gray bg) |
| `--color-accent` | `#34d399` | `#047857` | accent-as-text/icon (legible on white) |
| `--color-accent-strong` | `#10b981` | `#047857` | filled CTA (white ink ≥ AA) |
| `--color-accent-ink` | `#022c22` | `#ffffff` | text on filled accent |
| `--color-focus` | `#5eead4` | `#0d9488` | focus ring (visible on light) |

The `breathe` keyframe's `rgba(52,211,153,…)` accent glow is acceptable on both themes
(subtle, emerald) — left as-is, re-checked visually.

### 5. Badges — `web/src/features/proof/badges.tsx`

`PROVIDER_STYLE` and `STATUS_STYLE` each gain light-legible base classes with `dark:`
restoring the current dark values, e.g.:

```
mock:  "border-zinc-400/40 bg-zinc-400/10 text-zinc-600 dark:border-zinc-500/40 dark:bg-zinc-500/10 dark:text-zinc-300"
```

(local→slate, cloud→sky, error→rose, fail→amber follow the same pattern; light text uses the
600/700 step.) The `text-[11px]` / icon structure is unchanged.

### 6. Receipt export — `src/orionfold/receipts/export.py`

The HTML `<style>` block swaps hardcoded hexes for CSS custom properties:

```css
:root { --rc-bg: #0b0f14; --rc-ink: …; … }                 /* dark default */
@media (prefers-color-scheme: light) {
  :root { --rc-bg: #f4f6f8; … }                            /* standalone → reader OS */
}
:root[data-theme="light"] { --rc-bg: #f4f6f8; … }          /* explicit override (iframe) */
:root[data-theme="dark"]  { --rc-bg: #0b0f14; … }
```

Rules: `:root[data-theme]` (0,2,0) beats the `@media` `:root` (0,1,0), so the explicit
override always wins in the iframe; standalone files (no `data-theme`) fall to the media
query. Markdown and JSON exports are untouched. Sample receipts regenerated via
`scripts/gen_samples.py`.

### 7. Inline serve — `src/orionfold/server/routes.py`

The inline receipt endpoint (already takes `request`, `inline`) gains an optional
`theme: str | None` query param (`light|dark`, ignored otherwise). When present **and**
`inline`, inject `data-theme="<theme>"` onto the receipt's `<html>` element. Downloads
(`attachment`, no `theme`) are byte-identical to today's structure plus the new self-adapting
CSS — so a shared file is stable and `config_hash` unchanged.

`web/src/features/proof/ReceiptDetailView.tsx` appends `&theme=${resolved}` (from `useTheme`)
to the iframe `src`.

### 8. Docs — `docs/ux/product-design-system.md`

Add the light palette table + the theming mechanism (token override + `@custom-variant`,
`data-theme`, System resolution) so the design system documents both themes.

## Data flow

```
localStorage[orionfold-theme] ──► useTheme ──► <html data-theme="light|dark">
        ▲                              │                   │
   switcher.setChoice                  │             every var(--color-*) utility
   (rail footer)                       └──► ReceiptDetailView ─► iframe ?theme=resolved
                                                                  │
matchMedia(prefers-color-scheme) ──(when choice=system)──────────┘
standalone receipt.html ──► @media(prefers-color-scheme) (no app involved)
```

## Testing

- **Vitest:** `useTheme` — default `system`; persists an explicit choice; resolves via a
  mocked `matchMedia`; sets `data-theme`; re-resolves on OS change while `system`. Switcher —
  renders 3 segments, selecting persists + updates `aria-checked`. Badges — both light/dark
  class forms present.
- **pytest:** receipt HTML contains the dark `:root` defaults, the `@media
  (prefers-color-scheme: light)` block, and the `:root[data-theme]` overrides; the inline
  endpoint with `theme=light` injects `data-theme="light"`; the download path does not;
  `config_hash` identical with and without `theme`. Existing receipt-content assertions hold.
- **Playwright e2e:** toggle to Light → `html[data-theme="light"]`; reload → persists; open a
  receipt → iframe `src` carries `theme=light`. Rebuild embed first.
- **browser-visual-verification + ux-polish-review gate:** render Proof Run, leaderboard,
  Datasets, and a receipt in **light**; screenshot each; confirm WCAG 2.2 AA for ink, muted
  ink, accent-as-text, CTA, and badges; confirm no FOUC on reload.

## Non-goals / YAGNI

- No per-component theme overrides, no theme beyond light/dark, no user-customizable palettes.
- Settings remains otherwise out of scope — only the theme switcher lands there.
- No receipt **schema** change; MD/JSON exports unchanged.
- The `breathe` keyframe color is not tokenized (single subtle accent glow, fine in both).

## Risks

- **Contrast regressions in light.** Mitigate: AA measured per token at build; ux-polish gate.
- **FOUC.** Mitigate: pre-paint inline script sets `data-theme` before the bundle loads.
- **Receipt iframe/standalone divergence.** Mitigate: explicit `[data-theme]` override beats
  the media query by specificity; pytest asserts both paths.
- **Sample-receipt drift.** Mitigate: regenerate via `scripts/gen_samples.py`; CI/tests cover
  receipt content.
