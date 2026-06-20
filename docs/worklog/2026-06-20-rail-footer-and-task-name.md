# 2026-06-20 — Polish pass: sticky rail footer (#2) + receipt task-name sync

> Two small, atomic, fully-verified UI fixes from the operator's backlog priority
> (chosen order 1 > 2 > 4 > 3): the sticky rail footer (#2) and the live-eval
> follow-up on the receipt heading. Committed to `main` (not pushed).

## Summary

- **#2 Sticky rail footer** (`030b9db`). The left rail used `lg:h-full` + `mt-auto` on
  its footer (Settings + engine-status pill). In the 2-col CSS grid, `h-full` resolves
  against the **row** height — which grows to the (tall) main-pane content — so the rail
  stretched and `mt-auto` parked the footer at the bottom of that tall column, below the
  fold. On any long run page the footer scrolled away. Fix: make the rail viewport-height
  and sticky on desktop (`lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto`) so it pins
  to the viewport and `mt-auto` anchors the footer to the screen's bottom edge. Mobile
  (stacked block) unchanged.

- **Receipt Task-name sync** (`11f035e`). The Proof Receipt's HTML subtitle (the line
  under "Proof Receipt", `export.py:229`) is `brief.task_name`, but Task name was a static
  default ("Investment memo summarization") that never followed the Dataset dropdown — so a
  receipt for an **imported** dataset showed the bundled set's name in its headline (the
  `Dataset:` line was always correct; only the headline was stale). Fix: ProofCockpit
  derives an `effectiveBrief` — until the user types in the Task name field, it mirrors the
  selected dataset's name; the first edit sets `taskNameTouched` and locks it. Editing the
  decision question does **not** lock the task name. `effectiveBrief` feeds both the form
  and the run body, so the stored brief (and the receipt) track the dataset. **No receipt
  schema change** (still v3) — no `version` bump needed.

## Verification (evidence, not claims)

- `pnpm test`: **17** frontend units green (was 16; +1 new test covering sync + lock).
- `pnpm build`: clean (`tsc --noEmit` + vite).
- `pnpm e2e`: **2/2** Playwright green (rebuilt embed first).
- **Browser (port 8814, fresh temp DB, listener PID asserted mine):**
  - #2: ran a proof → long page → scrolled to `scrollY == scrollMax`; measured
    `position:sticky`, `asideTop:0`, `asideBottom == innerHeight`, footer fully on-screen.
  - Task name: imported "Client memo summaries v1" via `POST /api/datasets` → selected it →
    Task name auto-synced → ran proof → opened the in-app receipt → **subtitle reads
    "Client memo summaries v1"** (matches the Dataset line). Screenshots captured.

## Product impact

The instrument panel stays oriented (engine status / Settings always visible), and the
product's key deliverable — the Proof Receipt — no longer ships a client-facing heading that
contradicts the dataset it was run on. Both are calm-confidence fixes, not features.

## Risks

- None blocking. Commits on `main` are **not pushed**.
- Light theme (#1) and decision recipes (#5) remain; both are sizable and want a plan /
  brainstorm gate before code.

## Next recommended step

Operator's call between the two remaining threads (priority had #1 before #5):
1. **#1 Light theme + switcher** — token audit of all `--color-*` for a light set + a
   persisted `data-theme` toggle in the now-sticky rail footer (where "Settings · soon"
   sits). Sizable; **start in plan mode**.
2. **#5 Decision recipes** — named comparison presets bundling a candidate panel + starter
   question. **Needs its own brainstorm** before any plan/code.
