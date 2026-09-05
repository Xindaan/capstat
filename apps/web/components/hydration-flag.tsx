"use client";

import { useEffect } from "react";

/**
 * Mark the document once React has taken over the server-rendered HTML.
 *
 * Rendered from the root layout, so this effect runs only after the whole
 * initial tree has committed -- which is precisely the moment every control on
 * the page starts listening. Before it, the page looks finished and is not:
 * the markup is there, `load` has fired, but no handler is attached yet.
 *
 * The e2e suite waits on this attribute (see e2e/support.ts). It had been
 * driving pages that had merely *loaded*, and a `fill` that lands in that
 * window is not replaced by hydration but survives beside it -- Playwright
 * selects the old text, React re-renders and drops the selection, and the typed
 * text is inserted rather than substituted. The suite then posted sixteen lots
 * where the test had written three (T-0083).
 *
 * There is no supported way to observe this from outside: React exposes no
 * hydration event, `networkidle` never arrives under `next dev`'s open HMR
 * socket, and the fibers React attaches to DOM nodes land top-down, so a parent
 * carries one while its inputs are still dead. A committed effect is the only
 * signal that means what it says.
 */
export function HydrationFlag() {
  useEffect(() => {
    document.documentElement.dataset.hydrated = "true";
  }, []);
  return null;
}
