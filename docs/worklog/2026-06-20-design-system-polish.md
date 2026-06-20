# 2026-06-20 — Design-system polish pass (cockpit → three-pane)

## Summary
Brought the cockpit from functional Gate-5 scaffolding (a single centered card) to the
documented **three-pane instrument panel** in `docs/ux/product-design-system.md`. Frontend-only
— **no backend, endpoint, noun, or receipt-schema change**. Operator decisions this pass
(via `AskUserQuestion`): **structural shell only** (no new backend nouns) and **keep emerald as
the single accent with separated semantic/provider roles**.

- **Three-pane shell.** `App.tsx` now renders a quiet **left rail** (brand wordmark + nav map:
  Proof Run active, Datasets/Candidates/Receipts marked _soon_, Settings + engine-status pill at
  the foot) and a content area; `ProofCockpit.tsx` splits that area into the **main workspace**
  and the **right inspector**. Reflows to a single stacked column below `lg`.
- **Right inspector** (`Inspector.tsx`, new): run config (dataset, rubric, candidates with
  provider tags, **config hash in monospace**, timestamp), the Proof Receipt export controls, and
  the **selected failure case** detail (input/expected/output). Failure selection is lifted into
  `ProofCockpit` so clicking a row in the workspace populates the inspector.
- **Decision → winner band** atop results (information hierarchy items 1–3): the decision
  question, then the recommended candidate in an accent-tinted card with an evidence one-liner
  (pass rate · avg score · latency · est. cost).
- **Token system** (`index.css`): three surface planes (panel/rail/inspector), a single
  `--color-accent` (emerald) reserved for **CTA + winner only**, a shared `--color-focus` ring,
  monospace for hashes/IDs, and a `prefers-reduced-motion` guard. Status (pass/warn/fail) and
  provider boundary (local=slate / cloud=sky / mock=zinc) moved to their own restrained colors via
  a new shared `badges.tsx` (`ProviderTag`, `StatusTag`) so green stops meaning four things.
- **Result panes retokened** (`RunSetup`, `Leaderboard`, `FailureCases`, `ReceiptExport`):
  provider chips, status by **text + color** (never color alone), accent-only winner highlight.
  All accessible names / region labels / button + link text the tests assert were preserved.

### Notable fix — Tailwind v4 bracket-var bug (pre-existing, latent)
The codebase used `bg-[--color-x]` / `text-[--color-x]`. **Tailwind v4 does not wrap that in
`var()`** — it emits `background-color:--color-x`, an invalid declaration the browser drops, so
every custom-token color silently never applied (the UI coasted on the body bg/color + built-in
palette classes). v4's CSS-variable shorthand is the **parenthesis** form `bg-(--color-x)`.
Converted all **95** occurrences across 7 files `[--color-*]` → `(--color-*)`; verified the built
CSS now emits `var(--color-*)` and **zero** bare/unwrapped refs. This is why the accent button and
pane surfaces were invisible on the first browser pass and correct after.

## Verification
- **Tests (all green):** `uv run pytest` → **65 passed**; `ruff check .` clean; `uv run pyright
  src` → **0 errors**; `pnpm --dir web test` → **3 passed**; `pnpm --dir web build` (tsc + vite)
  clean; `pnpm --dir web e2e` → **1 passed** (full happy path against the embedded build, with the
  new UI).
- **Browser visual verification** (Playwright MCP against `orionfold up` on a provably-free port,
  embedded build, temp DB; listener PID asserted ours):
  - _Empty_ — three panes render; rail/main/inspector distinct; keyless mocks pre-selected.
    `samples/screenshots/design-system-empty.png`.
  - _Populated_ — decision→winner band, leaderboard (Mock·good Recommended, 100% 5/5), failure
    list with the surfaced `RuntimeError: mock_bad: simulated provider failure`.
    `samples/screenshots/design-system-populated.png`.
  - _Failure selection_ — clicking a row populates the inspector detail.
    `samples/screenshots/design-system-inspector.png`.
  - _Narrow (400px)_ — reflows to one stacked column; leaderboard table scrolls horizontally
    rather than breaking layout.
  - _Focus_ — teal `:focus-visible` ring confirmed on the first control; tab order logical; Run
    proof reachable by keyboard.
- **WCAG AA contrast fix:** `--color-ink-faint` was ~4.49:1 on the panel (a hair under AA 4.5);
  lifted #6b7c8c → #7c8b9b (~5.5:1) and dropped the `/70` opacity on the _soon_ label.
- _Loading_ and _error_ engine states are implemented as `CenteredNotice` text notices (logic
  unchanged from prior verified gates; compile-checked) — not separately screenshotted because
  they are transient/hard to force without route interception. Stated plainly rather than faked.

## Product impact
The cockpit now reads as the charter's "calm instrument panel": the decision and recommended
winner lead, the leaderboard and failure cases sit in the main workspace, and repro metadata +
the takeaway receipt live quietly in the inspector. The latent token bug is fixed, so the design
system's surfaces and muted-text hierarchy actually apply for the first time.

## Risks / follow-ups
- Button copy is `Run proof` / `Rerun proof` (lowercase p) to honor the vitest/e2e contract;
  `copy-deck.md` shows `Run Proof`. Cosmetic; left as-is to avoid breaking tests.
- Left rail items Datasets/Candidates/Receipts are _soon_ markers (operator chose structural shell
  only). Wiring them to real views is a deliberate later step, not a regression.
- ADR-0003 (progress-based streaming timeout) still owed — out of scope this pass.
- Screenshots saved under `samples/screenshots/` are **uncommitted** along with the code (this
  project commits to `main` only when the operator asks).

## Next recommended step
Operator review of the three-pane cockpit (screenshots above). On approval, commit to `main`.
Then ADR-0003 (progress-based timeout) or wiring the deferred rail destinations, operator's call.
