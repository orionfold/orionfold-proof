# Receipt Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render the real Proof Receipt artifact in-app (a dedicated detail view) instead of only offering it as a download.

**Architecture:** Add an opt-in `?inline=1` to the existing receipt-download route so the same generated HTML can be served for rendering; embed it in a sandboxed iframe inside a new `ReceiptDetailView`; wire it into the App's state-based navigation so clicking a receipt opens the artifact, with "Explore in cockpit" as the secondary path. No receipt schema change.

**Tech Stack:** Python 3.12 / FastAPI / pytest (backend); Vite / React / TypeScript / Tailwind v4 / Vitest / Playwright (frontend).

**Spec:** `docs/superpowers/specs/2026-06-20-receipt-preview-design.md`

## Global Constraints

- **No receipt schema change:** `RECEIPT_VERSION` stays `3`; `src/orionfold/receipts/export.py` is untouched.
- **Keyless mock default** and **both run endpoints** (`POST /api/runs` batch + `/api/runs/stream`) remain untouched.
- **Test-contract strings must not regress:** heading "Orionfold Proof"; "Connected"; button `/Run proof/`; regions "Leaderboard", "Failure cases", "Proof Receipt export"; "Export Markdown|HTML|JSON"; "100% (5/5)"; "Failure cases (5)"; "simulated provider failure".
- **Tailwind v4 CSS vars use the parenthesis shorthand** `bg-(--color-x)`, never `bg-[--color-x]`.
- **The detail view's download section must NOT reuse the aria-label "Proof Receipt export"** (that belongs to the cockpit's post-run exporter, which stays mounted-but-hidden — reusing it creates a duplicate region).
- **Commit directly to `main`** (solo project; no per-task branches). Do not push.
- **Verify before claiming done:** `uv run pytest`, `pnpm --dir web test`, `pnpm --dir web build`, `pnpm --dir web e2e`.

---

### Task 1: Backend — serve the receipt HTML inline

**Files:**
- Modify: `src/orionfold/server/routes.py:220-238` (`download_receipt`)
- Test: `tests/integration/test_proof_api.py`

**Interfaces:**
- Produces: `GET /api/runs/{run_id}/receipt.{fmt}` now accepts an optional `inline: bool = False` query param. `?inline=1` → `Content-Disposition: inline`; default → `attachment`. Body, media type, and escaping are unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/integration/test_proof_api.py`:

```python
def test_html_receipt_can_be_served_inline_for_preview(client):
    run_id = client.post(
        "/api/runs",
        json={
            "dataset_id": "investment-memo-summarization",
            "candidate_ids": ["mock_good", "mock_bad"],
            "brief": {
                "task_name": "Memo summarization",
                "decision_question": "Which model to trust?",
                "success_criteria": "",
            },
        },
    ).json()["run"]["id"]

    inline = client.get(f"/api/runs/{run_id}/receipt.html?inline=1")
    assert inline.status_code == 200
    assert inline.headers["content-type"].startswith("text/html")
    assert "inline" in inline.headers["content-disposition"]
    assert "attachment" not in inline.headers["content-disposition"]

    # Default stays a download, and the inline body is byte-identical.
    download = client.get(f"/api/runs/{run_id}/receipt.html")
    assert "attachment" in download.headers["content-disposition"]
    assert inline.text == download.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_proof_api.py::test_html_receipt_can_be_served_inline_for_preview -v`
Expected: FAIL — the `inline` param is ignored today, so the response is `attachment` and `assert "inline" in ...` fails.

- [ ] **Step 3: Write minimal implementation**

Replace `download_receipt` in `src/orionfold/server/routes.py` (currently lines 220-238) with:

```python
@router.get("/runs/{run_id}/receipt.{fmt}")
def download_receipt(
    request: Request, run_id: str, fmt: str, inline: bool = False
) -> Response:
    if fmt not in _FORMATS:
        raise HTTPException(status_code=404, detail="Unknown receipt format")
    conn = _conn(request)
    try:
        report = get_report(conn, run_id)
    finally:
        conn.close()
    if report is None:
        raise HTTPException(status_code=404, detail="Unknown run")

    render, media_type = _FORMATS[fmt]
    body = render(report)
    filename = f"proof-receipt-{report.run.config_hash}.{fmt}"
    # inline=1 lets the cockpit render the receipt in an iframe; the default download is unchanged.
    disposition = "inline" if inline else "attachment"
    headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
    if fmt == "html":
        return Response(content=body, media_type=media_type, headers=headers)
    return PlainTextResponse(content=body, media_type=media_type, headers=headers)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_proof_api.py -v && uv run ruff check src/orionfold/server/routes.py && uv run pyright src`
Expected: all PASS (incl. the existing `test_full_loop_...` which still asserts `attachment` by default); ruff clean; pyright 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py
git commit -m "feat(receipts): serve receipt HTML inline for in-app preview"
```

