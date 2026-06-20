# Design — In-app Proof Receipt preview (review finding #8)

- **Status:** Approved (operator-approved 2026-06-20, brainstorming pass)
- **Date:** 2026-06-20
- **Related:** `docs/worklog/2026-06-20-ui-feature-review.md` (finding #8),
  `docs/release-charter.md`, `.claude/rules/receipts.md`,
  `docs/adr/0001-local-first-proof-receipt-architecture.md`

## Problem & goal

The Proof Receipt is the product's central deliverable ("get a repeatable receipt showing what
is worth trusting"), yet the cockpit can only **download** it (`Markdown / HTML / JSON`) — the
formatted artifact is never **rendered in-app**. A user can't see what they'll hand a client
without leaving the app and opening a file. Today the Receipts archive card's primary click
reopens the run in the interactive cockpit (leaderboard/failures), which is *exploring the run*,
not *seeing the deliverable*.

**Goal:** render the real, generated receipt artifact inside the app, byte-for-byte identical to
the downloaded HTML — without duplicating the receipt's layout.

## Decision (settled in brainstorming)

1. **Dedicated Receipt detail view (artifact-first).** Clicking a receipt in the archive opens a
   full-pane view that renders the receipt; a secondary **Explore in cockpit** action reaches the
   existing interactive leaderboard/failures. (Chosen over a modal or inline-expand.)
2. **Render the real HTML via an inline endpoint + sandboxed iframe** — not a React re-render from
   JSON (which would risk drifting from the actual file and violate `receipts.md`'s "protect the
   artifact"). Chosen over `fetch`+`srcdoc` because it keeps the frontend trivial, gives a clean
   server-serves / client-embeds test split, extends the existing "receipt is a GET-able resource"
   pattern, and yields a reusable URL (open-in-tab / print later).
3. **Archive-entry only for this slice.** A post-run "View receipt" link in the cockpit is
   **deferred** (cheap, but needs a callback threaded App → cockpit; keep the slice thin).
4. **No receipt schema change.** `RECEIPT_VERSION` stays `3`; `export.to_html/_markdown/_json` are
   unchanged. This is a serving + surfacing change only.

## Backend change (small)

`GET /api/runs/{run_id}/receipt.{fmt}` (`src/orionfold/server/routes.py`, `download_receipt`)
currently always sets `Content-Disposition: attachment` (forces download). Add an opt-in query
param so the **same** `export.to_html()` body can be served for rendering:

```python
def download_receipt(request: Request, run_id: str, fmt: str, inline: bool = False) -> Response:
    ...
    disposition = "inline" if inline else "attachment"
    headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
```

- Default (no param) is unchanged: `attachment` (download).
- `?inline=1` → `inline` disposition; the browser renders the document. Only the `html` format is
  used inline; the flag is format-agnostic but harmless for `md`/`json`.
- Body, media type, escaping, and the secret-free guarantees are untouched.
- **Security (defense-in-depth).** The HTML response also carries `Content-Security-Policy:
  sandbox` and `X-Content-Type-Options: nosniff`. The inline endpoint is directly navigable (a
  top-level tab is **not** covered by the iframe sandbox), so the server sandboxes the document
  itself — no script execution, opaque origin, no MIME sniffing — regardless of how it's loaded.
  Three independent layers protect the same-origin XSS surface: output escaping (`html.escape`
  in `export.to_html`) · server `CSP: sandbox` · the iframe `sandbox=""`. (Flagged by automated
  security review; see `docs/worklog/2026-06-20-ui-feature-review.md`.)

## Frontend changes

**`web/src/lib/api.ts`** — add a tiny helper beside `receiptUrl` (keep `receiptUrl`'s signature
stable so existing callers/tests don't churn):

```ts
export function receiptPreviewUrl(runId: string): string {
  return `/api/runs/${runId}/receipt.html?inline=1`;
}
```

**`web/src/features/proof/ReceiptDetailView.tsx`** (new) — props `{ report, onBack, onExplore }`:

- Built on the existing `ViewShell` chrome. Header: **`‹ Receipts`** back link, the decision-
  question title (`run.brief.decision_question || run.brief.task_name`), and **`Explore in
  cockpit`** (secondary, calls `onExplore`).
- Body: a **sandboxed iframe** rendering the artifact —
  `<iframe src={receiptPreviewUrl(run.id)} sandbox="" title="Proof Receipt preview" />` — filling
  the content pane, scrolling internally. `sandbox=""` (no `allow-scripts`/`allow-same-origin`)
  makes the framed document an inert, opaque-origin island: no script execution, no style leakage
  either direction. (The content is already fully `html.escape`d server-side; the sandbox is
  defense-in-depth.) An `onLoad`-driven "Loading receipt…" notice covers the brief load.
- Toolbar: the three **Download** buttons (MD · HTML · JSON), reusing `receiptUrl` — same anchors
  as the archive card.

**`web/src/features/proof/ReceiptsView.tsx`** — the card's primary click now opens the detail view
instead of the cockpit: rename its `onOpen` prop to **`onOpenReceipt`** and update the subtitle
copy ("Open one to view its receipt; explore it in the cockpit, or download it to share — each
carries its config hash and timestamp."). The card keeps its quick Download buttons.

**`web/src/app/App.tsx`** — extend the state-based navigation (consistent with today; no router):

- Add `const [receiptInView, setReceiptInView] = useState<ProofReport | null>(null)`.
- `openReceipt(r)` → `setReceiptInView(r)` (passed to `ReceiptsView` as `onOpenReceipt`).
- A `navigate(v)` wrapper used by the rail clears `receiptInView` then `setView(v)`, so Receipts
  always opens to the list.
- Render: when `view === "receipts"`, show `receiptInView ? <ReceiptDetailView report=…
  onBack={() => setReceiptInView(null)} onExplore={openInCockpit} /> : <ReceiptsView
  onOpenReceipt={openReceipt} />`.
- `openInCockpit` is unchanged (loads the run into the always-mounted Proof Run workspace);
  invoking it from the detail view's **Explore in cockpit** also leaves `receiptInView` cleared on
  next Receipts visit via `navigate`.

## Data flow

Receipts archive (`getRuns`) → click a card → `openReceipt(report)` sets `receiptInView` →
`ReceiptDetailView` mounts an iframe whose `src` GETs `/api/runs/{id}/receipt.html?inline=1` →
FastAPI renders `export.to_html(report)` inline → browser paints the artifact inside the sandbox.
Download buttons hit the same route without `inline` (attachment). **Explore in cockpit** →
`openInCockpit(report)` → Proof Run workspace. **‹ Receipts** → clears `receiptInView` → list.

## Testing & non-regression

- **Backend (pytest):** `?inline=1` → `200`, `text/html`, `Content-Disposition: inline`, body
  identical to `export.to_html(report)`; default (no param) still `attachment`. Add beside the
  existing receipt-download tests.
- **Frontend (Vitest):** `ReceiptDetailView` renders the iframe with the correct `src`, `title`,
  and `sandbox=""`; renders three download links with correct `href`s; **Explore in cockpit** calls
  `onExplore`; **‹ Receipts** calls `onBack`. `ReceiptsView` card click calls `onOpenReceipt`.
  `App` integration: clicking a receipt shows the detail view (heading + iframe); back returns to
  the list. Update `ReceiptsView.test.tsx` and `App.test.tsx`.
- **Playwright (e2e):** extend the happy path — after a run, open Receipts → click a receipt →
  assert the detail heading, the iframe element, and the three download buttons. (Do not assert
  cross-document iframe *contents*.)
- **Non-regression / contract:** `RECEIPT_VERSION` stays `3`; `export.py` untouched; the cockpit's
  post-run `ReceiptExport` (carrying "Export Markdown/HTML/JSON") is untouched; mock-default,
  keyless path and both run endpoints are untouched. Tailwind v4 CSS vars use the
  `bg-(--color-x)` parenthesis shorthand.

## Out of scope / deferred

- Post-run "View receipt" link in the cockpit export section (fast-follow).
- A tabbed multi-format viewer (rendered HTML | raw Markdown | raw JSON) — downloads suffice now.
- URL routing / deep links / SPA fallback (review finding #10) — separate decision.
- Any change to receipt content, schema, or the other review findings (#1, #2, #4–#7, #9).

## Files touched

- `src/orionfold/server/routes.py` — `inline` param on `download_receipt` (+ test).
- `web/src/lib/api.ts` — `receiptPreviewUrl`.
- `web/src/features/proof/ReceiptDetailView.tsx` (new) + `.test.tsx` (new).
- `web/src/features/proof/ReceiptsView.tsx` — `onOpenReceipt`, copy.
- `web/src/app/App.tsx` — `receiptInView` wiring.
- `web/src/features/proof/ReceiptsView.test.tsx`, `web/src/app/App.test.tsx` — updates.
- `e2e/playwright/proof.spec.ts` — receipt-detail step in the happy path.
