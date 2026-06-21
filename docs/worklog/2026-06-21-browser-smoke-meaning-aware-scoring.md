# 2026-06-21 — Browser smoke: meaning-aware scoring (RECEIPT_VERSION 5)

## Summary

End-to-end visual verification of the last release (meaning-aware scoring, live-review
Finding 2) in a real browser via Claude-in-Chrome. No code changes — verification only.
Rebuilt the cockpit embed fresh, started a clean server on a provably-free port with a
fresh demo DB, and drove the full keyless proof path.

## Verification

- Build: `pnpm --dir web build` → embed copied to `src/orionfold/server/static` (fresh).
- Server: `ORIONFOLD_DB=/tmp/orionfold-smoke.db orionfold up --port 8842` (PID 18601, mine;
  health HTTP 200). Codex checkout on 8787 left alone.
- Browser (tab on `http://127.0.0.1:8842`):
  - Configure: keyless default — Mock·good + Mock·bad pre-checked, cloud models off.
  - Scoring method picker present and interactive (Auto · Keypoint · Similarity · LLM judge).
  - LLM judge → judge-model grid with `Mock judge` keyless default + KeyEntry machinery.
  - Auto run → Inspector rubric `keypoint · threshold 0.8`, config hash `467ddd96c9a5`.
  - Decision: `RECOMMENDED Mock · good`; new line `Scored by Keypoint coverage`; new
    `Run cost: candidate $0.0000 · judge $0.0000 · total $0.0000`.
  - Leaderboard `100% (5/5)` vs `0% (0/5)`; Failure cases (5) incl. `simulated provider failure`.
  - No console errors.
- Receipt exports (API read, `run_36533705742c`): MD/HTML/JSON all carry `Receipt schema: v5`,
  Verdict **Ship**, `scored_by: "Keypoint coverage"`, `cost {candidate, judge, total}`.
  Secret scan across all three formats: **0 hits**.
- fable-5 absent from catalog (Finding 3 holds).

## Product impact

Confirms the shipped release renders and exports correctly for a keyless operator: a correct
summary is now scored by meaning (keypoint coverage), judge cost is reported separately, and
the receipt is secret-free at v5. Decision-grade proof path is intact end-to-end.

## Risks / observations (non-blocking)

- Scoring-method picker is positioned *below* the "Run proof" card rather than inside the
  configure flow above the button — slightly out of reading order for a run input.
- Stale dev servers from prior sessions still listening (8788, 8814, 8861, 63210); harmless cruft.

## Next recommended step

Proceed with #6 PROMPT-VARIANT CANDIDATES (brainstorm first), per HANDOFF.
