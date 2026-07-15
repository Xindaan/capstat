import { test, expect, type Page } from "@playwright/test";

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
  await page.goto("/gage-rr");

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
  await page.goto("/");
  await page.getByRole("link", { name: "Gage R&R" }).click();
  await expect(page).toHaveURL(/\/gage-rr$/);
  await expect(
    page.getByRole("button", { name: "Compute Gage R&R" }),
  ).toBeVisible();
});
