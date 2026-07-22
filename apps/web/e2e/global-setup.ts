import { chromium } from "@playwright/test";

/**
 * Compile every route — server *and* client — before the workers start.
 *
 * The suite drives `next dev`, which compiles a route on first request and its
 * client bundle when a browser first asks for the chunks. Left to the tests,
 * that cost lands on whichever test happens to go first, and with several
 * workers hitting a cold page at once it lands on all of them. The failures
 * then read as assertions about missing results, never about compilation.
 *
 * A plain HTTP fetch is not enough: it compiles the server component and stops
 * there. Driving a real browser page is what forces the client chunks through
 * as well, which is the half that was still being paid per test.
 */
const ROUTES = ["/", "/gage-rr", "/msa", "/acceptance-sampling"];

export default async function warmRoutes() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ baseURL: "http://localhost:3000" });
  for (const route of ROUTES) {
    await page.goto(route, { waitUntil: "load", timeout: 120_000 });
  }
  await browser.close();
}
