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

## Receipt artifact standards

- **Markdown:** clean headings, leaderboard as a table, failure cases as bullets, no
  app-only UI language.
- **HTML:** self-contained, printable, readable without app CSS, no external tracking,
  includes timestamp + config hash.
- **JSON:** versioned schema, predictable field names, machine-readable, no secrets.

Never put secrets, raw keys, or full provider config in any receipt format.
