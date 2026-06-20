import { defineConfig, devices } from "@playwright/test";

// E2E runs against the EMBEDDED build (the real shipped artifact): the wheel-served cockpit
// + FastAPI on one port. The webServer boots `orionfold up` from the repo root with a temp
// DB so the run is reproducible and never touches the user's real database.
const PORT = 8799;
const DB = "/tmp/orionfold-e2e.db";

export default defineConfig({
  testDir: "../e2e/playwright",
  fullyParallel: true,
  reporter: [["line"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `bash -c "rm -f ${DB} && cd .. && ORIONFOLD_DB=${DB} uv run orionfold up --port ${PORT}"`,
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
