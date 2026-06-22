# 2026-06-22 — Theme chooser → Settings · default dark for first-run

## Summary
Two small UX changes to the theme control:

1. **Moved the theme chooser into Settings.** The 3-way System/Light/Dark switcher
   used to be pinned in the left-rail footer. It now lives in a new **Appearance**
   card at the top of the Settings view (above Data management), as a labelled
   "Theme" row. The rail footer keeps only the engine-status pill.
2. **Default theme is now dark for first-time users.** Previously the first-run
   default resolved to `system`; new installs now land in dark and can switch to
   System to follow the OS. Changed in both theme sources that must stay in lockstep:
   - `web/index.html` pre-paint script (`|| "dark"`) — avoids a flash before React mounts.
   - `web/src/lib/theme.ts` `getStoredChoice()` fallback (`"dark"`).

The switcher's active segment now uses the codebase's standard selected-state
treatment (`border-(--color-accent)/50 bg-(--color-accent)/10`, as in MethodCard /
CandidatePicker) so selection reads clearly on the card surface in both themes.

## Files
- `web/src/app/App.tsx` — removed `ThemeSwitcher` + `THEMES` from the rail; dropped now-unused imports; refreshed the stale rail comment.
- `web/src/features/proof/SettingsView.tsx` — new Appearance section + relocated `ThemeSwitcher`.
- `web/src/lib/theme.ts` — first-run default `system` → `dark`.
- `web/index.html` — pre-paint default `system` → `dark`.
- Tests: `theme.test.ts` (default expectation), `App.test.tsx` (removed rail switcher test), `SettingsView.test.tsx` (added switcher test), `ReceiptDetailView.test.tsx` (pin explicit choice instead of relying on default), `e2e/playwright/theme.spec.ts` (navigate to Settings first; added first-run-defaults-dark test).

## Verification
- `pnpm --dir web exec tsc --noEmit` — clean.
- `pnpm --dir web test` — 90 passed (23 files).
- `bash scripts/build.sh` — clean (embeds cockpit).
- `pnpm --dir web exec playwright test` — 9/9 passed (serial), incl. both theme specs.
- Real browser (Vite dev, proxied API): fresh install (localStorage cleared) boots
  `data-theme=dark`; Settings → Appearance shows the switcher with Dark active;
  clicking Light applies instantly and persists (`stored=light`, `data-theme=light`).
  Screenshots captured for dark + light Settings.

## Product impact
Settings is the natural home for appearance, decluttering the rail so it reads as
pure navigation + status. Dark-first matches the cockpit's dark-first design intent
(`@theme` default) so new operators see the product as designed.

## Risks
- Low. No data-model, engine, receipt, or `config_hash` surface touched. The DS
  accent/status split is respected (the switcher uses the cyan accent only as the
  interactive selected state).

## Next recommended step
Unchanged from the existing backlog (HANDOFF): git remote + push (top item).
