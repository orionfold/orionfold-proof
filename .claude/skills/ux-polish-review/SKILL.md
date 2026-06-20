---
name: ux-polish-review
description: Use when a route is functionally complete, the UI feels generic, or the operator asks for polish. Inspects the route in the browser, runs the UX quality gate, lists top issues, fixes scoped ones, and re-verifies.
---

# UX polish review

Target feel: **a calm instrument panel for proving AI work, not a noisy dashboard for
watching AI theater.** Precise, calm, confident, premium, evidence-first.

## Steps

1. Open the route in the browser (use `browser-visual-verification`).
2. Run the UX quality gate against `docs/ux/usability-checklist.md` and
   `docs/ux/product-design-system.md`:
   - Information hierarchy: Decision → winner/recommendation → evidence → leaderboard →
     failure cases → raw details → repro metadata.
   - One primary CTA per view; main workspace has the clearest visual weight; right
     inspector secondary; left rail quiet.
   - All four states present: empty, loading, error, populated.
   - Empty states answer: what is this, why it matters, what to do next, can I try a sample.
   - Copy matches `docs/ux/copy-deck.md` nouns and labels.
3. List the top issues, worst-first.
4. Fix scoped, clearly-visible issues only — do not redesign.
5. Re-verify in the browser and confirm WCAG 2.2 AA contrast and a working keyboard path.

## Avoid

Generic SaaS cards everywhere, purple-gradient AI cliché, noisy dashboards, confetti,
fake "autonomous agent" theatrics, decorative icons that do not aid scanning.
