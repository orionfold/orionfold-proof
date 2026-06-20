---
name: browser-visual-verification
description: Use for any UI change. Renders the route in a real browser, screenshots each state, compares against the target, and lists precise visual differences before fixing. Closes the loop so UI work is graded, not asserted.
---

# Browser visual verification

Never declare UI work done from the diff alone. Close the loop in a real browser.

## Procedure

1. **Start or check the dev server.** Confirm it is running and note the exact URL
   (e.g. `http://localhost:8787`).
2. **Name the exact route** you are verifying.
3. **Test one state at a time** — empty, loading, error, populated. Capture a
   screenshot of each.
4. **Compare** each screenshot against the design target or the prior state.
5. **List differences explicitly** before changing anything.
6. **Fix only the visible issue** unless instructed otherwise, then re-verify.

## Tools, in order of preference

1. **Claude in Chrome** — quick visual checks of localhost; click through and screenshot.
2. **Playwright** (directly or via MCP) — automated navigation, multi-viewport
   screenshots, visual regression. Highest leverage: the model opens the app and grades
   itself.
3. **Chrome DevTools MCP** — only for performance, network, or accessibility-tree inspection.

## Checklist before "done"

- Each state rendered and screenshotted; differences from target listed.
- Keyboard path works for the core action.
- Color contrast meets WCAG 2.2 AA.
- No secrets or API keys appear anywhere on screen.
