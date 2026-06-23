# Worklog — 2026-06-23 · WS-E1 (Candidates inline add-key / start-host affordance)

Stage 3, Task 9 of the approved `_SPECS/2026-06-22-trustworthy-proof-and-polish.md` point queue.
Committed to `main` as `f65e686`.

## Summary

The **Candidates** catalog (the rail destination) previously rendered from `/api/candidates`,
which lists **only available** candidates. A cloud-only or no-Ollama user therefore saw an
incomplete list with **no explanation of what was missing or how to turn it on** — the exact gap
WS-E1 names ("an unconfigured provider … explains its absence").

Fix (FE-only): `CandidatesView` now renders from **`/api/selection`** — the selection panel, which
lists **every catalog provider** grouped, each with an `available` flag (sandbox-aware, resolved
server-side). Per provider:

- **Available** → its models are listed (display name + model id), full ink.
- **Unconfigured cloud** (`!available && CLOUD_KEY_NAMES[id]`) → dimmed brand logo, neutral **Cloud**
  identity tag, **"Not configured"**, a reason naming the exact env var
  (*"Add a ANTHROPIC_API_KEY key to compare Anthropic models."*), and the existing inline
  **`<KeyEntry>`** — which writes the key to `.env.local` server-side (never echoed) and invalidates
  the `["selection"]` query so the card flips to available **live**.
- **Unconfigured local** (`!available`, no key) → a **"Start the local server"** hint
  (`ollama serve` / LM Studio). No key to add.

Operator decision (asked up front): **reuse the inline `KeyEntry`** rather than a "Add key in
Settings →" deep-link — SettingsView has no key field to land on, and `KeyEntry` is the already-built,
secrets-guard-safe path used in 3 other places (`CandidatePicker`, `JudgeFilter`, `RecipeRow`).

Reuses `KeyEntry`, `CLOUD_KEY_NAMES`, `ProviderTag`, `ProviderLogo`, and the selection panel's
`available` gate — **no new gating, no key-entry rebuild**. Also removed the now-orphaned
`getCandidates()` client wrapper (the `/api/candidates` endpoint + `candidateSchema`/`Candidate`
type stay — still used by `runSchema` and `badges.tsx`).

## Verification

- **Unit:** new `CandidatesView.test.tsx` (3 tests) — unconfigured cloud shows the reason + env-var
  name + Add-key button; unconfigured local shows the start-host hint (no key field); a configured
  provider lists models with exactly **one** add-key button across the panel (distinguishing gated
  Anthropic from available OpenAI). **192 FE (+3)**.
- **Backend:** **298 BE unchanged** (FE-only; no backend/Pydantic/migration/`config_hash` touched —
  mock matrix `467ddd96c9a5` intact by construction).
- **tsc + vite build:** clean.
- **Playwright:** **12/12** (+1 smoke `candidates catalog lists known providers and explains
  unconfigured ones`: catalog renders provider names from the selection panel; each gated provider
  carries an affordance + reason). Re-embedded the fresh build into the gitignored package static dir.
- **Real-browser (per CLAUDE.md):** stood up a **keyless** API instance via `ORIONFOLD_ENV_FILE`
  override + cleared cloud-key env vars (the real `.env.local` was never read or modified — the
  secrets-guard correctly blocked reading it) to force the unconfigured state. Confirmed all 4 cloud
  providers (Anthropic/OpenAI/Gemini/OpenRouter) show "Not configured" + env-var reason + Add-key;
  the inline field reveals on click (password input placeholdered with the env var name + cyan
  Save-key control); 2 local providers (Ollama/LM Studio) list models. **Light + dark graded**,
  screenshots **secret-free** (keys are write-only via password fields).
- **Fresh-context diff-reviewer:** **ship-ready** — all six verification points pass, no regressions,
  no DS violations, no scope creep. Non-blocking notes: e2e final assertion is environment-dependent
  (deterministic provider-name assertions carry the weight); `getByRole("main")` is safe because the
  hidden ProofCockpit `<main>` uses Tailwind `hidden` (`display:none`, excluded from the a11y tree) —
  load-bearing if that view ever switches to visibility/opacity.

## Product impact

Closes the activation gap for a fresh install: the Candidates view is now an honest map of *what you
can prove and what's one step away*, not a list that silently omits unconfigured providers. A
cloud-only user can add a key right where they notice the absence; a local user is told to start the
host. DS-clean — cost/identity stays neutral, the only accent is the interactive Save control.

## Risks

- The e2e smoke's last assertion proves little on its own (vacuous when every key is configured in the
  test environment); the provider-name assertions are the real coverage. Acceptable.
- `getByRole("main")` in the e2e relies on ProofCockpit staying `hidden` (`display:none`). If a future
  change toggles it via `visibility`/`opacity`, the locator becomes strict-mode ambiguous.

## Files

- `web/src/features/proof/CandidatesView.tsx` — rewritten (selection-panel source + 3-state cards).
- `web/src/features/proof/CandidatesView.test.tsx` — new (3 tests).
- `web/src/lib/api.ts` — removed orphaned `getCandidates()`.
- `e2e/playwright/proof.spec.ts` — +1 smoke test.

## Next recommended step

**Task 10 — WS-E2 (Guided first-run CTA).** ⚠️ **BLOCKED on the demo-scorer default fix** (see
`_IDEAS/issues.md` "REAL-RUN … NO CLEAR WINNER"): the bundled summarization demo still reads "no
winner" under the shipped 0.55 Similarity default, so a one-click CTA would land users on failing
dots — worse than the blank form. Fix the demo scorer default (→ LLM judge) FIRST, then build the CTA.
Alternatively pick up **Task 11 — WS-F (DS application-consistency pass, LOW)** which is unblocked.
