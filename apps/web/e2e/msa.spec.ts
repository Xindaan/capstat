import { test, expect, type Page } from "@playwright/test";

import { gotoReady } from "./support";

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
  warnings: [
    {
      code: "mock.bias-changes-across-the-range-the-measur",
      message:
        "bias changes across the range; the measurement system is not linear",
    },
  ],
  linearity_significant: true,
};

const POINTS = Array.from({ length: 20 }, (_, i) => 10 + (i % 3) * 0.01);
const STABILITY = {
  stable: false,
  warnings: [
    {
      code: "stability.not-stable",
      message:
        "the measurement system is not stable: 2 out-of-control point(s)",
    },
  ],
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
  await gotoReady(page, "/msa");

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
  // Both control charts draw (SVG, so the report prints as vector). Scoped to
  // the panel: Next's dev overlay has SVGs of its own.
  await expect(page.locator('[aria-label="Stability study"] svg')).toHaveCount(
    2,
  );
});

test("printing drops the controls and keeps the report", async ({ page }) => {
  await mockApi(page);
  await gotoReady(page, "/msa");
  await page.getByRole("button", { name: "Check stability" }).click();
  await expect(page.locator('[aria-label="Stability study"] svg')).toHaveCount(
    2,
  );

  await page.emulateMedia({ media: "print" });

  // Navigation and actions are not part of a report.
  await expect(page.locator("nav")).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Check stability" }),
  ).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Print / save as PDF" }),
  ).toBeHidden();

  // The substance survives, charts included (SVG -> vector in the PDF).
  // exact: the page h1 ("Bias, linearity, stability") contains this word too.
  await expect(
    page.getByRole("heading", { name: "Stability", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Not stable", { exact: true })).toBeVisible();
  await expect(
    page.locator('[aria-label="Stability study"] svg').first(),
  ).toBeVisible();
});

test("msa is reachable from the nav", async ({ page }) => {
  await gotoReady(page, "/");
  await page.getByRole("link", { name: "Bias & linearity" }).click();
  await expect(page).toHaveURL(/\/msa$/);
  await expect(
    page.getByRole("button", { name: "Compute bias" }),
  ).toBeVisible();
});

test("an msa study saves all three panels and loads them back", async ({
  page,
}) => {
  await gotoReady(page, "/msa");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Save study" }).click(),
  ]);
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const saved = JSON.parse(Buffer.concat(chunks).toString());

  expect(saved.page).toBe("msa");
  // The three studies are independent, and the document keeps them apart.
  expect(Object.keys(saved.inputs).sort()).toEqual([
    "bias",
    "linearity",
    "stability",
  ]);
  expect(saved.inputs.bias.reference).toBe("36");
  expect(saved).not.toHaveProperty("results");

  await page.getByLabel("Load study file").setInputFiles({
    name: "study.json",
    mimeType: "application/json",
    buffer: Buffer.from(
      JSON.stringify({
        format: "capstat-study",
        schema_version: 1,
        page: "msa",
        inputs: {
          bias: { readings: "1, 2, 3", reference: "2.5" },
          linearity: {
            rows: [{ reference: "7", readings: "7.1, 7.2" }],
            processVariation: "14.1",
          },
          stability: { readings: "5, 6, 7" },
        },
      }),
    ),
  });

  // Scope per panel: "Reference" also names the linearity rows' own inputs.
  // All three studies must come back, not just the first.
  await expect(
    page.getByLabel("Bias study").getByLabel("Reference", { exact: true }),
  ).toHaveValue("2.5");
  await expect(
    page.getByLabel("Linearity study").getByLabel("Process variation"),
  ).toHaveValue("14.1");
  await expect(
    page.getByLabel("Stability study").getByLabel("Readings"),
  ).toHaveValue("5, 6, 7");
});
