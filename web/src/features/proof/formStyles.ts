// Shared form-control styling for the Proof setup surface. One source of truth so the text inputs,
// selects, and textareas across RunSetup and PromptVariants stay visually identical — Orionfold
// form controls on the panel surface with a token-driven hairline and 8px (rounded-lg) radius.
export const inputCls =
  "rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-3 py-2 text-(--color-ink)";

// Selects share the same surface as inputCls but drop the native per-OS arrow
// (appearance-none) and reserve right room (pr-9) for a custom chevron seated by SelectField.
// Use pl-3 pr-9 rather than px-3 + pr-9 so the right padding can't lose a Tailwind source-order race.
export const selectCls =
  "w-full appearance-none rounded-lg border border-(--color-panel-line) bg-(--color-panel) py-2 pl-3 pr-9 text-(--color-ink)";
