"use client";

/**
 * Hands the current analysis to the browser's print dialog, which is also its
 * "save as PDF". The print stylesheet in globals.css does the rest: controls
 * drop away, the results stay, and the ECharts SVG comes out vector.
 *
 * Server-side PDF rendering is deliberately not here (see TASK.md): it would
 * mean a headless browser in the API image for something every browser already
 * does well.
 */
export function PrintButton() {
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className="h-9 shrink-0 rounded-lg border border-foreground/20 px-3 text-sm text-foreground/70 transition-colors hover:text-foreground"
    >
      Print / save as PDF
    </button>
  );
}
