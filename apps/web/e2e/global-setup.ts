import { request } from "@playwright/test";

/**
 * Compile every route before the clock starts on the first test.
 *
 * The e2e suite runs against `next dev`, which compiles a route lazily on its
 * first request. That compile can take longer than a test's own timeout, so
 * whichever test happened to reach a cold route first would fail — with an
 * assertion error about a missing result, never about compilation. It bit the
 * acceptance-sampling page as soon as that page grew a client workspace, and it
 * would bite CI every run, where the dev server is always fresh.
 *
 * Fetching each route here pays that cost once, outside any test's budget.
 */
const ROUTES = ["/", "/gage-rr", "/msa", "/acceptance-sampling"];

export default async function warmRoutes() {
  const context = await request.newContext({
    baseURL: "http://localhost:3000",
  });
  for (const route of ROUTES) {
    await context.get(route, { timeout: 120_000 });
  }
  await context.dispose();
}
