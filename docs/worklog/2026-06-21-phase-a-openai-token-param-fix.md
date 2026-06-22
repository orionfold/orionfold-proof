# Worklog — 2026-06-21 · Phase A: OpenAI `max_tokens` fix + judge-default triage

## Summary

Closed **Phase A** of the post-smoke plan (see
`2026-06-21-browser-smoke-last-three-releases.md` and the prior HANDOFF):

1. **Issue 1 — FIXED (confirmed code bug, was blocking ALL OpenAI runs).** OpenAI's GPT-5.x models
   reject the legacy `max_tokens` parameter with `HTTP 400: "Unsupported parameter: 'max_tokens' is
   not supported with this model. Use 'max_completion_tokens' instead."` This blocked every OpenAI
   candidate **and** the OpenAI hosted LLM-judge. Fix (TDD, no paid calls): added a per-profile
   `token_param: str = "max_tokens"` to `OpenAICompatibleProvider`; the payload now sends
   `{self.token_param: max_output_tokens()}`. The registry wires the **OpenAI** profile with
   `token_param="max_completion_tokens"`; OpenRouter + LM Studio (same class, accept the legacy name)
   keep the default `"max_tokens"`. The judge resolves through `get_provider`, so it inherits the fix
   for free.

2. **Issue 2 — triaged: already handled by existing gating; real symptom was Issue 1.** The reported
   "Hosted judge defaults to Claude Haiku · Anthropic and errors with no Anthropic key" is **not
   reproducible** in current code. `filterJudgeModels` already routes any unavailable cloud provider
   to a `gated` hint-row (KeyEntry) and **never** offers it as an option, so the Hosted default lands
   on the first *available/keyed* recommended provider in catalog order — with Anthropic unkeyed and
   OpenAI/Gemini/OpenRouter keyed, that default is **OpenAI**, not Anthropic. The smoke-test error was
   therefore Issue 1 (the `max_tokens` 400) firing on the auto-selected OpenAI judge, mis-attributed
   to Anthropic. Added a regression guard codifying the invariant: *the Hosted judge default is never
   an unavailable provider.* No production change needed.

3. **Issue 3 — deferred (low priority, already bounded + safe).** Raw provider error JSON is already
   capped at `_MAX_ERROR_BODY = 500` chars and run through `_scrub_error_body` + `redact_secrets`
   (no secret leak — re-confirmed by the prior smoke). The verbatim body is useful for debugging;
   normalizing it further would strip diagnostics for no security gain. Left as-is.

## Verification (all green)

- `uv run pytest` → **226 passed** (was 223; +3 new: two in `test_providers_http.py` —
  OpenAI sends `max_completion_tokens` / others keep `max_tokens` — and one in `test_registry.py`
  asserting the profile wiring). 1 pre-existing 3rd-party StarletteDeprecationWarning.
- `uv run ruff check src tests` → clean.
- `pnpm --dir web test` → **84 passed** (was 83; +1 Issue-2 guard in `scoring.test.ts`).
- `pnpm --dir web build` → clean. `bash scripts/build.sh` → wheel built (embed rebuilt).
- `pnpm --dir web e2e` → **6/6 passed** (fresh DB on port 8799).

### Files changed

- `src/orionfold/providers/openai_compatible.py` — added `token_param` ctor arg; payload uses it.
- `src/orionfold/providers/registry.py` — OpenAI profile wired with `token_param="max_completion_tokens"`.
- `tests/unit/test_providers_http.py` — 2 payload tests (OpenAI vs default cap param).
- `tests/unit/test_registry.py` — 1 wiring test.
- `web/src/features/proof/scoring.test.ts` — 1 Issue-2 regression guard.
- `CHANGELOG.md` — Fixed entry for the OpenAI cap parameter.

## Product impact

OpenAI candidates and the OpenAI hosted judge now actually run instead of 400-erroring — the cross-
provider model-compare (OpenAI + Gemini + OpenRouter) and any OpenAI-graded judge run are unblocked.
The judge picker is verified to never auto-select an unkeyed provider.

## Risks / notes

- The fix is verified keyless (stubbed POST asserts the wire param). A **real** paid OpenAI call has
  not yet been re-run — that is exactly Phase B's job.
- Model-compare byte-identity is untouched: the change is confined to the OpenAI wire-payload key name
  and registry wiring; it cannot affect `config_hash` (sample `467ddd96c9a5`) or the mocks.

## Next recommended step

**Phase B — comprehensive REAL-WORLD browser smoke** (Claude-in-Chrome, real keys in `.env.local`).
This spends real money (OpenAI billing topped up; Gemini + OpenRouter healthy; add an Anthropic key
to cover it). It needs the operator's go-ahead before launching the paid session. Checklist lives in
HANDOFF.md (custom dataset import · real cross-provider model-compare · decision recipes · model
picker/catalog · all 4 scoring methods incl. a real LLM judge · prompt-variant compare on a real
model · streaming progress · leaderboard/verdict · failure-case browser · receipt export + secret
scan · Candidates/Receipts views · keyless regression guard `467ddd96c9a5`).
