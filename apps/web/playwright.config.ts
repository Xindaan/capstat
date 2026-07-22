import { defineConfig, devices } from "@playwright/test";

// A single-browser smoke test. The API is mocked per-test (see e2e/smoke.spec),
// so this needs only the Next dev server -- no Python backend, no network.
export default defineConfig({
  testDir: "./e2e",
  // Compile the routes before the first test; see e2e/global-setup.ts.
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
