# Visual Verification Checklist

For each UI change, before declaring done. Pairs with the `browser-visual-verification`
skill. Never assert UI success from the diff alone.

- [ ] Dev server is running and the exact route is named.
- [ ] Each state (empty, loading, error, populated) is rendered and screenshotted.
- [ ] Each screenshot is compared against the design/target or prior state, and
      differences are listed explicitly.
- [ ] Only the visible issue is fixed (no opportunistic redesign), then re-verified.
- [ ] Keyboard path works for the core action.
- [ ] Color contrast meets WCAG 2.2 AA.
- [ ] No secrets, API keys, or full provider config appear anywhere on screen.

## Tools, in order

1. Claude in Chrome — quick localhost checks.
2. Playwright (direct or MCP) — multi-viewport screenshots, visual regression, self-grading.
3. Chrome DevTools MCP — only for performance, network, or accessibility-tree inspection.

Add screenshot regression tests only where they earn their keep; avoid brittle snapshots
of every minor layout.
