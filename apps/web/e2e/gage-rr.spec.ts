import { test, expect, type Page } from "@playwright/test";

import { gotoReady } from "./support";

// A faithful-shaped GageRRReportOut; the page is pre-filled with the AIAG grid,
// so clicking Compute posts real data and this stands in for the API's reply.
const REPORT = {
  method: "anova",
  n_parts: 5,
  n_operators: 3,
  n_trials: 3,
  interaction_included: false,
  interaction_pvalue: 0.9964,
  var_repeatability: 0.0468,
  var_operator: 0.0512,
  var_interaction: 0.0,
  var_part: 0.7978,
  var_reproducibility: 0.0512,
  var_gage_rr: 0.098,
  var_total: 0.8958,
  study_var_multiplier: 6.0,
  tolerance: null,
  pct_contribution_gage_rr: 10.94,
  pct_contribution_repeatability: 5.22,
  pct_contribution_reproducibility: 5.72,
  pct_contribution_part: 89.06,
  pct_study_var_gage_rr: 33.07,
  pct_study_var_repeatability: 22.85,
  pct_study_var_reproducibility: 23.91,
  pct_study_var_part: 94.37,
  pct_tolerance_gage_rr: null,
  ndc: 4,
  verdict: "unacceptable",
  ndc_adequate: false,
  warnings: [
    "gage R&R is 33.1% of study variation (> 30%): the measurement system is unacceptable",
  ],
};

async function mockApi(page: Page) {
  await page.route("**/compute/gage-rr", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(REPORT),
    }),
  );
}

test("gage r&r: compute the pre-filled study and show the verdict", async ({
  page,
}) => {
  await mockApi(page);
  await gotoReady(page, "/gage-rr");

  // The grid is pre-filled, so a single click computes.
  await page.getByRole("button", { name: "Compute Gage R&R" }).click();

  // Headline verdict + the variance breakdown table.
  await expect(page.getByText("% Study Var (GRR)")).toBeVisible();
  await expect(page.getByText("Repeatability (EV)")).toBeVisible();
  await expect(page.getByText("Reproducibility (AV)")).toBeVisible();
  await expect(page.getByText("Part (PV)")).toBeVisible();
  await expect(page.getByText(/unacceptable/)).toBeVisible();
});

test("gage r&r is reachable from the nav", async ({ page }) => {
  await gotoReady(page, "/");
  await page.getByRole("link", { name: "Gage R&R" }).click();
  await expect(page).toHaveURL(/\/gage-rr$/);
  await expect(
    page.getByRole("button", { name: "Compute Gage R&R" }),
  ).toBeVisible();
});

test("a gage r&r study saves and loads back", async ({ page }) => {
  await mockApi(page);
  await gotoReady(page, "/gage-rr");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Save study" }).click(),
  ]);
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const saved = JSON.parse(Buffer.concat(chunks).toString());

  expect(saved.page).toBe("gage-rr");
  expect(saved.inputs.parts).toBe(5);
  expect(saved.inputs.grid).toHaveLength(5);
  // Inputs only: a saved study never carries the variance table it produced.
  expect(saved).not.toHaveProperty("results");

  // A three-part study loads back and resizes the grid with it.
  await page.getByLabel("Load study file").setInputFiles({
    name: "study.json",
    mimeType: "application/json",
    buffer: Buffer.from(
      JSON.stringify({
        format: "capstat-study",
        schema_version: 1,
        page: "gage-rr",
        inputs: {
          parts: 3,
          operators: 2,
          trials: 2,
          grid: [
            [
              ["1", "2"],
              ["3", "4"],
            ],
            [
              ["5", "6"],
              ["7", "8"],
            ],
            [
              ["9", "10"],
              ["11", "12"],
            ],
          ],
          method: "average_range",
          tolerance: "0.5",
        },
      }),
    ),
  });

  await expect(page.getByLabel("Tolerance")).toHaveValue("0.5");
});

test("a damaged study file is refused by name, not rendered into a crash", async ({
  page,
}) => {
  // Before T-0055 the `inputs` object was cast unchecked, so `"grid": 1`
  // reached `grid.map` and took the page down with an unhandled TypeError. A
  // file the user hand-edited must not be able to do that.
  const crashes: string[] = [];
  page.on("pageerror", (error) => crashes.push(error.message));

  await gotoReady(page, "/gage-rr");
  await page.getByLabel("Load study file").setInputFiles({
    name: "broken.json",
    mimeType: "application/json",
    buffer: Buffer.from(
      JSON.stringify({
        format: "capstat-study",
        schema_version: 1,
        page: "gage-rr",
        inputs: { parts: 3, grid: 1 },
      }),
    ),
  });

  await expect(page.getByText(/study file is damaged/i)).toBeVisible();
  await expect(page.getByText(/"grid" should be a list/)).toBeVisible();
  // Nothing was half-restored: the example study is still on screen and usable.
  await expect(page.getByRole("button", { name: "Compute" })).toBeEnabled();
  expect(crashes).toEqual([]);
});

