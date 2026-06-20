# Accessibility Checklist

Target: WCAG 2.2 AA. Reference: https://www.w3.org/WAI/WCAG22/quickref/

## Per interactive view

- [ ] Color contrast meets AA (≥ 4.5:1 body text, ≥ 3:1 large text and UI components).
- [ ] Status is never conveyed by color alone (pass/warn/fail also have text or icon).
- [ ] Full keyboard path for the core action: tab order is logical, focus is visible.
- [ ] All controls have accessible names (labels, `aria-label`, or associated `<label>`).
- [ ] Forms expose errors programmatically and associate them with fields.
- [ ] Images/icons that convey meaning have text alternatives; decorative ones are hidden.
- [ ] Live regions announce async results (proof run completion, export success/failure).
- [ ] Dialogs/menus trap and restore focus correctly; Escape closes them.
- [ ] Content reflows without loss at 200% zoom and narrow widths.
- [ ] Motion is minimal and respects `prefers-reduced-motion`.

## Receipt (HTML export)

- [ ] Semantic headings and tables; readable without app CSS.
- [ ] Sufficient contrast in printed/standalone form.