---

### Task 2: Frontend — `ReceiptDetailView` + preview URL helper

**Files:**
- Modify: `web/src/lib/api.ts` (add `receiptPreviewUrl` beside `receiptUrl` at line ~144)
- Create: `web/src/features/proof/ReceiptDetailView.tsx`
- Test: `web/src/features/proof/ReceiptDetailView.test.tsx`

**Interfaces:**
- Consumes: `receiptUrl(runId, fmt)` (existing), `ProofReport` type (existing).
- Produces:
  - `receiptPreviewUrl(runId: string): string` → `"/api/runs/${runId}/receipt.html?inline=1"`.
  - `ReceiptDetailView({ report, onBack, onExplore }: { report: ProofReport; onBack: () => void; onExplore: (report: ProofReport) => void })` — renders an iframe titled `"Proof Receipt preview"` plus three download links and the two nav buttons.

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/ReceiptDetailView.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ReceiptDetailView } from "./ReceiptDetailView";
import { SAMPLE_REPORT } from "../../test/fixtures";

test("renders the receipt artifact in a sandboxed iframe with downloads", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);

  const frame = screen.getByTitle("Proof Receipt preview");
  expect(frame).toHaveAttribute("src", "/api/runs/run_abc123def456/receipt.html?inline=1");
  expect(frame).toHaveAttribute("sandbox");

  for (const label of ["Markdown", "HTML", "JSON"]) {
    expect(screen.getByRole("link", { name: label })).toHaveAttribute(
      "href",
      expect.stringContaining("/api/runs/run_abc123def456/receipt."),
    );
  }
});

