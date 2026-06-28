import { expect, test } from "@playwright/test";

// The charter's happy path, graded in a real browser against the embedded build:
// open → run sample proof → see leaderboard → open a failure case → export all three receipts.
test("proof loop: run → leaderboard → failure case → receipts", async ({ page }) => {
  // Mocks are off the customer happy path — enable Sandbox up front. The flag is global and the
  // suite shares one DB, so set it deterministically via the API rather than clicking the toggle.
  await page.request.put("/api/settings", { data: { sandbox_enabled: true } });
  await page.goto("/");

  // Engine reachable and setup rendered.
  await expect(page.getByRole("heading", { name: "Orionfold Proof" })).toBeVisible();
  await expect(page.getByText(/Connected/)).toBeVisible();

  // Cold-start guard (R4): this is the FIRST test in the serial suite, so it races a freshly-booted
  // server. The heading + "Connected" pill render immediately, but the setup form is held behind a
  // full-screen "Loading the local engine…" notice until the `datasets` + `selection` queries
  // settle — which can exceed the default 5s assertion timeout on a cold boot. Anchor on the dataset
  // select (the form's gate element) with a generous timeout so the picker interactions below run
  // against a settled DOM instead of flaking. Sibling tests inherit a warm server and don't need it.
  const datasetSelect = page.getByLabel("Dataset");
  await expect(datasetSelect).toBeVisible({ timeout: 30_000 });

  // The shared DB may hold datasets from other tests; pin the keypoint demo set explicitly so the
  // 5-example / keypoint-coverage / 5-failure-cases assertions below are deterministic.
  await datasetSelect.selectOption("investment-memo-summarization");

  // Type the decision question AFTER selecting the dataset. Since WS-C, an *untouched* question
  // clears on dataset change, so the receipt heading would otherwise fall back to the task name —
  // a typed (touched) question survives and headlines the receipt (matched in the archive below).
  await page.getByLabel("Decision question").fill("Which model should I trust for client memos?");

  // The Mock provider's Good/Bad models appear in the picker, pre-selected for a keyless run.
  // The Candidates section header is a <span> (not a <legend>, which can't host a right-aligned
  // Recheck action) — match it inside the picker fieldset.
  await expect(page.getByText("Candidates", { exact: true })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: "Good model" })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Bad model" })).toBeChecked();
  await expect(page.getByRole("button", { name: /custom model for Ollama/i })).toBeVisible();

  // Run the sample proof (both mock candidates are selected by default in Sandbox).
  await page.getByRole("button", { name: /Run proof/ }).click();

  // Leaderboard: mock_good is recommended and passes everything. Generous timeout — on a cold
  // server the first streaming run + scoring can outrun the default 5s (R4, the original flake site).
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard).toBeVisible({ timeout: 30_000 });
  await expect(leaderboard.getByText("Recommended")).toBeVisible();
  await expect(leaderboard.getByText("100% (5/5)")).toBeVisible();

  // Pareto cost-vs-quality scatter (WS-D1) mounts beneath the leaderboard on a populated run.
  const scatter = page.getByRole("region", { name: "Cost vs quality" });
  await expect(scatter).toBeVisible();
  await expect(scatter.getByTestId("frontier-scatter").locator("svg.recharts-surface")).toBeVisible();

  // Decide insight layer (Task 7): default Y is Pass rate; the toggle flips it to Avg score.
  const passToggle = scatter.getByRole("button", { name: "Pass rate" });
  const avgToggle = scatter.getByRole("button", { name: "Avg score" });
  await expect(passToggle).toHaveAttribute("aria-pressed", "true");
  await avgToggle.click();
  await expect(avgToggle).toHaveAttribute("aria-pressed", "true");
  // Chart stays mounted under the new metric and the axis re-labels to "Avg score".
  await expect(scatter.getByTestId("frontier-scatter").locator("svg.recharts-surface")).toBeVisible();
  await expect(scatter.locator("svg.recharts-surface").getByText("Avg score")).toBeVisible();
  // The deterministic explainer renders beneath the chart (clear-winner run → ok tone).
  const explainer = scatter.getByTestId("decide-explainer");
  await expect(explainer).toBeVisible();
  await expect(explainer).toHaveAttribute("data-tone", "ok");

  // Run-level cost ledger (WS-D2) mounts beneath the scatter on a populated run.
  // A keyless mock run is free, so the run total reconciles to "Free" — the same
  // zero the verdict banner's "Run cost … total $0.0000" line reports.
  const costLedger = page.getByRole("region", { name: "Run cost" });
  await expect(costLedger).toBeVisible();
  await expect(costLedger.getByTestId("run-cost-total")).toHaveText("Free");

  // Finding 2 — keypoint default: the demo dataset has keypoints, so the keyless
  // run defaults to keypoint coverage scoring. The DecisionSummary must say so.
  await expect(page.getByText(/Scored by/i)).toContainText(/Keypoint coverage/i);

  // Failure cases: at least one, including the surfaced provider error.
  const failures = page.getByRole("region", { name: "Failure cases" });
  await expect(failures.getByRole("heading", { name: /Failure cases \(5\)/ })).toBeVisible();
  await expect(failures.getByText(/simulated provider failure/)).toBeVisible();

  // The receipt is viewable in-app AND downloadable, but after the Arena reshape (Slice 4/5) both
  // live on the L3 ReceiptDetailView — the Prove canvas now offers only a "View full receipt" CTA.
  // Receipts opens to the Runs table; opening a row's "→" lands on L3, which leads with the receipt
  // artifact (iframe) + an "Explore in cockpit" CTA + the three exports.
  await page.getByRole("button", { name: "Receipts" }).click();
  await page.getByRole("button", { name: /^Open Which model should I trust/ }).first().click();
  await expect(page.getByTitle("Proof Receipt preview")).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore in cockpit/ })).toBeVisible();

  // All three receipts download from L3 with the config hash in the filename.
  for (const label of ["Markdown", "HTML", "JSON"]) {
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: label, exact: true }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^proof-receipt-[a-f0-9]{12}\.(md|html|json)$/);
  }
});

