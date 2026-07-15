import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// The `@/` alias mirrors tsconfig's paths so tests import the same way the app
// does. Tests are the pure-logic ones under lib/; components (which need a DOM)
// are covered by the Playwright smoke test instead.
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
  test: {
    include: ["lib/**/*.test.ts"],
    environment: "node",
  },
});