test("fires onExplore and onBack from the nav buttons", () => {
  const onBack = vi.fn();
  const onExplore = vi.fn();
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={onBack} onExplore={onExplore} />);

  fireEvent.click(screen.getByRole("button", { name: /Explore in cockpit/ }));
  expect(onExplore).toHaveBeenCalledWith(SAMPLE_REPORT);

  fireEvent.click(screen.getByRole("button", { name: /Receipts/ }));
  expect(onBack).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test ReceiptDetailView`
Expected: FAIL — `ReceiptDetailView` and `receiptPreviewUrl` don't exist yet (module not found).

- [ ] **Step 3: Write minimal implementation**

Add to `web/src/lib/api.ts` directly below the `receiptUrl` function (after line ~146):

```ts
// Same receipt, served for rendering (Content-Disposition: inline) so the cockpit can embed it.
export function receiptPreviewUrl(runId: string): string {
  return `/api/runs/${runId}/receipt.html?inline=1`;
}
```

Create `web/src/features/proof/ReceiptDetailView.tsx`:

```tsx
import { ArrowLeft, Download, ExternalLink } from "lucide-react";

import { receiptPreviewUrl, receiptUrl, type ProofReport } from "../../lib/api";

const FORMATS: { fmt: "md" | "html" | "json"; label: string }[] = [
  { fmt: "md", label: "Markdown" },
  { fmt: "html", label: "HTML" },
  { fmt: "json", label: "JSON" },
];

// The receipt artifact, rendered exactly as it exports. The cockpit shows the interactive run;
// this shows the deliverable a user would hand a client. The iframe is fully sandboxed (no
// scripts, opaque origin) — the HTML is already escaped server-side, so this is defense-in-depth.
export function ReceiptDetailView({
  report,
  onBack,
  onExplore,
}: {
  report: ProofReport;
  onBack: () => void;
  onExplore: (report: ProofReport) => void;
}) {
  const { run } = report;
  const heading = run.brief.decision_question || run.brief.task_name;

  return (
    <main aria-label="Proof Receipt" className="flex flex-col gap-6 px-6 py-8 lg:px-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-sm text-(--color-ink-muted) transition-colors hover:text-(--color-ink)"
        >
          <ArrowLeft aria-hidden className="h-4 w-4 shrink-0" />
          Receipts
        </button>
        <button
          type="button"
          onClick={() => onExplore(report)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-(--color-panel-line) px-3 py-1.5 text-sm text-(--color-ink) transition-colors hover:border-(--color-accent)/50"
        >
          Explore in cockpit
          <ExternalLink aria-hidden className="h-3.5 w-3.5 shrink-0" />
        </button>
      </div>

      <header className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold tracking-tight text-(--color-ink)">{heading}</h2>
        <p className="max-w-prose text-sm text-(--color-ink-muted)">
          The receipt you'd share — rendered exactly as it exports. Config hash{" "}
          <code className="text-(--color-ink)">{run.config_hash}</code>.
        </p>
      </header>

      <iframe
        title="Proof Receipt preview"
        src={receiptPreviewUrl(run.id)}
        sandbox=""
        className="min-h-[60vh] w-full rounded-xl border border-(--color-panel-line) bg-(--color-panel-card)"
      />

      <section className="flex flex-wrap items-center gap-2">
        <span className="flex items-center gap-1 text-xs text-(--color-ink-faint)">
          <Download aria-hidden className="h-3 w-3 shrink-0" />
          Download
        </span>
        {FORMATS.map(({ fmt, label }) => (
          <a
            key={fmt}
            href={receiptUrl(run.id, fmt)}
            download
            className="rounded-md border border-(--color-panel-line) px-2.5 py-1 text-sm text-(--color-ink) transition-colors hover:border-(--color-accent)/50"
          >
            {label}
          </a>
        ))}
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test ReceiptDetailView`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api.ts web/src/features/proof/ReceiptDetailView.tsx web/src/features/proof/ReceiptDetailView.test.tsx
git commit -m "feat(cockpit): ReceiptDetailView renders the receipt artifact in a sandboxed iframe"
```

---

### Task 3: Wire the detail view into navigation

**Files:**
- Modify: `web/src/features/proof/ReceiptsView.tsx` (rename prop `onOpen` → `onOpenReceipt`; update subtitle copy)
- Modify: `web/src/app/App.tsx` (add `receiptInView` state + render branch + import)
- Test: `web/src/features/proof/ReceiptsView.test.tsx`, `web/src/app/App.test.tsx`

**Interfaces:**
- Consumes: `ReceiptDetailView` (Task 2), `openInCockpit` (existing App handler).
- Produces: `ReceiptsView({ onOpenReceipt }: { onOpenReceipt: (report: ProofReport) => void })`. Clicking a receipt card opens the detail view; "Explore in cockpit" routes to the existing cockpit.

- [ ] **Step 1: Write the failing tests**

In `web/src/features/proof/ReceiptsView.test.tsx`, replace every `onOpen` with `onOpenReceipt`:
the three `renderWithQuery(<ReceiptsView onOpen={...} />)` calls become `onOpenReceipt={...}`, and
the second test becomes:

```tsx
test("clicking a run calls onOpenReceipt with that report", async () => {
  mockRuns([SAMPLE_REPORT]);
  const onOpenReceipt = vi.fn();
  renderWithQuery(<ReceiptsView onOpenReceipt={onOpenReceipt} />);

  const heading = await screen.findByText(
    "Which model should I trust for client memo summaries?",
  );
  fireEvent.click(heading.closest("button")!);
  expect(onOpenReceipt).toHaveBeenCalledWith(SAMPLE_REPORT);
});
```

In `web/src/app/App.test.tsx`, replace the `"opens a past run from Receipts back into the cockpit"` test with:

```tsx
test("opens a receipt into its detail view, then explores it in the cockpit", async () => {
  mockServer();
  renderWithQuery(<App />);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: /Run proof/ })).toBeInTheDocument(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Receipts" }));
  const card = await screen.findByRole("button", { name: /Which model should I trust/ });
  fireEvent.click(card);

  // The receipt detail view renders the artifact; the archive list is gone.
  const frame = await screen.findByTitle("Proof Receipt preview");
  expect(frame).toHaveAttribute("src", expect.stringContaining("receipt.html?inline=1"));
  expect(screen.queryByLabelText("Past proof runs")).not.toBeInTheDocument();

  // Explore in cockpit loads the run into the workspace.
  fireEvent.click(screen.getByRole("button", { name: /Explore in cockpit/ }));
  await waitFor(() =>
    expect(screen.getByRole("region", { name: "Leaderboard" })).toBeInTheDocument(),
  );
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pnpm --dir web test ReceiptsView App`
Expected: FAIL — `ReceiptsView` has no `onOpenReceipt` prop yet; App still routes the card to the cockpit (no iframe), so `findByTitle("Proof Receipt preview")` fails.

- [ ] **Step 3: Write minimal implementation**

In `web/src/features/proof/ReceiptsView.tsx`, change the component signature, the subtitle, and the card callback:

```tsx
export function ReceiptsView({ onOpenReceipt }: { onOpenReceipt: (report: ProofReport) => void }) {
  const runs = useQuery({ queryKey: ["runs"], queryFn: getRuns });

  return (
    <ViewShell
      title="Receipts"
      subtitle="Every proof you've run, newest first. Open one to view its receipt and explore it in the cockpit, or download it to share — each carries its config hash and timestamp."
    >
```

and the list item:

```tsx
              <ReceiptCard report={report} onOpen={() => onOpenReceipt(report)} />
```

(Leave `ReceiptCard`'s internal `onOpen` name and the rest of the file unchanged.)

In `web/src/app/App.tsx`:

1. Add the import beside the other feature imports (after line 15):

```tsx
import { ReceiptDetailView } from "../features/proof/ReceiptDetailView";
```

2. Replace the `App()` body (lines 154-179) with:

```tsx
export function App() {
  const [view, setView] = useState<View>("proof");
  // The run shown in the cockpit. Lifted here so a past run can load into the Proof Run workspace.
  const [report, setReport] = useState<ProofReport | null>(null);
  // The receipt being previewed as an artifact (Receipts → detail view). Null = show the archive.
  const [receiptInView, setReceiptInView] = useState<ProofReport | null>(null);

  // Rail navigation always clears the open receipt so Receipts reopens to its list.
  const navigate = (next: View) => {
    setReceiptInView(null);
    setView(next);
  };

  const openInCockpit = (r: ProofReport) => {
    setReceiptInView(null);
    setReport(r);
    setView("proof");
  };

  return (
    <div className="grid min-h-full grid-rows-[auto_1fr] lg:grid-cols-[15rem_minmax(0,1fr)] lg:grid-rows-1">
      <LeftRail view={view} onNavigate={navigate} />
      {/* Proof Run stays mounted (toggled with display, not unmounted) so an in-flight run, the
          brief, and the result survive a side trip to the other views. */}
      <div className={view === "proof" ? "contents" : "hidden"}>
        <ProofCockpit report={report} onReport={setReport} />
      </div>
      {view === "datasets" && <DatasetsView />}
      {view === "candidates" && <CandidatesView />}
      {view === "receipts" &&
        (receiptInView ? (
          <ReceiptDetailView
            report={receiptInView}
            onBack={() => setReceiptInView(null)}
            onExplore={openInCockpit}
          />
        ) : (
          <ReceiptsView onOpenReceipt={setReceiptInView} />
        ))}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test`
Expected: PASS (all suites, including the updated ReceiptsView + App tests). No TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/ReceiptsView.tsx web/src/features/proof/ReceiptsView.test.tsx web/src/app/App.tsx web/src/app/App.test.tsx
git commit -m "feat(cockpit): open a receipt into its artifact view from the archive"
```

---

### Task 4: Playwright — extend the happy path through the receipt view

**Files:**
- Modify: `e2e/playwright/proof.spec.ts` (append a receipt-detail step before the closing `});` at line 34)

**Interfaces:**
- Consumes: the running embedded app (Task 5 rebuilds the embed before this runs).

- [ ] **Step 1: Write the failing step**

In `e2e/playwright/proof.spec.ts`, insert before the final `});` (after line 33):

```tsx
  // The receipt is viewable in-app, not just downloadable: open it from the archive.
  await page.getByRole("button", { name: "Receipts" }).click();
  await page.getByRole("button", { name: /Which model should I trust/ }).first().click();
  await expect(page.getByTitle("Proof Receipt preview")).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore in cockpit/ })).toBeVisible();
  for (const label of ["Markdown", "HTML", "JSON"]) {
    await expect(page.getByRole("link", { name: label, exact: true })).toBeVisible();
  }