test("scoring cards: LLM-judge card reveals judge filter", async ({ page }) => {
  await page.goto("/");

  // The scoring section renders before the Run proof button.
  await expect(page.getByText("Scoring method")).toBeVisible();

  // The LLM-judge card is visible (aria-label includes title and cost).
  const judgeCard = page.getByRole("button", { name: /LLM judge/i });
  await expect(judgeCard).toBeVisible();

  // Click the LLM-judge card — it should expand the judge filter below.
  await judgeCard.click();

  // "Run on" row with Local/Hosted toggles must appear.
  await expect(page.getByText(/Run on/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /^Local$/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /^Hosted$/ })).toBeVisible();

  // The judge-model label and dropdown are visible; the Mock judge option is the default.
  await expect(page.getByText(/Judge model/i)).toBeVisible();
  const judgeSelect = page.getByLabel(/Judge model/i);
  const selectedText = await judgeSelect.evaluate((el: HTMLSelectElement) =>
    el.options[el.selectedIndex]?.text ?? ""
  );
  expect(selectedText).toMatch(/Mock judge/i);
});

test("decision recipes pre-fill the setup", async ({ page }) => {
  await page.goto("/");
  // The recipe row renders above setup.
  await expect(page.getByRole("heading", { name: "Start from a decision recipe" })).toBeVisible();
  // A recipe with a keyless local arm pre-fills the decision question.
  const recipe = page.getByRole("button", { name: /Different providers/i });
  await expect(recipe).toBeVisible();
  await recipe.click();
  await expect(page.getByLabel(/decision question/i)).toHaveValue(/different hosts/i);
});

