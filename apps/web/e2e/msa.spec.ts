import { test, expect, type Page } from "@playwright/test";

// Faithful-shaped responses for the three MSA endpoints. The panels are
// pre-filled, so a single click on each posts real data.
const BIAS = {
  n: 10,
  reference: 36.0,
  mean: 36.005,
  bias: 0.005,
  repeatability: 0.1092,
  std_error: 0.0345,
  t_statistic: 0.1448,
  p_value: 0.888,
  alpha: 0.05,
  ci_lower: -0.0731,
  ci_upper: 0.0831,
  warnings: [],
  bias_significant: false,
};

const LINEARITY = {
  n: 20,
  n_parts: 5,
  slope: -0.132,
  intercept: 1.408,
  r_squared: 0.9442,
  slope_std_error: 0.0075,
  slope_t_statistic: -17.6,
  slope_p_value: 1e-12,
  alpha: 0.05,
  percent_linearity: 13.2,
  process_variation: null,
  linearity: null,
  references: [7, 9, 11, 13, 15],
  part_mean_biases: [0.49, 0.16, 0.02, -0.28, -0.61],
  warnings: ["bias changes across the range; the measurement system is not linear"],
  linearity_significant: true,
};

const POINTS = Array.from({ length: 20 }, (_, i) => 10 + (i % 3) * 0.01);
const STABILITY = {
  stable: false,
  warnings: ["the measurement system is not stable: 2 out-of-control point(s)"],
  chart: {
    in_control: false,
    sigma_within: 0.02,
    subgroup_size: 1,
    subgroups: POINTS.length,
    warnings: [],
    location: {
      name: "Individuals",
      points: POINTS,
      limits: { center: 10.01, lower: 9.95, upper: 10.07 },
      violations: [18, 19],
      in_control: false,
    },
    dispersion: {
      name: "Moving range",
      points: POINTS.slice(1).map(() => 0.01),
      limits: { center: 0.01, lower: 0, upper: 0.03 },
      violations: [],
      in_control: true,
    },
  },
};

async function mockApi(page: Page) {
  const json = (body: unknown) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
  await page.route("**/compute/bias", (r) => r.fulfill(json(BIAS)));
  await page.route("**/compute/linearity", (r) => r.fulfill(json(LINEARITY)));
  await page.route("**/compute/stability", (r) => r.fulfill(json(STABILITY)));
}

test("msa: the three studies compute and report", async ({ page }) => {
  await mockApi(page);
  await page.goto("/msa");

  await page.getByRole("button", { name: "Compute bias" }).click();
  await expect(page.getByText("No bias")).toBeVisible();
  await expect(page.getByText(/straddles zero/)).toBeVisible();

  await page.getByRole("button", { name: "Compute linearity" }).click();
  await expect(page.getByText("% Linearity")).toBeVisible();
  await expect(page.getByText("Mean bias")).toBeVisible();
  await expect(page.getByText(/not linear/)).toBeVisible();

  await page.getByRole("button", { name: "Check stability" }).click();
  // exact: the warning below also contains "not stable".
  await expect(page.getByText("Not stable", { exact: true })).toBeVisible();
  // Both control charts draw.
  await expect(page.locator("canvas")).toHaveCount(2);
});

test("msa is reachable from the nav", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Bias & linearity" }).click();
  await expect(page).toHaveURL(/\/msa$/);
  await expect(page.getByRole("button", { name: "Compute bias" })).toBeVisible();
});
