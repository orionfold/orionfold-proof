# Sample screenshots

Captured against the embedded build on the 0.2.0 **Arena-shape cockpit** — a compact top app bar
(Prove · Datasets · Receipts · Settings), a full-width always-on **telemetry rail** (host CPU / GPU /
memory · runtime · last result · cost · last receipt), and a full-width canvas. Dark theme, keyless
Sandbox run (the bundled investment-memo demo on the two deterministic mock candidates). No key
material appears anywhere in any run or receipt.

- **`rail-prove-result.png`** — the README hero: the Prove canvas after a keyless mock run, with the
  telemetry rail showing a live `5/5` last result, the dataset + decision-recipe panel, and the
  candidate picker. The whole instrument in one frame.
- **`cockpit-arena-populated.png`** — the full Prove page (long capture): the verdict band
  (recommended winner), the leaderboard (Mock · good vs Mock · bad), the cost-vs-quality scatter,
  and the run-cost ledger, all on one scrolling canvas.
- **`stream-configure.png`** — the Prove setup before a run: dataset selected, decision question
  filled, the five scoring-method cards.
- **`rail-datasets.png`** — the Datasets screen (coverage strip, governance bench badge, corpus).
- **`rail-receipts.png`** — the Receipts screen: the bento masthead (Latest proof · Cost today ·
  Cost to date · Library) over the `[ Runs | Track Record ]` toggle and the compact Runs table.
- **`receipt-detail-l3.png`** — the L3 receipt detail (tabbed): the v12 Proof Receipt artifact —
  verdict hero, metric spine, the pass-rate + cost-vs-quality figures — with the Receipt / Run config
  / Leaderboard / Cost / Failure cases tabs and the Markdown / HTML / JSON export links.
- **`rail-settings.png`** — the Settings bento (Appearance · Runtime · scoring thresholds · data
  management), including the GPU-telemetry toggle with its ready/needs-setup badge.

Note: mock runs are deterministic and keyless — they prove the **loop and the receipt**, not a real
model's score. See [`../../docs/demo-script.md`](../../docs/demo-script.md). Regenerate after a UI
change with `CAPTURE=1 pnpm --dir web exec playwright test capture-screenshots.spec.ts`.
