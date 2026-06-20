# Light theme + theme switcher — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-state (System / Light / Dark) theme to the cockpit and the Proof Receipt, with a switcher in the rail footer, persisted and flash-free.

**Architecture:** Hybrid Tailwind v4 theming — override the `--color-*` design tokens under `:root[data-theme="light"]` (dark stays the `@theme` base), and register `@custom-variant dark` for the handful of literal-color badge utilities. "System" is resolved to a concrete `data-theme` on `<html>` by a pre-paint script + a `useTheme` hook. The receipt carries both palettes as CSS variables (standalone follows the reader's OS via `@media (prefers-color-scheme)`; the in-app iframe is forced to the cockpit theme via a server-injected `data-theme`).

**Tech Stack:** Vite + React 19 + TypeScript + Tailwind v4 (cockpit); FastAPI + Python 3.12 (receipt/routes). Vitest + Playwright + pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-20-light-theme-design.md`. Decisions: three-state default **System**; receipt themed; standalone download follows reader OS; the disabled "Settings · soon" marker is **replaced** by the switcher; **`receipt_version` stays 3** (presentation-only).
- localStorage key is exactly `orionfold-theme`; values `system | light | dark` (default `system`).
- `<html>` carries `data-theme="light" | "dark"` (always a concrete value, never `system`).
- Tailwind v4: CSS vars use the PARENTHESIS shorthand `bg-(--color-x)`, never `bg-[--color-x]`. Filled-accent button = `bg-(--color-accent-strong)` + `text-(--color-accent-ink)`; inputs use `bg-(--color-panel-card)`.
- Do NOT regress test-contract strings or the receipt's structured content/`config_hash`. Light hex values below are starting points — tune any that miss **WCAG 2.2 AA** during the Task 8 visual gate.
- Commit after each task. Solo project: commit directly to `main`.
- The receipt preview iframe is `sandbox=""` (no JS) — receipt theming must be pure CSS.

---

### Task 1: Theme module + hook, pre-paint script, matchMedia test shim

**Files:**
- Create: `web/src/lib/theme.ts`
- Create: `web/src/lib/theme.test.ts`
- Modify: `web/index.html` (add pre-paint `<script>` in `<head>`)
- Modify: `web/src/setupTests.ts` (add a `window.matchMedia` shim)

**Interfaces:**
- Produces: `type ThemeChoice = "system" | "light" | "dark"`; `type ResolvedTheme = "light" | "dark"`; `getStoredChoice(): ThemeChoice`; `resolveTheme(choice: ThemeChoice): ResolvedTheme`; `applyTheme(resolved: ResolvedTheme): void`; `useTheme(): { choice: ThemeChoice; resolved: ResolvedTheme; setChoice: (c: ThemeChoice) => void }`.

- [ ] **Step 1: Add a `matchMedia` shim so jsdom can render components that read it**

In `web/src/setupTests.ts`, append:

```ts
// jsdom has no matchMedia; the theme system queries prefers-color-scheme. Default to "not dark"
// (light) so components render deterministically; individual tests override as needed.
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}
```

- [ ] **Step 2: Write the failing test**

Create `web/src/lib/theme.test.ts`:

```ts
import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { getStoredChoice, resolveTheme, useTheme } from "./theme";

afterEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  vi.restoreAllMocks();
});

function mockPrefersDark(dark: boolean) {
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        matches: dark,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList,
  );
}

test("defaults to system when nothing is stored", () => {
  expect(getStoredChoice()).toBe("system");
});

test("reads a stored explicit choice", () => {
  localStorage.setItem("orionfold-theme", "light");
  expect(getStoredChoice()).toBe("light");
});

test("resolves an explicit choice without consulting the OS", () => {
  expect(resolveTheme("light")).toBe("light");
  expect(resolveTheme("dark")).toBe("dark");
});

