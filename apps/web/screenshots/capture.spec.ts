/**
 * Capture the README screenshots.
 *
 * Not a test: it asserts only enough to guarantee it never photographs an empty
 * or half-rendered panel. Run it with `npm run screenshots`, which starts both
 * the real API and the app -- deliberately *not* the mocked stack the e2e specs
 * use. A project whose whole claim is reference-validated numbers must not put
 * invented ones in its README, so every figure here is computed by the real
 * core from `examples/shaft-diameter.csv`.
 *
 * Re-shoot after any UI change; that is the whole reason this is a script and
 * not a folder of hand-taken pictures.
 */

import { expect, test, type Locator } from "@playwright/test";
import path from "node:path";

// Playwright runs with the config's directory (apps/web) as the cwd.
const REPO = path.resolve(process.cwd(), "../..");
const CSV = path.join(REPO, "examples/shaft-diameter.csv");
const OUT = path.join(REPO, "docs/images");

// The spec the demo dataset is built around (see examples/shaft-diameter.csv).
const LSL = "9.70";
const USL = "10.30";

/** Screenshot a panel, after waiting for the chart inside it to have painted. */
async function shoot(panel: Locator, name: string) {
  await expect(panel).toBeVisible();
  // ECharts renders SVG. Count the paths rather than asserting the first one is
  // visible: the first child is typically an invisible clip path, so visibility
  // is the wrong signal. A drawn chart has many paths; an undrawn one has none.
  if (await panel.locator("svg").count()) {
    await expect
      .poll(() => panel.locator("svg path").count(), { timeout: 10_000 })
      .toBeGreaterThan(5);
  }
  // Screenshot a padded clip rather than the element: a bare element shot cuts
  // flush against the border, which clips uppercase field labels that overflow
  // their box by a pixel or two.
  // Document coordinates, not viewport ones: boundingBox() is relative to the
  // viewport, while a fullPage clip is relative to the document. The two agree
  // only while the page is unscrolled, so using boundingBox() here silently
  // slides the crop down the page once anything has scrolled.
  const box = await panel.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return {
      x: r.x + window.scrollX,
      y: r.y + window.scrollY,
      width: r.width,
      height: r.height,
    };
  });
  if (!box.width || !box.height) {
    throw new Error(`panel for ${name} has no layout box`);
  }
  const pad = 12;
  await panel.page().screenshot({
    path: path.join(OUT, name),
    // fullPage, or the clip would be capped at the viewport -- these panels are
    // taller than the window.
    fullPage: true,
    clip: {
      x: Math.max(0, box.x - pad),
      y: Math.max(0, box.y - pad),
      width: box.width + pad * 2,
      height: box.height + pad * 2,
    },
  });
}

test.use({ viewport: { width: 1280, height: 900 } });

test("capability, control chart and the row-index warning", async ({ page }) => {
  await page.goto("/");
  await page.setInputFiles('input[type="file"]', CSV);

  // The panel auto-selects diameter_mm, skipping the part-number column.
  await expect(page.getByText("diameter_mm — selected")).toBeVisible();

  // Shot 1: the row-index guard. Select `part` to make the warning appear,
  // then switch back -- this is the one figure that shows capstat refusing to
  // compute something confidently wrong.
  await page.getByRole("radio").first().check();
  const warning = page.getByText("this looks like a row number");
  await expect(warning).toBeVisible();
  await shoot(page.getByLabel("Data upload"), "row-index-warning.png");
  await page.getByRole("radio").nth(1).check();
  await expect(page.getByText("diameter_mm — selected")).toBeVisible();

  // Shot 2: the capability report. The demo data breaks normality, so this
  // lands on the ISO 22514 percentile path -- Pp/Ppk only, with Cp/Cpk stating
  // why they are absent rather than showing a dash.
  await page.getByLabel("LSL").fill(LSL);
  await page.getByLabel("USL").fill(USL);
  await page.getByRole("button", { name: "Compute capability" }).click();
  const capability = page.getByLabel("Capability analysis");
  // exact: the warnings list below also contains the string "Pp/Ppk".
  await expect(capability.getByText("Ppk", { exact: true })).toBeVisible();
  await expect(
    capability.getByText("not defined on the percentile path").first(),
  ).toBeVisible();
  await shoot(capability, "capability.png");

  // Shot 3: I-MR with the run-rule flags. The process drifts and excursions at
  // part 31, so this is not a chart of a well-behaved process on purpose.
  await shoot(page.getByLabel("Control chart"), "control-chart.png");
});

test("gage r&r", async ({ page }) => {
  await page.goto("/gage-rr");
  const panel = page.getByLabel("Gage R&R");
  await panel.getByRole("button", { name: /compute/i }).click();
  await expect(panel.getByText(/ndc/i).first()).toBeVisible();
  await shoot(panel, "gage-rr.png");
});
