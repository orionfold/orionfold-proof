# 2026-06-20 — In-app Proof Receipt preview (review finding #8)

## Summary
The Proof Receipt — the product's central deliverable — was download-only; you couldn't *see* what
you'd hand a client without leaving the app. Now a **dedicated, artifact-first Receipt detail
view** renders the real generated HTML in-app. This came out of an operator-guided UI/feature
review (10 findings, in `2026-06-20-ui-feature-review.md`); #8 was chosen as highest value-to-effort
and taken brainstorm → spec → plan → subagent-driven execution with per-task and final reviews.

### What shipped
- **Backend** (`server/routes.py`): an opt-in `?inline=1` on `GET /api/runs/{id}/receipt.{fmt}`
  serves the same `export.to_html()` body with `Content-Disposition: inline` (default stays
  `attachment`). The HTML response also carries `Content-Security-Policy: sandbox` and
  `X-Content-Type-Options: nosniff`. No receipt schema change (`RECEIPT_VERSION` still 3).
- **Frontend**: `ReceiptDetailView` renders the receipt in a `sandbox=""` iframe via
  `receiptPreviewUrl`; clicking a receipt card opens it; **Explore in cockpit** is the secondary
  path to the interactive leaderboard/failures. Wired through `App` state (`receiptInView`),
  consistent with the existing state-based navigation — the detail view and the archive list are
  mutually exclusive (both use `<main>`); rail nav and `openInCockpit` clear `receiptInView`.
- **Security — three independent layers** (recorded in the design spec, prompted by an automated
  security review mid-build): output escaping (`html.escape` in `export.to_html`) · server
  `CSP: sandbox` (covers the directly-navigable URL, which the iframe sandbox can't) · the iframe
  `sandbox=""` (no `allow-scripts`/`allow-same-origin`).

New: `ReceiptDetailView.tsx` (+ test), `receiptPreviewUrl`, design spec + plan under
`docs/superpowers/`. Touched: `routes.py`, `App.tsx`, `ReceiptsView.tsx`, the e2e happy path,
fixtures (added a `: ProofReport` annotation).

## Verification
- **Backend:** `uv run pytest` → **73 passed** (+4: inline disposition, sandbox headers on inline,
  sandbox headers on the default download, body byte-identity). ruff clean; pyright 0.
- **Frontend:** `pnpm --dir web test` → **12 passed** (+`ReceiptDetailView` 2; App/ReceiptsView flow
  updated to card → detail → Explore → cockpit). `pnpm --dir web build` (tsc + vite) clean.
- **e2e:** `pnpm --dir web e2e` → **1 passed** — the happy path now opens the receipt artifact view
  (asserts the sandboxed iframe + Explore + the three downloads) against a freshly-rebuilt embed.
- **Reviews:** per-task spec+quality gates all PASS; **final whole-branch review: ready to merge**
  (no Critical/Important; the four logged minors were non-issues or low-value deferrals — e.g.
  measured ink-faint contrast 5.51:1, above AA). The one finding with defensive value (assert the
  sandbox headers on the default download too) was folded in (`7b3a09c`).
- **Browser:** Playwright is the browser evidence (renders the iframe end-to-end). A manual
  screenshot was blocked by the Chrome extension's per-origin permission gate; available on request
  if `localhost` is re-allowed.

Commits (on `main`, not pushed): `780daee` · `50e4dfb` · `4214a03` · `725362c` · `4e8417b` ·
`1d8ea18` · `7b3a09c`.

## Product impact
The product now *shows its own deliverable*. A user can read the exact receipt they'd share with a
client without downloading a file, while the cockpit remains the place to explore the run
interactively — two clean mental models ("see the deliverable" vs "explore the run"). The
serving + sandbox approach means the preview can never drift from the downloaded artifact.

## Risks / follow-ups
- Deferred by design: the post-run "View receipt" link in the cockpit, a tabbed MD/JSON viewer,
  URL routing/deep links (#10), and the `onLoad` loading affordance (unnecessary on a local
  instant serve). All recorded in the spec's out-of-scope list.
- The remaining review findings are the backlog (see `2026-06-20-ui-feature-review.md` §Next steps).

## Next recommended step
Operator review of the shipped preview, then pick the next thread: the cheap **#2 sticky footer**,
the Tier-1 **#9 dataset import**, or the strategic **#5 decision recipes** (its own brainstorm).