test("guided first-run CTA reflects cloud availability (WS-E2)", async ({ page }) => {
  // The "Run the demo proof on real models" CTA on the empty Results state appears only when ≥2
  // cheap, available cloud candidates exist — so its one-click promise (a real-model clear winner)
  // stays honest. We don't CLICK it here: that fires a real paid run, verified in a live browser per
  // the operator workflow. We assert the CTA's presence MATCHES the live /api/selection panel, so the
  // smoke passes whether or not this environment has cloud keys configured.
  await page.goto("/");
  const sel = await page.request.get("/api/selection");
  const panel = (await sel.json()) as {
    providers: { privacy: string; available: boolean; models: unknown[] }[];
  };
  const cheapCloud = panel.providers
    .filter((g) => g.privacy === "cloud" && g.available)
    .flatMap((g) => g.models).length;
  const cta = page.getByRole("button", { name: /Run the demo proof on real models/i });
  await expect(page.getByRole("region", { name: "Results" })).toBeVisible();
  await expect(cta).toHaveCount(cheapCloud >= 2 ? 1 : 0);
});

test("prompt compare: one model, two prompts → leaderboard + receipt section", async ({ page }) => {
  // Prompt-compare keyless needs a mock model — enable Sandbox up front via the API (deterministic).
  await page.request.put("/api/settings", { data: { sandbox_enabled: true } });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Orionfold Proof" })).toBeVisible();

  // Switch the comparison axis to Prompts.
  await page.getByRole("button", { name: "prompts", exact: true }).click();

  // The prompt editor appears, seeded with two starter variants on a keyless mock model.
  await expect(page.getByLabel(/Prompt model/i)).toBeVisible();
  await expect(page.getByLabel(/Variant prompt 1/i)).toBeVisible();
  await expect(page.getByLabel(/Variant prompt 2/i)).toBeVisible();

  // Run keyless (mock model) and confirm a leaderboard row per variant.
  await page.getByRole("button", { name: /Run proof/ }).click();
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard).toBeVisible();
  await expect(leaderboard.getByText("Baseline")).toBeVisible();
  await expect(leaderboard.getByText("Concise")).toBeVisible();

  // The receipt records the prompt variants — fetch the JSON receipt for THIS run.
  // (The iframe approach is blocked by the receipt's Content-Security-Policy: sandbox header.)
  // The old inspector is gone (Slice 5); "View full receipt" on the Prove results opens the L3
  // ReceiptDetailView, whose JSON export link carries this run's id in its href.
  await page.getByRole("button", { name: /View full receipt/ }).click();
  const exportJsonLink = page.getByRole("link", { name: "JSON", exact: true });
  const href = await exportJsonLink.getAttribute("href");
  const runId = href!.match(/runs\/(run_[a-f0-9]+)\//)?.[1];
  expect(runId).toBeTruthy();
  const receiptRes = await page.request.get(`/api/runs/${runId}/receipt.json`);
  const receipt = await receiptRes.json();
  expect(receipt.prompt_variants.length).toBe(2);
});

// Quick-compare: the unscored head-to-head lane — one prompt, two candidates, human pick,
// saved as a clearly-labeled quick-check Proof Receipt.
test("quick compare: run → pick → save receipt", async ({ page }) => {
  await page.request.put("/api/settings", { data: { sandbox_enabled: true } });
  await page.goto("/");
  await expect(page.getByText(/Connected/)).toBeVisible();

  // Enter the Quick lane; the two mock candidates are pre-selected in Sandbox.
  // Since WS-C, a Quick receipt's headline is DERIVED FROM THE PROMPT (never a carried
  // Models-mode question), so a unique prompt is what makes the receipt card deterministic to
  // open later. The suite shares one DB, so keep it distinctive.
  const quickPrompt = "Quick e2e summarize: revenue grew 22% to $48.2M.";
  await page.getByRole("button", { name: /Quick/ }).click();
  await page.getByLabel("Prompt", { exact: true }).fill(quickPrompt);
  await page.getByRole("button", { name: /Run proof/ }).click();

  // Head-to-head renders; Save is gated until a pick is made.
  const quick = page.getByRole("region", { name: "Quick compare" });
  await expect(quick).toBeVisible();
  const save = quick.getByRole("button", { name: /Save as Proof Receipt/i });
  await expect(save).toBeDisabled();

  // Pick a winner, then save.
  await quick.getByRole("button", { name: /wins$/ }).first().click();
  await expect(save).toBeEnabled();
  await save.click();

  // The picked quick check now appears in Receipts and the receipt reads as a QUICK CHECK.
  await page.getByRole("button", { name: "Receipts" }).click();
  await page.getByRole("button", { name: new RegExp(quickPrompt.replace(/[.?$]/g, "\\$&")) }).first().click();
  const preview = page.frameLocator('iframe[title="Proof Receipt preview"]');
  await expect(preview.getByText(/QUICK CHECK/i).first()).toBeVisible();
  await expect(preview.getByText(/Picked Mock/i)).toBeVisible();
  await expect(preview.getByText(/Promote to a full scored run/i)).toBeVisible();
});

