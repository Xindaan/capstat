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

// The percentile path: no within/between split, so Cp and Cpk do not exist —
// and a one-sided spec on top, so Pp has no value either, for a different
// reason. The UI has to tell those two apart.
const CAPABILITY_PERCENTILE = {
  path: "percentile",
  pp: null,
  ppk: 0.942,
  box_cox: null,
  normal: null,
  percentile: { distribution: "weibull_min", pp: null, ppk: 0.942 },
  normality: {
    normal: false,
    recommendation: "Normal model rejected; use the non-normal path.",
  },
  rationale:
    "the normal model was rejected and Box-Cox failed to fix it, so the ISO 22514 percentile method was used instead.",
  warnings: ["the percentile method yields long-term (Pp/Ppk) indices only."],
};

// A realistic spreadsheet: the row number comes first, the measurement second.
// 1, 2, 3 ... is valid numeric data, so nothing downstream would object to
// analysing it -- which is exactly why the UI has to.
const INGEST_WITH_ROW_INDEX = {
  n_rows: VALUES.length,
  columns: [
    {
      name: "part",
      values: Array.from({ length: VALUES.length }, (_, i) => i + 1),
      dropped_missing: 0,
    },
    { name: "diameter_mm", values: VALUES, dropped_missing: 0 },
  ],
  ignored_columns: [],
  warnings: [],
};

async function mockApi(
  page: Page,
  capability: unknown = CAPABILITY,
  ingest: unknown = INGEST,
) {
  const json = (body: unknown) => ({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
  await page.route("**/ingest", (r) => r.fulfill(json(ingest)));
  await page.route("**/compute/capability/analyze", (r) =>
    r.fulfill(json(capability)),
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

test("an index with no value says why, instead of showing a bare dash", async ({
  page,
}) => {
  // A real user asked "did I enter the limits wrong?" on seeing two empty
  // Cp/Cpk cards. They had not: on the percentile path those indices do not
  // exist. An absent value and a rejected input must not look the same.
  await mockApi(page, CAPABILITY_PERCENTILE);
  await page.goto("/");
  await page
    .locator('input[type="file"]')
    .setInputFiles({
      name: "sample.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("measurement\n10.0\n10.1\n"),
    });

  // USL only, so Pp is absent too — for a different reason.
  await page.getByLabel("USL").fill("10.3");
  await page.getByRole("button", { name: "Compute capability" }).click();

  const cards = page.locator('[aria-label="Capability analysis"] .grid > div');
  await expect(cards.filter({ hasText: "Cp" }).first()).toContainText(
    "not defined on the percentile path",
  );
  await expect(cards.filter({ hasText: "Pp" }).first()).toContainText(
    "needs both spec limits",
  );
  // Ppk is defined by one limit, so it still shows a number.
  await expect(cards.filter({ hasText: "Ppk" }).first()).toContainText("0.942");
});

test("a row-index column is neither auto-selected nor silently analysed", async ({
  page,
}) => {
  // The demo CSV starts with `part` = 1..60. Auto-selecting it produced Pp 0.006
  // -- arithmetically correct, entirely meaningless, and with no warning, since
  // consecutive integers are perfectly good numbers.
  await mockApi(page, CAPABILITY, INGEST_WITH_ROW_INDEX);
  await page.goto("/");
  await page
    .locator('input[type="file"]')
    .setInputFiles({
      name: "shaft.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("part,diameter_mm\n1,10.0\n2,10.1\n"),
    });

  // The measurement is preselected, not the index.
  await expect(page.getByText("diameter_mm — selected")).toBeVisible();
  await expect(page.getByText(/looks like a row number/)).toHaveCount(0);

  // Picking the index anyway is allowed -- but it says what it is.
  await page.getByRole("radio").first().check();
  await expect(page.getByText("part — selected")).toBeVisible();
  await expect(page.getByText(/looks like a row number/)).toBeVisible();
});
