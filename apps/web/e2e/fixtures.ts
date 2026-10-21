import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test as base } from "@playwright/test";

import { checkRequest, type ContractBreak } from "./contract/check-request";
import type { OpenApiSpec } from "./contract/openapi-contract";

/**
 * `test` for every spec in this directory: Playwright's, plus a contract check.
 *
 * The suite mocks the API (playwright.config.ts), and a mock answers 200 to
 * whatever it is sent. That is how "Decide the lot" shipped a body the real
 * endpoint refuses with a 422 and stayed green for six weeks (T-0099). So every
 * request the page makes to the API is also checked against the committed
 * `apps/api/openapi.json` -- the schema the API's own models are exported to --
 * and a test fails if the API would have refused the request, whatever its mock
 * said.
 *
 * It listens to the page's `request` event rather than wrapping `page.route`:
 * the specs register dozens of their own handlers, and an event sees what the
 * browser actually sent, after any handler, whether it fulfilled, continued or
 * aborted. A spec that forgets to opt in cannot opt out of it either, because
 * `page` itself is the fixture that is replaced.
 */

const OPENAPI_PATH = path.resolve(__dirname, "../../api/openapi.json");

let cached: OpenApiSpec | undefined;
function spec(): OpenApiSpec {
  cached ??= JSON.parse(readFileSync(OPENAPI_PATH, "utf8")) as OpenApiSpec;
  return cached;
}

/** The origin the app under test sends API requests to. */
export const API_ORIGIN = new URL(
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
).origin;

export const test = base.extend({
  // The second argument is Playwright's `use`; it is named otherwise because
  // eslint's rules-of-hooks takes any call to `use` for a React hook.
  page: async ({ page }, provide) => {
    const breaks: ContractBreak[] = [];
    page.on("request", (request) => {
      const found = checkRequest(spec(), API_ORIGIN, request);
      if (found) breaks.push(found);
    });
    await provide(page);
    // Soft: the test's own verdict (and any earlier failure) stays visible.
    expect
      .soft(
        breaks,
        "the API would have refused a request this page sent (apps/api/openapi.json)",
      )
      .toEqual([]);
  },
});

export { expect };