test("resolves system from prefers-color-scheme", () => {
  mockPrefersDark(true);
  expect(resolveTheme("system")).toBe("dark");
  mockPrefersDark(false);
  expect(resolveTheme("system")).toBe("light");
});

test("useTheme persists a choice and applies data-theme", () => {
  mockPrefersDark(true);
  const { result } = renderHook(() => useTheme());
  act(() => result.current.setChoice("light"));
  expect(localStorage.getItem("orionfold-theme")).toBe("light");
  expect(result.current.resolved).toBe("light");
  expect(document.documentElement.dataset.theme).toBe("light");
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd web && pnpm exec vitest run src/lib/theme.test.ts`
Expected: FAIL — cannot resolve `./theme`.

- [ ] **Step 4: Implement the theme module**

Create `web/src/lib/theme.ts`:

```ts
import { useEffect, useState } from "react";

export type ThemeChoice = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

const KEY = "orionfold-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

export function getStoredChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch {
    /* localStorage unavailable — fall through to default */
  }
  return "system";
}

export function resolveTheme(choice: ThemeChoice): ResolvedTheme {
  if (choice === "light" || choice === "dark") return choice;
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

export function applyTheme(resolved: ResolvedTheme): void {
  document.documentElement.dataset.theme = resolved;
}

// One hook owns the choice, its resolved value, and live OS-change tracking while on "system".
export function useTheme(): {
  choice: ThemeChoice;
  resolved: ResolvedTheme;
  setChoice: (c: ThemeChoice) => void;
} {
  const [choice, setChoiceState] = useState<ThemeChoice>(getStoredChoice);
  const [resolved, setResolved] = useState<ResolvedTheme>(() => resolveTheme(getStoredChoice()));

  const setChoice = (next: ThemeChoice) => {
    try {
      localStorage.setItem(KEY, next);
    } catch {
      /* ignore persistence failure */
    }
    setChoiceState(next);
    const r = resolveTheme(next);
    setResolved(r);
    applyTheme(r);
  };

  useEffect(() => {
    if (choice !== "system") return;
    const mq = window.matchMedia(DARK_QUERY);
    const onChange = () => {
      const r: ResolvedTheme = mq.matches ? "dark" : "light";
      setResolved(r);
      applyTheme(r);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [choice]);

  return { choice, resolved, setChoice };
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd web && pnpm exec vitest run src/lib/theme.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 6: Add the pre-paint script (no FOUC)**

In `web/index.html`, inside `<head>` immediately after the `<title>` line, add:

```html
    <script>
      // Apply the persisted theme before first paint so there is no dark→light flash.
      // Mirrors web/src/lib/theme.ts (key + resolution); the React hook re-attaches listeners.
      (function () {
        try {
          var c = localStorage.getItem("orionfold-theme") || "system";
          var dark =
            c === "dark" ||
            (c === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
          document.documentElement.dataset.theme = dark ? "dark" : "light";
        } catch (e) {
          document.documentElement.dataset.theme = "dark";
        }
      })();
    </script>
```

- [ ] **Step 7: Run the full frontend suite + build**

Run: `cd web && pnpm test && pnpm build`
Expected: all green; build succeeds.

- [ ] **Step 8: Commit**

```bash
git add web/src/lib/theme.ts web/src/lib/theme.test.ts web/index.html web/src/setupTests.ts
git commit -m "feat(cockpit): theme module, useTheme hook, pre-paint script"
```

---

### Task 2: Light palette tokens + dark custom variant (index.css)

**Files:**
- Modify: `web/src/styles/index.css`

**Interfaces:**
- Produces: a `:root[data-theme="light"]` token override and a `dark` Tailwind variant (`[data-theme="dark"] &`) consumed by Task 3.

- [ ] **Step 1: Register the dark custom variant**

In `web/src/styles/index.css`, immediately after the `@import "tailwindcss";` line, add:

```css
/* Resolved theme drives a data attribute on <html>; expose it as Tailwind's `dark:` variant so
   literal-color utilities (badges) can carry a light base + dark override. Design-token colors
   are handled by the :root[data-theme="light"] override below, not this variant. */
@custom-variant dark ([data-theme="dark"] &);
```

- [ ] **Step 2: Add the light token override**

In `web/src/styles/index.css`, immediately after the closing `}` of the `@theme { … }` block (before the `@keyframes reveal`), add:

```css
/* Light theme — "paper, not glare": soft gray app surface, white raised cards, deepened emerald
   accent that stays AA-legible on white. Overrides the @theme dark base; :root[data-theme=light]
   (0,2,0) beats @theme's :root (0,1,0). Keep token names identical so every utility re-resolves. */
:root[data-theme="light"] {
  --color-panel: #f4f6f8;
  --color-rail: #eceff3;
  --color-inspector: #f0f2f5;
  --color-panel-card: #ffffff;
  --color-panel-line: #dde3ea;
  --color-panel-line-strong: #c3ccd6;

  --color-ink: #1b2430;
  --color-ink-muted: #51616f;
  --color-ink-faint: #67768a;

  --color-accent: #047857;
  --color-accent-strong: #047857;
  --color-accent-ink: #ffffff;

  --color-focus: #0d9488;
}
```

- [ ] **Step 3: Verify the build compiles the new CSS**

Run: `cd web && pnpm build`
Expected: PASS (`tsc --noEmit` + vite build succeed).

- [ ] **Step 4: Sanity-check the tokens emitted**

Run: `cd web && pnpm build && grep -c 'data-theme="light"' dist/assets/*.css`
Expected: `1` or more (the override block is present in the bundle).

- [ ] **Step 5: Commit**

```bash
git add web/src/styles/index.css
git commit -m "feat(cockpit): light palette tokens + dark custom variant"
```

---

### Task 3: Light/dark badge colors (badges.tsx)

**Files:**
- Modify: `web/src/features/proof/badges.tsx`
- Modify: `web/src/features/proof/badges.test.tsx` (create if absent)

**Interfaces:**
- Consumes: the `dark` variant from Task 2.

- [ ] **Step 1: Write the failing test**

Create `web/src/features/proof/badges.test.tsx`:

```tsx
import { render } from "@testing-library/react";
import { expect, test } from "vitest";

import { ProviderTag, StatusBadge } from "./badges";

test("provider tag carries both a light base and a dark override class", () => {
  const { container } = render(
    <ProviderTag candidate={{ provider_id: "openai", privacy: "cloud" }} />,
  );
  const el = container.querySelector("span")!;
  expect(el.className).toContain("text-sky-700"); // light base
  expect(el.className).toContain("dark:text-sky-300"); // dark override
});

test("status badge carries both a light base and a dark override class", () => {
  const { container } = render(<StatusBadge kind="error">boom</StatusBadge>);
  const el = container.querySelector("span")!;
  expect(el.className).toContain("text-rose-700");
  expect(el.className).toContain("dark:text-rose-300");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && pnpm exec vitest run src/features/proof/badges.test.tsx`
Expected: FAIL — current classes are dark-only (`text-sky-300`, no `text-sky-700`).

- [ ] **Step 3: Update the badge style maps**

In `web/src/features/proof/badges.tsx`, replace the `PROVIDER_STYLE` map with:

```tsx
const PROVIDER_STYLE: Record<ProviderKind, { label: string; cls: string; Icon: LucideIcon }> = {
  mock: {
    label: "Mock",
    cls: "border-zinc-400/50 bg-zinc-400/10 text-zinc-600 dark:border-zinc-500/40 dark:bg-zinc-500/10 dark:text-zinc-300",
    Icon: FlaskConical,
  },
  local: {
    label: "Local",
    cls: "border-slate-400/50 bg-slate-400/10 text-slate-600 dark:border-slate-400/40 dark:bg-slate-400/10 dark:text-slate-200",
    Icon: HardDrive,
  },
  cloud: {
    label: "Cloud",
    cls: "border-sky-500/50 bg-sky-500/10 text-sky-700 dark:border-sky-400/40 dark:bg-sky-400/10 dark:text-sky-300",
    Icon: Cloud,
  },
};
```

And replace the `STATUS_STYLE` map with:

```tsx
const STATUS_STYLE: Record<"error" | "fail", { cls: string; Icon: LucideIcon }> = {
  error: {
    cls: "border-rose-500/50 bg-rose-500/10 text-rose-700 dark:border-rose-400/40 dark:bg-rose-500/10 dark:text-rose-300",
    Icon: CircleX,
  },
  fail: {
    cls: "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:border-amber-400/40 dark:bg-amber-500/10 dark:text-amber-300",
    Icon: TriangleAlert,
  },
};
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && pnpm exec vitest run src/features/proof/badges.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/badges.tsx web/src/features/proof/badges.test.tsx
git commit -m "feat(cockpit): light/dark badge colors via dark variant"
```

---

### Task 4: Theme switcher in the rail footer (App.tsx)

**Files:**
- Modify: `web/src/app/App.tsx`
- Modify: `web/src/app/App.test.tsx`

**Interfaces:**
- Consumes: `useTheme`, `ThemeChoice` from `web/src/lib/theme.ts` (Task 1).

- [ ] **Step 1: Write the failing test**

In `web/src/app/App.test.tsx`, add (uses the existing `mockServer` helper):

```tsx
test("theme switcher persists a choice and sets data-theme", async () => {
  mockServer();
  renderWithQuery(<App />);
  const dark = await screen.findByRole("radio", { name: "Dark" });
  fireEvent.click(dark);
  expect(dark).toHaveAttribute("aria-checked", "true");
  expect(localStorage.getItem("orionfold-theme")).toBe("dark");
  expect(document.documentElement.dataset.theme).toBe("dark");
});
```

Add to the existing `afterEach` in that file (alongside `vi.restoreAllMocks()`):

```tsx
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && pnpm exec vitest run src/app/App.test.tsx`
Expected: FAIL — no `radio` named "Dark".

- [ ] **Step 3: Add imports**

In `web/src/app/App.tsx`, add `Monitor`, `Moon`, `Sun` to the existing `lucide-react` import, and add a new import:

```tsx
import { useTheme, type ThemeChoice } from "../lib/theme";
```

- [ ] **Step 4: Add the `ThemeSwitcher` component**

In `web/src/app/App.tsx`, add above `LeftRail`:

```tsx
const THEMES: { value: ThemeChoice; label: string; Icon: LucideIcon }[] = [
  { value: "system", label: "System", Icon: Monitor },
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
];

// Replaces the old "Settings · soon" marker: a calm 3-way theme control pinned in the rail
// footer. radiogroup semantics so it's keyboard-navigable; the active segment uses the raised
// card surface, matching the nav's active treatment.
function ThemeSwitcher() {
  const { choice, setChoice } = useTheme();
  return (
    <div
      role="radiogroup"
      aria-label="Theme"
      className="flex gap-0.5 rounded-lg border border-(--color-panel-line) p-0.5"
    >
      {THEMES.map(({ value, label, Icon }) => {
        const active = value === choice;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            aria-label={label}
            title={label}
            onClick={() => setChoice(value)}
            className={
              "flex flex-1 items-center justify-center gap-1 rounded-md px-1.5 py-1 text-xs transition-colors " +
              (active
                ? "bg-(--color-panel-card) text-(--color-ink)"
                : "text-(--color-ink-muted) hover:text-(--color-ink)")
            }
          >
            <Icon aria-hidden className="h-3.5 w-3.5 shrink-0" />
            {label}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 5: Replace the Settings marker with the switcher**

In `web/src/app/App.tsx` `LeftRail`, replace the disabled Settings `<span aria-disabled="true" …>…</span>` block (the one containing `<SettingsIcon …>` and the `soon` tag) with:

```tsx
        <ThemeSwitcher />
```

Remove the now-unused `Settings as SettingsIcon` from the `lucide-react` import.

- [ ] **Step 6: Run the test to verify it passes**

Run: `cd web && pnpm exec vitest run src/app/App.test.tsx`
Expected: PASS.

- [ ] **Step 7: Full suite + build**

Run: `cd web && pnpm test && pnpm build`
Expected: all green; build succeeds (no unused-import error for `SettingsIcon`).

- [ ] **Step 8: Commit**

```bash
git add web/src/app/App.tsx web/src/app/App.test.tsx
git commit -m "feat(cockpit): theme switcher in the rail footer"
```

---

### Task 5: Theme the receipt export (export.py)

**Files:**
- Modify: `src/orionfold/receipts/export.py`
- Modify: `tests/unit/test_receipts.py` (existing receipt tests; build reports with the module's `_report()` helper)

**Interfaces:**
- Produces: `to_html(report: ProofReport, theme: str | None = None) -> str` — `theme` ∈ `{"light","dark"}` sets `data-theme` on `<html>`; anything else omits it.

- [ ] **Step 1: Write the failing test**

In `tests/unit/test_receipts.py`, add (reuse the existing module-level `_report()` helper that the other tests use):

```python
def test_html_receipt_carries_both_palettes():
    html_out = export.to_html(_report())
    assert "@media (prefers-color-scheme: light)" in html_out
    assert ':root[data-theme="light"]' in html_out
    assert ':root[data-theme="dark"]' in html_out
    # standalone (no explicit theme) must not pin a data-theme on <html>
    assert "data-theme=" not in html_out.split("<head>")[0]


def test_html_receipt_theme_param_pins_data_theme():
    report = _report()
    assert '<html lang="en" data-theme="light">' in export.to_html(report, theme="light")
    assert '<html lang="en" data-theme="dark">' in export.to_html(report, theme="dark")
    # an unknown theme is ignored (no attribute)
    assert '<html lang="en">' in export.to_html(report, theme="bogus")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_receipts.py -k "palette or theme_param" -v`
Expected: FAIL — `to_html` takes no `theme`; media query / data-theme selectors absent.

- [ ] **Step 3: Add a `theme` parameter and the `<html>` attribute**

In `src/orionfold/receipts/export.py`, change the signature:

```python
def to_html(report: ProofReport, theme: str | None = None) -> str:
```

and replace the `<html lang="en">` line in the returned f-string with:

```python
<html lang="en"{f' data-theme="{theme}"' if theme in ("light", "dark") else ""}>
```

- [ ] **Step 4: Replace hardcoded receipt colors with CSS variables**

In the same f-string's `<style>` block, replace the `:root {{ color-scheme: light dark; }}` line and every hardcoded color with variable-driven rules. Use exactly:

```css
  :root {{
    color-scheme: light dark;
    --rc-bg: #0b0f14; --rc-ink: #e6edf3; --rc-muted: #9fb0c0; --rc-line: #1c2530;
    --rc-rec-bg: #11331f; --rc-rec-line: #1f5135; --rc-rec-ink: #c8f5da;
    --rc-case: #c4d0db; --rc-case-key: #6f8190;
  }}
  @media (prefers-color-scheme: light) {{
    :root {{
      --rc-bg: #f4f6f8; --rc-ink: #1b2430; --rc-muted: #51616f; --rc-line: #dde3ea;
      --rc-rec-bg: #e7f7ee; --rc-rec-line: #b6e6cb; --rc-rec-ink: #0f5132;
      --rc-case: #2b3744; --rc-case-key: #67768a;
    }}
  }}
  :root[data-theme="dark"] {{
    --rc-bg: #0b0f14; --rc-ink: #e6edf3; --rc-muted: #9fb0c0; --rc-line: #1c2530;
    --rc-rec-bg: #11331f; --rc-rec-line: #1f5135; --rc-rec-ink: #c8f5da;
    --rc-case: #c4d0db; --rc-case-key: #6f8190;
  }}
  :root[data-theme="light"] {{
    --rc-bg: #f4f6f8; --rc-ink: #1b2430; --rc-muted: #51616f; --rc-line: #dde3ea;
    --rc-rec-bg: #e7f7ee; --rc-rec-line: #b6e6cb; --rc-rec-ink: #0f5132;
    --rc-case: #2b3744; --rc-case-key: #67768a;
  }}
  body {{ margin: 0; font: 15px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
         background: var(--rc-bg); color: var(--rc-ink); }}
  main {{ max-width: 56rem; margin: 0 auto; padding: 2.5rem 1.5rem; }}
  h1 {{ font-size: 1.5rem; letter-spacing: -0.01em; margin: 0 0 0.25rem; }}
  .rec {{ background: var(--rc-rec-bg); border: 1px solid var(--rc-rec-line); color: var(--rc-rec-ink);
          padding: 0.9rem 1rem; border-radius: 10px; margin: 1rem 0 1.5rem; }}
  dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; margin: 0 0 1.5rem; }}
  dt {{ color: var(--rc-muted); }} dd {{ margin: 0; }}
  table {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0 1.5rem; }}
  th, td {{ text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid var(--rc-line); }}
  th {{ color: var(--rc-muted); font-weight: 600; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
  .muted {{ color: var(--rc-muted); }}
  ul.failures {{ list-style: none; padding: 0; }}
  ul.failures > li {{ border: 1px solid var(--rc-line); border-radius: 10px; padding: 0.8rem 1rem; margin: 0.6rem 0; }}
  .case {{ color: var(--rc-case); margin-top: 0.25rem; }}
  .case > span {{ color: var(--rc-case-key); display: inline-block; min-width: 4.5rem; }}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/unit/test_receipts.py -k "palette or theme_param" -v`
Expected: PASS.

- [ ] **Step 6: Run the full receipt test module**

Run: `uv run pytest tests/unit/test_receipts.py -v`
Expected: PASS (existing content assertions still hold; `receipt_version` unchanged at 3).

- [ ] **Step 7: Commit**

```bash
git add src/orionfold/receipts/export.py tests/unit/test_receipts.py
git commit -m "feat(receipts): theme the HTML receipt (OS-adaptive + data-theme override)"
```

---

### Task 6: Inline route theme param + cockpit wiring

**Files:**
- Modify: `src/orionfold/server/routes.py` (the `download_receipt` handler)
- Modify: `tests/integration/test_proof_api.py` (existing `client` TestClient fixture; create a run inline)
- Modify: `web/src/lib/api.ts` (`receiptPreviewUrl`)
- Modify: `web/src/features/proof/ReceiptDetailView.tsx`
- Modify: `web/src/features/proof/ReceiptDetailView.test.tsx`

**Interfaces:**
- Consumes: `to_html(report, theme=…)` (Task 5); `useTheme().resolved` (Task 1).
- Produces: `receiptPreviewUrl(runId: string, theme?: "light" | "dark"): string`.

- [ ] **Step 1: Write the failing backend test**

In `tests/integration/test_proof_api.py`, add (mirror the run-creation in `test_html_receipt_can_be_served_inline_for_preview`, which posts a run with mock candidates and reads `["run"]["id"]`):

```python
def test_inline_receipt_theme_param_injects_data_theme(client):
    run_id = client.post(
        "/api/runs",
        json={
            "dataset_id": "investment-memo-summarization",
            "candidate_ids": ["mock_good", "mock_bad"],
            "brief": {"task_name": "Memo", "decision_question": "Which?", "success_criteria": ""},
        },
    ).json()["run"]["id"]

    light = client.get(f"/api/runs/{run_id}/receipt.html?inline=1&theme=light")
    assert light.status_code == 200
    assert 'data-theme="light"' in light.text

    # A plain download pins no theme (it self-adapts via prefers-color-scheme).
    download = client.get(f"/api/runs/{run_id}/receipt.html")
    assert "data-theme=" not in download.text.split("<head>")[0]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/integration/test_proof_api.py -k "theme_param" -v`
Expected: FAIL — `theme` not accepted / not injected.

- [ ] **Step 3: Thread `theme` through the handler**

In `src/orionfold/server/routes.py`, change the signature:

```python
def download_receipt(
    request: Request, run_id: str, fmt: str, inline: bool = False, theme: str | None = None
) -> Response:
```

and replace `body = render(report)` with:

```python
    if fmt == "html":
        body = export.to_html(report, theme=theme)
    else:
        body = render(report)
```

- [ ] **Step 4: Run to verify backend passes**

Run: `uv run pytest tests/integration/test_proof_api.py -k "theme_param" -v`
Expected: PASS. (The existing byte-identical inline/download test still passes — it sends no `theme`.)

- [ ] **Step 5: Add the theme arg to `receiptPreviewUrl`**

In `web/src/lib/api.ts`, replace `receiptPreviewUrl`:

```ts
// Same receipt, served for rendering (Content-Disposition: inline) so the cockpit can embed it.
// `theme` pins the iframe to the cockpit's resolved theme (overrides the receipt's OS media query).
export function receiptPreviewUrl(runId: string, theme?: "light" | "dark"): string {
  const t = theme ? `&theme=${theme}` : "";
  return `/api/runs/${runId}/receipt.html?inline=1${t}`;
}
```

- [ ] **Step 6: Write the failing frontend test (and fix the existing exact-match assertion)**

The existing first test asserts the iframe `src` with **exact equality**:

```tsx
  expect(frame).toHaveAttribute("src", "/api/runs/run_abc123def456/receipt.html?inline=1");
```

Appending the theme will break that. In `web/src/features/proof/ReceiptDetailView.test.tsx`, replace that line with a substring check:

```tsx
  expect(frame.getAttribute("src")).toContain("/api/runs/run_abc123def456/receipt.html?inline=1");
```

Then add a new test (mirror the existing inline `render(<ReceiptDetailView … />)` setup — there is no shared helper). The `matchMedia` shim resolves `system → light`, so the iframe must request `theme=light`:

```tsx
test("the preview iframe pins the cockpit's resolved theme", () => {
  render(<ReceiptDetailView report={SAMPLE_REPORT} onBack={() => {}} onExplore={() => {}} />);
  const frame = screen.getByTitle("Proof Receipt preview");
  expect(frame.getAttribute("src")).toContain("theme=light");
});
```

- [ ] **Step 7: Run to verify it fails**

Run: `cd web && pnpm exec vitest run src/features/proof/ReceiptDetailView.test.tsx`
Expected: the new test FAILs — `src` has no `theme=` (the existing tests pass with the substring edit).

- [ ] **Step 8: Wire `useTheme` into the preview**

In `web/src/features/proof/ReceiptDetailView.tsx`, add the import:

```tsx
import { useTheme } from "../../lib/theme";
```

Inside the component (near the top of its body), add:

```tsx
  const { resolved } = useTheme();
```

and change the iframe `src` to:

```tsx
        src={receiptPreviewUrl(run.id, resolved)}
```

- [ ] **Step 9: Run to verify it passes**

Run: `cd web && pnpm exec vitest run src/features/proof/ReceiptDetailView.test.tsx`
Expected: PASS (the existing `inline=1` assertion still holds).

- [ ] **Step 10: Full suites + build**

Run: `cd web && pnpm test && pnpm build && cd .. && uv run pytest`
Expected: all green.

- [ ] **Step 11: Commit**

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py web/src/lib/api.ts \
        web/src/features/proof/ReceiptDetailView.tsx web/src/features/proof/ReceiptDetailView.test.tsx
git commit -m "feat: pin the in-app receipt preview to the cockpit theme"
```

---

### Task 7: e2e, docs, samples, and the visual/UX gate

**Files:**
- Modify: `e2e/playwright/proof.spec.ts` (add a theme assertion) or create `e2e/playwright/theme.spec.ts`
- Modify: `docs/ux/product-design-system.md`
- Regenerate: `samples/receipts/*` via `scripts/gen_samples.py`

- [ ] **Step 1: Write the e2e theme check**

Create `e2e/playwright/theme.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test("theme switcher toggles to light and persists across reload", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("radio", { name: "Light" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
```

- [ ] **Step 2: Rebuild the embed and run e2e**

Run: `bash scripts/build.sh && cd web && pnpm e2e`
Expected: all e2e green (rebuild puts the new cockpit in the served artifact).

- [ ] **Step 3: Regenerate sample receipts**

Run: `uv run python scripts/gen_samples.py`
Then confirm the regenerated `samples/receipts/sample-proof-receipt.html` contains `@media (prefers-color-scheme: light)`:

Run: `grep -c "prefers-color-scheme: light" samples/receipts/sample-proof-receipt.html`
Expected: `1`.

- [ ] **Step 4: Document both themes**

In `docs/ux/product-design-system.md`, add a "Theming" subsection: the three-state model (System default), the `data-theme` mechanism (token override + `@custom-variant dark`), the `orionfold-theme` localStorage key, and the light palette table (copy from the spec §4). Keep it concise.

- [ ] **Step 5: Visual + UX gate (real browser)**

Invoke the `browser-visual-verification` skill, then the `ux-polish-review` skill. Build the embed, start `orionfold up` on a provably-free port (assert the listener PID is yours), run a proof, and in **light** theme screenshot: Proof Run setup, the leaderboard + decision summary, Datasets, and an opened Receipt. Confirm WCAG 2.2 AA for `--color-ink`, `--color-ink-muted`, `--color-ink-faint`, accent-as-text ("Recommended"), the filled CTA, and every badge. Confirm no FOUC on reload (System and explicit Light). Fix any token that misses AA in `index.css` / `export.py` and re-screenshot.

- [ ] **Step 6: Commit**

```bash
git add e2e/playwright/theme.spec.ts docs/ux/product-design-system.md samples/receipts/
git commit -m "test(e2e): theme toggle + persist; docs + regenerated light-aware samples"
```

---

## Self-Review

**Spec coverage:**
- §A theming mechanism → Task 2 (token override + `@custom-variant`). ✅
- §B state + no-flash → Task 1 (`theme.ts` + pre-paint script). ✅
- §C switcher → Task 4. ✅
- §D light palette → Task 2 (cockpit) + Task 5 (receipt). ✅
- §E receipt themed (standalone OS + iframe override) → Task 5 (CSS) + Task 6 (param/wiring). ✅
- §F verification → Tasks 1/3/4 (vitest), 5/6 (pytest), 7 (e2e + visual gate). ✅
- §G docs → Task 7. ✅ Sample regeneration → Task 7. ✅

**Placeholder scan:** Two deliberate "confirm the fixture/helper name in the existing test file" notes (Tasks 5/6) — the repo's test module/fixture names aren't in front of me; the instruction is to reuse the existing fixture, with exact assertion code given. No TODO/TBD/"handle edge cases".

**Type consistency:** `ThemeChoice`/`ResolvedTheme`, `getStoredChoice`/`resolveTheme`/`applyTheme`/`useTheme`, `receiptPreviewUrl(runId, theme?)`, `to_html(report, theme=None)` are used identically across Tasks 1, 4, 5, 6. localStorage key `orionfold-theme` and `data-theme` attribute consistent in the module, the pre-paint script, the switcher test, and the e2e. ✅

**Open implementation detail (non-blocking):** the receipt light `--rc-rec-*` (recommendation banner) and accent values are starting points; Task 7 step 5 measures and tunes any that miss AA.
