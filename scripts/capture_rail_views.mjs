// One-off visual-evidence capture for the wired rail destinations. Drives the EMBEDDED build
// served by a running `orionfold up` (pass its port via PORT) and writes PNGs to
// samples/screenshots/. The server's DB must already contain at least one proof run so the
// Receipts view is populated. Run from web/:  PORT=<port> node ../scripts/capture_rail_views.mjs
import { createRequire } from "module";
// Resolve @playwright/test from the cwd (run this from web/, where it's installed) rather than
// from this file's directory under scripts/, which has no node_modules.
const require = createRequire(`${process.cwd()}/`);
const { chromium } = require("@playwright/test");

const PORT = process.env.PORT;
if (!PORT) throw new Error("Set PORT to the running orionfold server port");
const BASE = `http://127.0.0.1:${PORT}`;
const OUT = "../samples/screenshots";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

async function shot(name) {
  // Park the cursor off the rail and let the hover transition settle so a lingering :hover
  // doesn't read as a second selection in the evidence shot.
  await page.mouse.move(1200, 700);
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log(`saved ${name}.png`);
}

await page.goto(`${BASE}/`);
await page.getByRole("button", { name: /Run proof/ }).waitFor();

await page.getByRole("button", { name: "Datasets" }).click();
await page.getByRole("heading", { name: "Datasets" }).waitFor();
await shot("rail-datasets");

await page.getByRole("button", { name: "Candidates" }).click();
await page.getByRole("heading", { name: "Candidates" }).waitFor();
await shot("rail-candidates");

await page.getByRole("button", { name: "Receipts" }).click();
await page.getByLabel("Past proof runs").waitFor();
await shot("rail-receipts");

await browser.close();
console.log("done");
