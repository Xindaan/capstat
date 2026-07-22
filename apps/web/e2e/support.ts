import type { Page } from "@playwright/test";

/**
 * Navigate, and wait for the document to finish loading.
 *
 * Deliberately `load` rather than `networkidle`: under `next dev` the HMR
 * connection stays open, so the network never goes idle and that wait either
 * hangs or expires — which is worse than not waiting at all. Route and bundle
 * compilation, the cost that actually made tests flaky, is paid before the
 * suite starts instead; see e2e/global-setup.ts.
 */
export async function gotoReady(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "load" });
}
