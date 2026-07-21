import { defineConfig, devices } from "@playwright/test";

/**
 * Config for the README screenshots (`npm run screenshots`).
 *
 * Separate from playwright.config.ts on purpose. The e2e suite mocks the API so
 * CI needs no Python; the screenshots must show numbers the real core actually
 * computed, so this one starts uvicorn as well. It is never run in CI -- the
 * figures change only when the UI does.
 */
export default defineConfig({
  testDir: "./screenshots",
  fullyParallel: false, // both specs drive the same API; keep the output stable
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    colorScheme: "light", // the README renders on a light page on GitHub
    deviceScaleFactor: 2, // retina, so the figures stay sharp when scaled down
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "uv run uvicorn capstat_api.main:app --port 8000 " +
        "--reload-dir ../../packages/capstat-core/src",
      cwd: "../api",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
