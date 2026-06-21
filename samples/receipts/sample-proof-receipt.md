# Proof Receipt

**Verdict: Ship** — Mock · good (mock_good) — passed 5/5 (100%), avg latency 57ms, est. cost $0.00, local.

_2 candidate(s) × 5 example(s) · rubric keypoint ≥ 0.8_

- **Decision:** Which model should I trust for client memos?
- **Task:** Investment memo summarization
- **Dataset:** Investment memo summarization (`investment-memo-summarization`)
- **Rubric:** keypoint ≥ 0.8
- **Scored by:** Keypoint coverage
- **Run id:** `run_sampledemo01`
- **Config hash:** `467ddd96c9a5`
- **Generated:** 2026-06-19T12:00:00Z
- **Receipt schema:** v6

## Leaderboard

| Candidate | Provider | Privacy | Pass rate | Avg score | Avg latency | Est. cost | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mock · good ⭐ | mock_good | local | 100% (5/5) | 1.00 | 57ms | $0.00 | 0 |
| Mock · bad | mock_bad | local | 0% (0/5) | 0.00 | 126ms | $0.00 | 5 |

_Run cost: candidate $0.0000 · judge $0.0000 · total $0.0000_

## Failure cases (5)

- **mock_bad** · example 0 · score 0.00
  - input: Q3 revenue reached $48.2M, up 22% year over year, driven by enterprise seat expansion. Net revenue retention held at 118%. Gross margin improved to 79% as infrastructure costs were renegotiated.
  - expected: Revenue grew 22% to $48.2M on enterprise expansion, with 118% net retention and margins improving to 79%.
  - output: This document discusses various financial topics and market conditions.
- **mock_bad** · example 1 · score 0.00
  - input: The company burned $6.1M in the quarter against $52M cash on hand, giving roughly eight quarters of runway. Management paused hiring outside of engineering and reaffirmed a path to breakeven by late next year.
  - expected: Burn of $6.1M leaves about eight quarters of runway; hiring paused except engineering, with breakeven targeted late next year.
  - output: This document discusses various financial topics and market conditions.
- **mock_bad** · example 2 · error: RuntimeError: mock_bad: simulated provider failure
  - input: Churn ticked up to 4.2% monthly among self-serve customers, concentrated in accounts under ten seats. Enterprise churn remained under 1%. The team is shifting acquisition spend toward larger accounts. Management is testing onboarding fixes.
  - expected: Self-serve churn rose to 4.2% in small accounts while enterprise stayed under 1%, prompting a shift to larger-account acquisition.
  - output: —
- **mock_bad** · example 3 · score 0.00
  - input: A new competitor launched an aggressively priced tier and captured several mid-market logos. The company responded with annual-contract discounts, protecting retention but compressing average selling price by 9%.
  - expected: Competitive pricing pressure cost mid-market logos; annual discounts defended retention but cut average selling price 9%.
  - output: This document discusses various financial topics and market conditions.
- **mock_bad** · example 4 · score 0.00
  - input: The founders are raising a $15M Series B at a $90M post-money valuation, a 2.1x markup from the prior round. Lead investor is requesting a board seat and a standard 1x non-participating liquidation preference.
  - expected: Raising $15M Series B at $90M post (2.1x markup); lead seeks a board seat and a 1x non-participating preference.
  - output: This document discusses various financial topics and market conditions.

## Repro

- **Run id:** `run_sampledemo01`
- **Config hash:** `467ddd96c9a5` (identical inputs reproduce this hash)
- **Generated:** 2026-06-19T12:00:00Z
- **Rerun:** `POST /api/runs {"dataset_id": "investment-memo-summarization", "candidate_ids": ["mock_good", "mock_bad"]}`
