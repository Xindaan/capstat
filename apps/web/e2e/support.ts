import type { Page } from "@playwright/test";

/**
 * Navigate, and wait until the page is actually usable.
 *
 * Two separate waits, because "loaded" and "listening" are different moments.
 *
 * `load` rather than `networkidle`: under `next dev` the HMR connection stays
 * open, so the network never goes idle and that wait either hangs or expires —
 * which is worse than not waiting at all. Route and bundle compilation, the
 * cost that actually made tests flaky, is paid before the suite starts
 * instead; see e2e/global-setup.ts.
 *
 * `load` alone, though, only says the markup and scripts arrived. React has
 * not necessarily run: measured under a throttled CPU, *no* element on the
 * page carried a React fiber at that point. Acting there is not a slow no-op
 * but a corrupting one — `fill` selects the server-rendered text, React
 * re-renders and drops the selection, and the typed text is inserted in front
 * of the old value instead of replacing it. That is how the suite came to post
 * sixteen lots for a three-lot series (T-0083).
 *
 * So we also wait for the flag the app raises from a committed root effect
 * (see components/hydration-flag.tsx). Probing React's own fibers instead was
 * tried and rejected: they are attached top-down, so `body` carries one while
 * the inputs beneath it are still dead, and the nodes Next injects never carry
 * one at all — there is no element whose fiber means "the page is live".
 */
export async function gotoReady(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "load" });
  await hydrated(page);
}

/** Wait for React to have taken over the server-rendered markup. */
export async function hydrated(page: Page): Promise<void> {
  await page.waitForSelector('html[data-hydrated="true"]', {
    state: "attached",
  });
}

/**
 * Run `action` and return the JSON body of the request it causes.
 *
 * The tests that assert "what reaches the API" used to push each intercepted
 * body into a local array and then `expect.poll` it. Polling was already the
 * second attempt -- reading the array once lost about one run in three,
 * because the label under test renders from component state and therefore
 * appears before the request necessarily has. But a poll carries a fixed 5 s
 * budget, and under parallel load with a cold `next dev` compile that budget
 * is exactly what ran out: T-0038 and then T-0049, the same shape twice.
 *
 * Waiting on the request *event* removes the budget from the equation. It is
 * armed before the action, so there is no window in which the request could be
 * missed, and it resolves the instant the request is made rather than up to a
 * poll interval later.
 *
 * Use this where one action causes one request. Where an assertion is about a
 * settled end state after several actions -- the run-rule selection in
 * smoke.spec -- polling the last captured body is still the right tool, because
 * the claim there is about where things came to rest, not about a single
 * request.
 */
export async function requestDuring<T>(
  page: Page,
  urlPattern: string,
  action: () => Promise<void>,
): Promise<T> {
  const [request] = await Promise.all([
    page.waitForRequest(urlPattern),
    action(),
  ]);
  return request.postDataJSON() as T;
}