test("a fault deep inside a grid names the cell, not the grid", async ({
  page,
}) => {
  await gotoReady(page, "/gage-rr");
  await page.getByLabel("Load study file").setInputFiles({
    name: "broken.json",
    mimeType: "application/json",
    buffer: Buffer.from(
      JSON.stringify({
        format: "capstat-study",
        schema_version: 1,
        page: "gage-rr",
        inputs: {
          parts: 1,
          operators: 1,
          trials: 2,
          grid: [[["1", 2]]],
        },
      }),
    ),
  });

  await expect(page.getByText(/"grid\.0\.0\.1" should be text/)).toBeVisible();
});

test("the card colours follow the verdict the API states, not a local threshold", async ({
  page,
}) => {
  // The discriminating case for T-0058. The percentage says "good" on the old
  // 10/30 rule; the verdict says "unacceptable". If the panel still owned the
  // thresholds it would paint this green, and the card would then contradict
  // the warning printed underneath it -- the exact discrepancy the change
  // exists to make impossible.
  await page.route("**/compute/gage-rr", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...REPORT,
        pct_study_var_gage_rr: 5.0,
        ndc: 40,
        verdict: "unacceptable",
        ndc_adequate: false,
      }),
    }),
  );

  await gotoReady(page, "/gage-rr");
  await page.getByRole("button", { name: "Compute" }).click();

  const grr = page.getByText("% Study Var (GRR)").locator("..");
  await expect(grr.locator(".text-red-600")).toBeVisible();
  await expect(grr.locator(".text-emerald-600")).toHaveCount(0);

  const ndc = page.getByText("ndc", { exact: true }).locator("..");
  await expect(ndc.locator(".text-red-600")).toBeVisible();
});

test("a gage with nothing to judge is not painted green", async ({ page }) => {
  // `null` is "not judged" -- a gage whose own variance is zero. The old ndc
  // colouring fell through to emerald there, which reads as a clean bill of
  // health for a study that established nothing.
  await page.route("**/compute/gage-rr", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...REPORT,
        pct_study_var_gage_rr: null,
        ndc: null,
        verdict: null,
        ndc_adequate: null,
      }),
    }),
  );

  await gotoReady(page, "/gage-rr");
  await page.getByRole("button", { name: "Compute" }).click();

  const ndc = page.getByText("ndc", { exact: true }).locator("..");
  await expect(ndc.locator(".text-emerald-600")).toHaveCount(0);
  await expect(ndc.locator(".text-red-600")).toHaveCount(0);
  // The value reads as absent rather than as a verdict. (Both the label and
  // the value carry text-muted, hence the count rather than a visibility
  // assertion on a locator that legitimately matches twice.)
  await expect(ndc.getByText("—")).toBeVisible();
});

test("typing a two-digit dimension does not eat the grid", async ({ page }) => {
  // Selecting the field and typing "10" passed through "1", which was clamped
  // up to the minimum of 2 and truncated the grid to two parts -- the
  // measurements for parts 3 to 5 were gone before the second digit landed,
  // with no undo (T-0065). The resize now happens once, on leaving the field.
  await gotoReady(page, "/gage-rr");

  const thirdPart = page.getByLabel("Part 3, operator A, trial 1");
  await expect(thirdPart).toHaveValue("4.34");

  const parts = page.getByLabel("Parts", { exact: true });
  await parts.click();
  await parts.press("ControlOrMeta+a");
  await parts.pressSequentially("10");
  await parts.blur();

  await expect(parts).toHaveValue("10");
  await expect(page.locator("tbody tr")).toHaveCount(10);
  // The rows that were already filled in still hold what the example put there.
  await expect(thirdPart).toHaveValue("4.34");
  await expect(page.getByLabel("Part 1, operator A, trial 1")).toHaveValue(
    "3.29",
  );
  await expect(page.getByLabel("Part 5, operator C, trial 3")).toHaveValue(
    "1.55",
  );
  // The rows it added are empty, waiting to be typed into.
  await expect(page.getByLabel("Part 10, operator A, trial 1")).toHaveValue("");

  // Beyond the cap the value is refused rather than clamped, so nothing resizes
  // and the grid on screen is still the one the user built.
  await parts.click();
  await parts.press("ControlOrMeta+a");
  await parts.pressSequentially("500");
  await parts.blur();
  await expect(parts).toHaveValue("10");
  await expect(page.locator("tbody tr")).toHaveCount(10);
});
