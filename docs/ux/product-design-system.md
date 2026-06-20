# Product Design System

> A calm instrument panel for proving AI work, not a noisy dashboard for watching AI theater.
> Surface metaphor: a lab bench plus a signed receipt.

This is the canonical visual and interaction language. Keep it lean; extend it
deliberately. Avoid one-off styles — run a design-system cleanup every two weeks.

## Design adjectives

Precise · calm · confident · technical-but-humane · premium · readable · private ·
evidence-first · quietly distinctive.

**Anti-patterns:** generic SaaS cards everywhere, purple-gradient AI cliché, noisy
dashboards, confetti, giant hero copy inside the app, terminal-only roughness, fake
"autonomous agent" theatrics, decorative icons that do not aid scanning.

## Layout

```text
Left rail:    Projects · Proof Runs · Datasets · Candidates · Receipts · Settings   (quiet)
Main workspace: the current task — create, run, compare, inspect, export.           (clearest weight)
Right inspector: context, metadata, config, selected failure case, receipt summary. (secondary)
```

Rules: one primary CTA per view. No nested sidebars. No card mosaics. Main workspace
always wins the eye.

## Core UX objects (do not invent new nouns lightly)

Project · Proof Brief · Dataset · Candidate · Proof Run · Leaderboard · Failure Case ·
Proof Receipt. If a feature cannot attach to one of these, reconsider it.

## Information hierarchy (every results view)

1. Decision → 2. Winner / recommendation → 3. Evidence summary → 4. Leaderboard →
5. Failure cases → 6. Raw run details → 7. Export / repro metadata.

The user must understand the outcome without reading raw logs.

## States

Every interactive view must implement: **empty · loading · error · populated.** Empty
states answer: what is this, why it matters, what to do next, can I try a sample.

## Visual tokens (starting point — refine during the UI slice)

- **Type:** one humanist sans for UI; a monospace for hashes, IDs, and config. Generous
  line height; high readability over density.
- **Color:** restrained neutral base; a single confident accent for the primary action
  and the "winner" highlight. Reserve semantic color for status only (pass / warn / fail).
  No gradient AI clichés.
- **Density:** roomy but information-dense where it earns it (the leaderboard table).
- **Motion:** minimal and functional; no decorative animation.
- **Provider boundary:** Local / Cloud / Mock must be visually distinct at a glance.

## Theming

**Three-state model:** `System / Light / Dark`. Default is **System** (follows
`prefers-color-scheme`). An explicit Light or Dark choice overrides and persists to
`localStorage["orionfold-theme"]` (values: `system`, `light`, `dark`).

**Mechanism:** The dark palette is the `@theme` base in `web/src/styles/index.css`.
Light overrides live in a sibling `:root[data-theme="light"]` block (specificity 0,2,0)
that reliably beats `@theme`'s `:root` (0,1,0). A `@custom-variant dark ([data-theme="dark"] &)`
lets badge classes carry light-legible base values with `dark:` restoring dark variants.
`System` always resolves to a concrete `data-theme` of `light` or `dark` on `<html>` before
the app reads it, so `[data-theme="dark"]` covers System-dark transparently. A tiny
inline `<script>` in `<head>` applies the token before the bundle loads — no FOUC.

**Light palette (starting values; AA-measured at the visual gate):**

| Token | Dark | Light | Notes |
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

The Proof Receipt is also themed: standalone HTML follows the reader's OS via
`@media (prefers-color-scheme)` (dark fallback); the in-app iframe preview receives an
explicit `?theme=<resolved>` param which injects `data-theme` and wins by specificity.

## Receipt artifact standards

- **Markdown:** clean headings, leaderboard as a table, failure cases as bullets, no
  app-only UI language.
- **HTML:** self-contained, printable, readable without app CSS, no external tracking,
  includes timestamp + config hash.
- **JSON:** versioned schema, predictable field names, machine-readable, no secrets.

Never put secrets, raw keys, or full provider config in any receipt format.
