import { test, expect, type Page } from "@playwright/test";

// A seeded, roughly-normal column so the histogram and control charts have
// something real to bin. The exact values do not matter -- the API is mocked.
const VALUES = Array.from({ length: 30 }, (_, i) =>
  Number((10 + Math.sin(i) * 0.1).toFixed(4)),
);

const INGEST = {
  n_rows: VALUES.length,
  columns: [{ name: "measurement", values: VALUES, dropped_missing: 0 }],
  ignored_columns: ["operator"],
  warnings: ["Ignored non-numeric column(s): operator."],
};

const CAPABILITY = {
  path: "normal",
  pp: 1.42,
  ppk: 1.31,
  box_cox: null,
  percentile: null,
  normal: { cp: 1.45, cpk: 1.33, mean: 10, sigma_overall: 0.058 },
  normality: {
    normal: true,
    recommendation: "Normal model not rejected; standard indices are defensible.",
  },
  rationale: "the normal model was not rejected, so the standard indices apply.",
  warnings: [],
};

const CHART = {
  in_control: true,
  sigma_within: 0.05,
  subgroup_size: 1,
  subgroups: VALUES.length,
  warnings: [],
  location: {
    name: "Individuals",
    points: VALUES,
    limits: { center: 10, lower: 9.8, upper: 10.2 },
    violations: [],
    in_control: true,
  },
  dispersion: {
    name: "Moving range",
    points: VALUES.slice(1).map((v, i) => Math.abs(v - VALUES[i])),
    limits: { center: 0.06, lower: 0, upper: 0.2 },
    violations: [],
    in_control: true,
  },
};

async function mockApi(page: Page) {
  const json = (body: unknown) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
  await page.route("**/ingest", (r) => r.fulfill(json(INGEST)));
  await page.route("**/compute/capability/analyze", (r) =>
    r.fulfill(json(CAPABILITY)),
  );
  await page.route("**/control-chart/i-mr", (r) => r.fulfill(json(CHART)));
  await page.route("**/rules/nelson", (r) => r.fulfill(json([])));
}

test("upload -> capability -> control chart", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");

  // Upload a file (the input is visually hidden but still settable).
  await page
    .locator('input[type="file"]')
    .setInputFiles({
      name: "sample.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("measurement\n10.0\n10.1\n"),
    });

  // Ingestion result: the parse summary, the ignored-column note, the picker.
  await expect(page.getByText(/Parsed/)).toContainText("sample.csv");
  await expect(page.getByText("Ignored non-numeric column(s): operator.")).toBeVisible();
  await expect(page.getByText("Choose the column to analyse")).toBeVisible();

  // Capability: enter limits and compute.
  await page.getByLabel("LSL").fill("9.7");
  await page.getByLabel("USL").fill("10.3");
  await page.getByRole("button", { name: "Compute capability" }).click();

  // Headline indices from the mocked decision-path response.
  await expect(page.getByText("1.310")).toBeVisible(); // Ppk
  await expect(page.getByText(/Path: Normal/)).toBeVisible();

  // Both panels draw a chart (capability histogram + the two control charts).
  // ECharts renders SVG here, so the report prints as vector. Scoped to the
  // panels: Next's dev overlay has SVGs of its own.
  await expect(page.getByText("Control chart (I-MR)")).toBeVisible();
  await expect(page.getByText("In control")).toBeVisible();
  await expect(
    page.locator('[aria-label="Capability analysis"] svg'),
  ).toHaveCount(1);
  await expect(page.locator('[aria-label="Control chart"] svg')).toHaveCount(2);
});
