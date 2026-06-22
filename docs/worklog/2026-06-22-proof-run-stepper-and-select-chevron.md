# 2026-06-22 — Proof Run: numbered stepper + custom select chevron

## Summary
Reshaped the top of the Proof Run setup into a calm, numbered inline workflow and fixed the
dataset dropdown's chevron, all pure presentation (no data-model / engine / receipt / `config_hash`
surface touched).

- **Dataset dropdown + Compare-by switcher → one row, then a numbered stepper.** The two top
  controls now read as **① Select dataset** ——— **② Compare by [Models | Prompts]**, using the same
  accent number-badge + hairline-connector language as the top `StageStepper` (Configure/Run/Decide)
  and the LLM-judge controls.
- **Extracted `WorkflowStep.tsx`** (`Step` + `StepLine`) from `JudgeFilter`'s local copies so the
  judge picker and the run-setup steps share one source of truth and cannot visually drift. The
  cockpit now has a two-tier stepper vocabulary: `StageStepper` (stateful top-level loop) and
  `WorkflowStep` (always-on inline config flows).
- **Custom select chevron.** New `SelectField` wraps a native `<select>` with `appearance-none` +
  a lucide `ChevronDown` and opened-up right padding (`selectCls` uses `pl-3 pr-9`, avoiding the
  `px-3 pr-9` source-order race). The native per-OS arrow sat flush at the edge; the custom chevron
  has breathing room and is theme-aware (`--color-ink-muted`). Applied to both the dataset and the
  prompt-model selects so they stay identical.
- `SelectField`'s `className` sizes the **wrapper** (the chevron's positioning context), so the
  dataset field can take a contained desktop width (`w-full sm:w-[27rem]`, sized to fit the longest
  sample name without clipping) while a default (no-className) select stays full-width in a grid/label.

## Verification
- `pnpm exec tsc --noEmit` → clean (exit 0).
- `pnpm test` → 90/90 unit tests pass (incl. unchanged `RunSetup` and `JudgeFilter` suites; the
  `JudgeFilter` tests assert behavior, so the `Step`/`StepLine` extraction is invisible to them).
- Real browser (Vite live source on :5174, `/api` → `orionfold dev` on :8790, dark + light):
  - Stepper renders ① / ② with cyan badges and the connector hairline; matches the top stepper.
  - Dataset field shows the full "Investment memo summarization (5 examples)" with chevron padding.
  - Prompts mode: prompt-model select stays full-width with the custom chevron.
  - LLM-judge scoring: `JudgeFilter` still renders ① Run on / ② Optimize / ③ Judge model via the
    shared component — no regression.

## Product impact
The run setup now reads as a guided "do this, then this" decision flow rather than a stack of
controls — reinforcing the calm-instrument-panel north star and making the first run more legible
for a newcomer, without adding any steps or persistence.

## Risks / deferrals
- The **③ Judge model** select inside `JudgeFilter` still uses its native browser chevron, so it is
  now slightly inconsistent with the dataset/prompt-model selects. Deferred (out of this request's
  scope) — a one-line swap to `SelectField` when desired.
- `:8787` on this machine is occupied by an unrelated app ("self-wealth" dashboard); Orionfold was
  run on `:8790` for verification. Environment-only, not a code issue.

## Next recommended step
Operator decision: optionally unify the judge-model select chevron (`SelectField`), then resume the
standing backlog (top item: git remote + push — `main` is still unpushed).
