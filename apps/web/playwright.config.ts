import { defineConfig, devices } from "@playwright/test";

// The port is overridable (E2E_PORT) so several checkouts can run the suite at
// the same time; 3000 stays the default.
const PORT = Number(process.env.E2E_PORT ?? 3000);

// A single-browser smoke test. The API is mocked per-test (see e2e/smoke.spec),
// so this needs only the Next dev server -- no Python backend, no network.
export default defineConfig({
  testDir: "./e2e",
  // Only *.spec.ts: the *.test.ts files under e2e/contract belong to vitest
  // (the contract validator is plain logic) and use import.meta, which
  // Playwright's loader rejects.
  testMatch: "**/*.spec.ts",
  // Compile the routes before the first test; see e2e/global-setup.ts.
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `npm run dev -- --port ${PORT}`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