```

- [ ] **Step 2: Rebuild the embed and run to verify it fails, then passes**

The e2e runs against the embedded build, so rebuild the cockpit first:

```bash
pnpm --dir web build && rm -rf src/orionfold/server/static && cp -r web/dist src/orionfold/server/static
pnpm --dir web e2e
```

Expected: with the embed rebuilt to include Tasks 1-3, the new step PASSES along with the existing happy path. (If you run e2e against a *stale* embed first, the new step FAILS at `getByTitle("Proof Receipt preview")` — that's the red state confirming the step is real.)

- [ ] **Step 3: Commit**

```bash
git add e2e/playwright/proof.spec.ts
git commit -m "test(e2e): happy path opens the receipt artifact view"
```

---

### Task 5: Full verification, embed rebuild, and docs

**Files:**
- Modify: `docs/worklog/2026-06-20-ui-feature-review.md` (mark #8 done), `HANDOFF.md`
- Build artifact: `src/orionfold/server/static` (gitignored; rebuilt, not committed)

- [ ] **Step 1: Run the full suite**

Run:
```bash
uv run pytest -q && uv run ruff check src/ tests/ && uv run pyright src
pnpm --dir web test && pnpm --dir web build
```
Expected: backend all green (now includes the inline test); ruff clean; pyright 0; Vitest all green; build clean.

- [ ] **Step 2: Rebuild the embedded cockpit and browser-check on a free port**

```bash
pnpm --dir web build && rm -rf src/orionfold/server/static && cp -r web/dist src/orionfold/server/static
```
Then launch on a PROVABLY-FREE port (assert the listener PID's cwd is this checkout, per HANDOFF), open the app, run a mock proof, go to Receipts, click a receipt, and confirm the rendered receipt fills the iframe with "Explore in cockpit" + the three download buttons. Screenshot to `samples/screenshots/receipt-detail.png`.

- [ ] **Step 3: Update the review notes and HANDOFF**

In `docs/worklog/2026-06-20-ui-feature-review.md`, mark finding #8 as **Done (this session)** with the commit hashes. Overwrite `HANDOFF.md` to point at the next thread (e.g. Tier-1 remainder #9 dataset import, or the #5 decision-recipes bet). Append a fresh `docs/worklog/` entry summarizing the receipt-preview build with verification evidence.

- [ ] **Step 4: Commit**

```bash
git add docs/worklog HANDOFF.md
git commit -m "docs: receipt preview shipped — worklog, review notes, handoff"
```

---

## Notes for the implementer

- **Why the iframe `sandbox=""` is safe and sufficient:** `export.to_html()` already `html.escape`s every dynamic value, so the document can't carry injected markup. `sandbox=""` (no `allow-scripts`, no `allow-same-origin`) additionally disables JS and isolates the document as an opaque origin — its CSS can't leak into the app and vice-versa. Do **not** add `allow-scripts` or `allow-same-origin`.
- **Why `inline` (not a separate route or `srcdoc`):** one renderer, one route; the frontend just sets `src`; the backend concern is independently testable. Reading the same bytes — `Content-Disposition` only changes the browser's download-vs-render decision.
- **uvicorn does not hot-reload** backend code; restart the server after Task 1 before any manual check. The cockpit is served from the gitignored `src/orionfold/server/static`, so rebuild+embed (Task 4/5) before e2e or a browser check.
