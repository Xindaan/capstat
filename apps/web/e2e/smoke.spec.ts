import { test, expect, type Page } from "@playwright/test";

import { gotoReady } from "./support";

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
    recommendation:
      "Normal model not rejected; standard indices are defensible.",
  },
  rationale:
    "the normal model was not rejected, so the standard indices apply.",
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
  await page.route("**/rules/catalogue", (r) =>
    r.fulfill(json({ nelson: NELSON_CATALOGUE, western_electric: {} })),
  );
}

// Trimmed copy of the API's catalogue; the panel fetches the wording rather
// than hard-coding it, so the test has to serve something.
const NELSON_CATALOGUE: Record<string, string> = {
  "1": "one point more than 3 sigma from the centre line",
  "2": "nine points in a row on the same side of the centre line",
  "3": "six points in a row all increasing, or all decreasing",
  "4": "fourteen points in a row alternating up and down",
  "5": "two out of three points in a row more than 2 sigma from the centre line, on the same side",
  "6": "four out of five points in a row more than 1 sigma from the centre line, on the same side",
  "7": "fifteen points in a row all within 1 sigma of the centre line",
  "8": "eight points in a row none within 1 sigma of the centre line, on both sides",
};

test("upload -> capability -> control chart", async ({ page }) => {
  await mockApi(page);
  await gotoReady(page, "/");

  // Upload a file (the input is visually hidden but still settable).
  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });

  // Ingestion result: the parse summary, the ignored-column note, the picker.
  await expect(page.getByText(/Parsed/)).toContainText("sample.csv");
  await expect(
    page.getByText("Ignored non-numeric column(s): operator."),
  ).toBeVisible();
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
  await gotoReady(page, "/");
  await page.locator('input[type="file"]').setInputFiles({
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
  await gotoReady(page, "/");
  await page.locator('input[type="file"]').setInputFiles({
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

test("the applied run rules are selectable, and the report names them", async ({
  page,
}) => {
  // What matters is not the checkbox but what reaches the API: a panel that
  // rendered a selection it did not apply would report violations of rules the
  // reader never asked for -- or stay silent about ones they did.
  const requested: number[][] = [];
  await mockApi(page);
  await page.route("**/rules/nelson", async (r) => {
    requested.push(r.request().postDataJSON().rules);
    await r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await gotoReady(page, "/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });

  // Default: the strongest four, and the label says so.
  await expect(
    page.getByText("No Nelson run-rule violations (rules 1–4)"),
  ).toBeVisible();
  // Poll, do not read once. The label is rendered from the checkbox state, not
  // from the response, so it appears *before* the request necessarily has --
  // reading `requested` at that moment is a race that lost about one run in
  // three under load. The claim here is about the request, so it has to wait
  // for the request.
  await expect.poll(() => requested.at(-1)).toEqual([1, 2, 3, 4]);

  // Adding rule 5 must reach the API and change the stated set.
  await page.getByRole("checkbox", { name: /Rule 5/ }).check();
  await expect(
    page.getByText("No Nelson run-rule violations (rules 1–5)"),
  ).toBeVisible();
  await expect.poll(() => requested.at(-1)).toEqual([1, 2, 3, 4, 5]);

  // Going beyond the default set says what it costs.
  await expect(
    page.getByText(/More rules means more false alarms/),
  ).toBeVisible();

  // A gapped selection must not be described as a range: "1-3" would claim
  // rule 2 was applied when it was not.
  await page.getByRole("checkbox", { name: /Rule 5/ }).uncheck();
  await page.getByRole("checkbox", { name: /Rule 2/ }).uncheck();
  await page.getByRole("checkbox", { name: /Rule 4/ }).uncheck();
  await expect(
    page.getByText("No Nelson run-rule violations (rules 1, 3)"),
  ).toBeVisible();
  await expect.poll(() => requested.at(-1)).toEqual([1, 3]);

  // Nothing selected: say that plainly rather than implying a clean chart.
  await page.getByRole("checkbox", { name: /Rule 1/ }).uncheck();
  await page.getByRole("checkbox", { name: /Rule 3/ }).uncheck();
  await expect(page.getByText("No run rules are applied.")).toBeVisible();

  // And the reset returns to the documented default.
  await page.getByRole("button", { name: "Reset to 1–4" }).click();
  await expect(
    page.getByText("No Nelson run-rule violations (rules 1–4)"),
  ).toBeVisible();
  await expect.poll(() => requested.at(-1)).toEqual([1, 2, 3, 4]);
});
