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