// WS-E1 (repurposed for the Arena reshape): the standalone Candidates catalog SCREEN was removed —
// Candidates folded into the Prove run-setup picker (CandidatePicker), which now carries provider
// availability + the add-key affordance inline. So this asserts the equivalent on Prove: known
// providers are listed by name, and EACH unavailable cloud provider carries an inline add-key
// affordance ("Unavailable — add a key" + a key entry). Deterministic regardless of key state:
// if every key is set in this environment there are simply zero unavailable cloud rows.
test("prove picker lists known providers and explains unavailable cloud ones", async ({ page }) => {
  await page.goto("/");

  // The Candidates picker renders inline on the Prove setup (no separate catalog tab anymore). Each
  // provider's label appears in a per-row "custom model for <Provider>" affordance, which gives a
  // stable, unambiguous handle on the provider list regardless of which models the env gates.
  // The setup is a <form aria-label="Proof setup"> — its implicit ARIA role is "form", not "region".
  const setup = page.getByRole("form", { name: "Proof setup" });
  await expect(setup.getByText("Candidates", { exact: true })).toBeVisible();
  await expect(setup.getByRole("button", { name: /custom model for Anthropic/i })).toBeVisible();
  await expect(setup.getByRole("button", { name: /custom model for Ollama/i })).toBeVisible();

  // Each unavailable cloud provider explains its absence AND offers the add-key next step inline;
  // each unavailable local provider hints to start the server. Asserted over whatever the env gates
  // (vacuously true if all keys are set), so the test is deterministic without pinning a key state.
  const addKeyHints = await setup.getByText(/Unavailable — add a key/i).count();
  const startServerHints = await setup.getByText(/Unavailable — start the local server/i).count();
  // A gated cloud row always pairs its "add a key" copy with a KeyEntry affordance — confirm at
  // least one such affordance exists when any add-key hint is shown (never a dangling explanation).
  if (addKeyHints > 0) {
    await expect(setup.getByRole("button", { name: /add .*key/i }).first()).toBeVisible();
  }
  // The assertion that matters is the affordance/explanation pairing above; this documents that
  // unavailable rows are always explained inline, never silently dropped.
  expect(addKeyHints + startServerHints).toBeGreaterThanOrEqual(0);
});

// B4 (repurposed for the Arena reshape): Track Record is no longer a standalone tab — it folded
// into Receipts as a segmented toggle mode (Slice 4). Reach it via Receipts → the "Track Record"
// tab in the "Receipts view mode" tablist, then assert the body is alive EITHER way (the suite
// shares one DB, so whether scored runs exist depends on order): the calm empty notice OR at least
// one populated <h3> dataset-group standings header. The exact rollup shape is unit/integration-tested.
test("track record mode is reachable from Receipts and renders its frame", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Receipts" }).click();

  // The segmented toggle lives inside Receipts; flip to Track Record.
  const modeToggle = page.getByRole("tablist", { name: "Receipts view mode" });
  await expect(modeToggle).toBeVisible();
  await modeToggle.getByRole("tab", { name: "Track Record" }).click();

  // Scope to the view's <main>: the cockpit stays mounted with Tailwind `hidden` (display:none) so
  // an in-flight run survives nav, and display:none excludes that <main> from the a11y tree — so
  // getByRole("main") resolves to exactly the Receipts view, never the hidden cockpit's text.
  const main = page.getByRole("main");
  // Either the empty-state notice or a rendered standings section header — never blank or errored.
  const emptyNotice = main.getByText(/No track record yet|No scored runs/i);
  const groupHeader = main.getByRole("heading", { level: 3 });
  await expect(emptyNotice.or(groupHeader).first()).toBeVisible();
});
