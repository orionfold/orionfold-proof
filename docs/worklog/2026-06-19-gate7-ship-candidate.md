# 2026-06-19 — Gate 7: ship candidate

## Summary
Turned the verified Gate-6 build into a shippable v0 candidate. **No product code changed**
— the work was the ship surface (docs, packaging, release evidence) plus closing the one
open live test from Gate 6.

- **Closed the OpenRouter live smoke test (7/7).** `OPENROUTER_API_KEY` now resolves in this
  session, so the only un-exercised provider profile ran live: real summary
  (`"Q3 revenue increased by 22% to $48.2 million driven by enterprise growth."`), no key
  leak, `error=None`. The parametrized real-provider test
  (`test_cloud_provider_completes_without_leaking_key[openrouter]`) now runs instead of
  skipping. All seven profiles (mock pair excluded) are now proven live across this + Gate 6.
- **README rewrite.** Status `Gate 5` → `Gate 7`; new **Configure providers** section
  documenting the credential model (system env wins over repo-root `.env.local`; cloud
  candidates appear only when their key resolves), a placeholder `.env.local` example, and a
  defaults/overrides table for all six profiles plus `ORIONFOLD_MAX_TOKENS` /
  `ORIONFOLD_TIMEOUT_S`. Fixed stale "Gate 5 / empty target dirs / planned stack" copy.
- **`CHANGELOG.md`** (new, repo root) — Keep-a-Changelog `0.1.0` entry: the full v0 surface,
  a Security note, and Known Limitations (estimated-cost gaps, fixed timeout, design polish,
  mock-tuned rubric).
- **`docs/demo-script.md`** (new) — two-pass walkthrough: keyless (mocks → leaderboard →
  failure case → 3-format receipt) and a real-provider variant, referencing the screenshot
  and sample receipts.
- **Rebuilt the wheel** (`bash scripts/build.sh`) so the committed artifact carries the
  max-tokens/timeout knobs; **clean-installed it in a throwaway venv** and drove the full
  keyless path from the install.
- **Captured a real-provider screenshot** → `samples/screenshots/real-provider-leaderboard.png`
  (+ folder README): cockpit comparing the mocks against a live OpenRouter cloud candidate.
- Version kept at **`0.1.0`** (operator decision); docs placement = root `CHANGELOG.md` +
  `docs/demo-script.md` (operator decision).

## Verification
- `uv run pytest` → **65 passed** (OpenRouter now runs live, no longer skipped). `ruff
  check .` clean; `uv run pyright src` → **0 errors**. `pnpm --dir web test` → 3 passed;
  `pnpm --dir web build` clean; `pnpm --dir web e2e` → **1 passed** (embedded build, happy
  path).
- **OpenRouter live run (manual, evidence):** registry lists `openrouter`; model
  `openai/gpt-4o-mini`; real output; `latency_ms≈1463`; `error=None`; `KEY LEAK: False`;
  `raw_metadata` keys = `{provider, model}` only. Note `est_cost=$0.00` — OpenRouter's
  **namespaced** model id (`openai/gpt-4o-mini`) misses the pricing table keyed on bare
  `gpt-4o-mini`; this is the deliberate "unknown model → $0, estimated not authoritative"
  path (`pricing.py:31`), not a bug.
- **Clean install from the wheel** (isolated `uv venv`, `uv pip install dist/*.whl`): wheel
  embeds cockpit `index.html` + the demo dataset and stamps `RECEIPT_VERSION = 3`; `orionfold
  up` served the embedded cockpit, a keyless `mock_good`/`mock_bad` run completed, and all
  three receipts exported (`receipt_version: 3`, config_hash present, **no secrets**).
  _(Pitfall hit and resolved: a first attempt's curls hit a **stale long-running server from
  a previous session** that still held the old v2 `export` module in memory — it showed
  `receipt_version: 2`. Killed the stale process, bound a provably-free port, asserted the
  listener PID matched my throwaway server, and re-verified v3.)_
- **Real-provider screenshot** captured against the embedded build via Playwright (one-off
  script, since removed) — shows the OpenRouter cloud row on the leaderboard. Browser render
  confirmed the cockpit lists all 8 candidates (4 cloud) when keys resolve.
- **Security & secrets review** (skill + `security-reviewer` subagent): **PASS on all six
  checks, no fixes.** The reviewer extracted the real `ANTHROPIC_API_KEY` literal from
  `.env.local` and confirmed it appears **only** there — not in the PNG, sample receipts, or
  built wheel. Default path keyless; cloud opt-in; redaction (HTTP-layer literal scrub +
  regex) intact; Gemini header-only; `.env.local` gitignored + untracked.
- `receipt-quality-review` **not re-run**: its trigger (receipt structure / export /
  leaderboard *changes*) was not met — no such code changed, samples unchanged at v3, and
  the v3 export + secret-free receipt were already confirmed in the clean-install check.

## Product impact
v0 is now installable and self-explanatory. A new user can `uv tool install orionfold-proof
&& orionfold up`, run the keyless proof immediately, and — following the README's provider
section — point the same loop at OpenAI / OpenRouter / Gemini / Anthropic / Ollama / LM
Studio with a `.env.local`, getting one private, repeatable, secret-free receipt that names
which candidate to trust. Every charter v0 acceptance criterion is met.

## Risks
- **Timeout is a fixed wall-clock value** (`ORIONFOLD_TIMEOUT_S`). The right primitive is a
  progress-based streaming idle timeout + backstop, with per-class defaults — candidate
  **ADR-0003** + a focused streaming change. Documented as the interim knob.
- **Estimated-cost gaps**: namespaced model ids (OpenRouter) and any non-default model show
  `$0.00`. Costs are labeled estimated, never authoritative; expanding the price table is a
  trivial later add.
- **Design-system polish still OWED**: the cockpit is functional Gate-5 scaffolding, not the
  three-pane design in `docs/ux/product-design-system.md`. This is the next headline task.
- Real-provider tests stay lenient (a clean 401 passes the no-leak check) — green ≠ proven
  live success; rely on the manual OpenRouter/Gemini/Anthropic run evidence in the worklogs.
- Brand naming: README title is "Orionfold Proof Receipt" while the cockpit/pyproject use
  "Orionfold Proof" — cosmetic, left as-is.

## Next recommended step
**Design-system polish pass** on the cockpit — bring it to the documented three-pane design
(`docs/ux/product-design-system.md`), verified with the `browser-visual-verification` and
`ux-polish-review` skills. Pair with **ADR-0003** (progress-based streaming timeout) if the
operator wants the timeout fix in the same pass.
