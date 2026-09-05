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
  warnings: [
    {
      code: "ingest.non-numeric-columns-ignored",
      message: "Ignored non-numeric column(s): operator.",
    },
  ],
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
  phase: "I",
  sigma_within: 0.05,
  subgroup_size: 1,
  subgroups: VALUES.length,
  warnings: [],
  location: {
    name: "individuals",
    points: VALUES,
    limits: { center: 10, lower: 9.8, upper: 10.2 },
    violations: [],
    in_control: true,
  },
  dispersion: {
    name: "moving range",
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
  warnings: [
    {
      code: "nonnormal.percentile-no-cpk",
      message: "the percentile method yields long-term (Pp/Ppk) indices only.",
    },
  ],
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

// Subgrouped answers (T-0075). `capability` returns a report, not the decision
// path -- Box-Cox and the percentile fit both work on a flat sample, so there
// is no path to choose with subgroups.
const CAPABILITY_SUBGROUPS = {
  n: 30,
  subgroup_size: 5,
  subgroups: 6,
  mean: 10,
  sigma_within: 0.04,
  sigma_overall: 0.058,
  within_method: "pooled",
  lsl: 9.7,
  usl: 10.3,
  target: null,
  cp: 2.5,
  cpl: 2.5,
  cpu: 2.5,
  cpk: 2.5,
  cpm: null,
  pp: 1.72,
  ppl: 1.72,
  ppu: 1.72,
  ppk: 1.72,
  normality: {
    n: 30,
    alpha: 0.05,
    normal: true,
    recommendation: "Normal model not rejected.",
    warnings: [],
    lag1_autocorrelation: 0.1,
    anderson_darling: {
      test: "anderson-darling",
      n: 30,
      statistic: 0.3,
      p_value: 0.5,
      alpha: 0.05,
      normal: true,
    },
    shapiro_wilk: {
      test: "shapiro-wilk",
      n: 30,
      statistic: 0.98,
      p_value: 0.6,
      alpha: 0.05,
      normal: true,
    },
  },
  warnings: [],
  stability_ratio: 1.45,
};

const XBAR_R = {
  in_control: true,
  phase: "I",
  sigma_within: 0.04,
  subgroup_size: 5,
  subgroups: 6,
  warnings: [],
  location: {
    name: "X-bar",
    points: [10.0, 10.02, 9.99, 10.01, 10.0, 9.98],
    limits: { center: 10, lower: 9.94, upper: 10.06 },
    violations: [],
    in_control: true,
  },
  dispersion: {
    name: "R",
    points: [0.1, 0.12, 0.09, 0.11, 0.1, 0.08],
    limits: { center: 0.1, lower: 0, upper: 0.21 },
    violations: [],
    in_control: true,
  },
};

async function mockApi(
  page: Page,
  capability: unknown = CAPABILITY,
  ingest: unknown = INGEST,
  chart: unknown = CHART,
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
  await page.route("**/control-chart/i-mr", (r) => r.fulfill(json(chart)));
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

test("a known baseline makes the chart Phase II, and half a baseline does not", async ({
  page,
}) => {
  // T-0076. Phase I limits are estimated from the data being plotted, so a
  // sustained shift drags the centre towards itself -- which does not merely
  // soften the signal, it condemns the subgroups that were fine. A baseline
  // from a stable period stops both.
  const sent: Array<{ center: number | null; sigma: number | null }> = [];
  await mockApi(page);
  await page.route("**/control-chart/i-mr", async (r) => {
    const body = r.request().postDataJSON();
    sent.push({ center: body.center, sigma: body.sigma });
    return r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...CHART,
        phase: body.center != null && body.sigma != null ? "II" : "I",
      }),
    });
  });
  await gotoReady(page, "/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n"),
  });
  await expect(page.getByText("Phase I", { exact: true })).toBeVisible();

  // Half a baseline is still Phase I, and the panel says why rather than
  // sending a known centre with an estimated sigma.
  await page.getByLabel("Known centre").fill("10");
  await expect(
    page.getByText(/needs both a centre and a positive sigma/),
  ).toBeVisible();
  await expect(page.getByText("Phase I", { exact: true })).toBeVisible();
  expect(sent.at(-1)).toEqual({ center: null, sigma: null });

  // Both halves: Phase II, and the baseline is what goes on the wire.
  await page.getByLabel("Known sigma").fill("0.05");
  await expect(page.getByText("Phase II", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/Phase II: the limits come from these numbers/),
  ).toBeVisible();
  expect(sent.at(-1)).toEqual({ center: 10, sigma: 0.05 });
});

test("a subgroup size reaches the subgrouped endpoints, not the individuals ones", async ({
  page,
}) => {
  // The point of T-0075. capstat-core has taken subgroups since T-0005 and
  // xbar_r_chart has existed since T-0007; neither was reachable from the page,
  // so every Cp/Cpk the app showed rested on a moving-range sigma -- the
  // fallback the library warns about on every such report.
  const called: string[] = [];
  await mockApi(page);
  await page.route("**/compute/capability", (r) => {
    called.push("capability");
    return r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(CAPABILITY_SUBGROUPS),
    });
  });
  await page.route("**/control-chart/xbar-r", (r) => {
    called.push("xbar-r");
    return r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(XBAR_R),
    });
  });
  await gotoReady(page, "/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });

  // 30 values, subgroups of 5: six complete subgroups and nothing left over.
  await page.getByLabel("Subgroup size").fill("5");
  await expect(
    page.getByText(/6 subgroups from 30 measurements/),
  ).toBeVisible();
  await expect(page.getByTestId("subgroup-leftover")).toHaveCount(0);

  // The chart pair switched, and its name comes from what was computed.
  await expect(page.getByText("Control chart (X-bar / R)")).toBeVisible();

  await page.getByLabel("LSL").fill("9.7");
  await page.getByLabel("USL").fill("10.3");
  await page.getByRole("button", { name: "Compute capability" }).click();

  // Cp/Cpk now come from a within-subgroup sigma rather than a moving range.
  await expect(page.getByText("2.500").first()).toBeVisible();
  await expect(page.getByText(/Subgroups of 5/)).toBeVisible();
  await expect(
    page.getByText(/decision path is not run on subgrouped data/),
  ).toBeVisible();

  expect(called).toContain("capability");
  expect(called).toContain("xbar-r");
  // And the individuals endpoints were not used.
  expect(called).not.toContain("analyze");
});

test("a column that does not divide evenly says which values are left out", async ({
  page,
}) => {
  // Silently analysing 28 of 30 measurements would be a different study with
  // nothing on screen to say so.
  await mockApi(page);
  await gotoReady(page, "/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n"),
  });

  await page.getByLabel("Subgroup size").fill("4");
  const note = page.getByTestId("subgroup-leftover");
  await expect(note).toBeVisible();
  await expect(note).toContainText(
    "the last 2 values are not part of any subgroup",
  );
});

test("the capability colouring follows the requirement you state, not 1.33", async ({
  page,
}) => {
  // The discriminating case for T-0073. The mocked Cpk is exactly 1.33: it
  // meets a 1.33 requirement and falls short of a 1.67 one, and the old fixed
  // threshold called it green for both. An automotive customer asking for 1.67
  // would have read a clean bill of health off a process that misses their
  // specification.
  await mockApi(page);
  await gotoReady(page, "/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });
  await page.getByLabel("LSL").fill("9.7");
  await page.getByLabel("USL").fill("10.3");
  await page.getByRole("button", { name: "Compute capability" }).click();

  const cpk = page.locator("div").filter({ hasText: /^Cpk$/ }).locator("..");
  await expect(cpk.getByText("1.330")).toBeVisible();

  // Default requirement 1.33: the index meets it.
  const required = page.getByLabel("Required Cpk");
  await expect(required).toHaveValue("1.33");
  await expect(cpk.locator(".text-emerald-600")).toHaveCount(1);
  await expect(
    page.getByText(/Coloured against a required index of 1.33/),
  ).toBeVisible();

  // Raise the requirement and the same number is no longer green. Nothing was
  // recomputed -- the threshold never reaches the API.
  await required.fill("1.67");
  await expect(cpk.locator(".text-emerald-600")).toHaveCount(0);
  await expect(cpk.locator(".text-amber-600")).toHaveCount(1);
  await expect(
    page.getByText(/Coloured against a required index of 1.67/),
  ).toBeVisible();

  // A requirement that cannot be read colours nothing, rather than falling
  // back to a threshold nobody asked for.
  await required.fill("");
  await expect(cpk.locator(".text-emerald-600")).toHaveCount(0);
  await expect(cpk.locator(".text-amber-600")).toHaveCount(0);
  await expect(page.getByText(/No required index is set/)).toBeVisible();
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

test("a warning arrives with the code a program can act on", async ({
  page,
}) => {
  // The point of T-0074, end to end: the code is set in capstat-core, survives
  // the HTTP contract as {code, message}, and reaches the DOM. Before it, a
  // consumer wanting to react to "this path has no Cpk" had to match English
  // prose, so rewording a sentence broke it silently.
  await mockApi(page, CAPABILITY_PERCENTILE);
  await gotoReady(page, "/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });
  await page.getByLabel("USL").fill("10.3");
  await page.getByRole("button", { name: "Compute capability" }).click();

  const warning = page.locator("li[data-code='nonnormal.percentile-no-cpk']");
  await expect(warning).toHaveCount(1);
  // Both halves survive: the person still reads the sentence.
  await expect(warning).toContainText("long-term (Pp/Ppk) indices only");
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

test("a failed run-rule request is reported, not rendered as a clean chart", async ({
  page,
}) => {
  // The worst wrong answer this app can give. "No violations" is a claim about
  // the process; if the rules never ran, there is no claim to make, and saying
  // one anyway is indistinguishable from a genuinely stable chart (T-0052).
  await mockApi(page);
  await page.route("**/rules/nelson", (r) =>
    r.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "the rules engine fell over" }),
    }),
  );

  await gotoReady(page, "/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });

  await expect(
    page.getByText(/The run rules could not be applied/),
  ).toBeVisible();
  await expect(page.getByText(/the rules engine fell over/)).toBeVisible();
  // The chart itself still computed, so it stays on screen -- only the rule
  // verdict is withdrawn.
  await expect(page.getByLabel("Control chart")).toBeVisible();
  await expect(page.getByText(/No Nelson run-rule violations/)).toHaveCount(0);
});

test("the charts carry an accessible name that says what they show", async ({
  page,
}) => {
  // A screen reader got nothing for the central claim of the page: three bare
  // divs (T-0060). The name is built from the same props the chart draws, so it
  // cannot drift from the picture.
  await mockApi(page);
  await gotoReady(page, "/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });

  await expect(
    page.getByRole("img", { name: /Individuals chart, 30 points, in control/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("img", { name: /Moving range chart/ }),
  ).toBeVisible();
});

test("an out-of-control chart names the points, not just the state", async ({
  page,
}) => {
  // "Out of control" without the where is barely more use than silence.
  await mockApi(page, undefined, undefined, {
    ...CHART,
    in_control: false,
    location: { ...CHART.location, violations: [2, 5], in_control: false },
  });
  await gotoReady(page, "/");
  await page.locator('input[type="file"]').setInputFiles({
    name: "sample.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n10.1\n"),
  });

  await expect(
    page.getByRole("img", {
      name: /Individuals chart, 30 points, out of control at points 3, 6/,
    }),
  ).toBeVisible();
});

test("a second file replaces the analyses rather than reusing them", async ({
  page,
}) => {
  // A second file must not leave the first one's report on screen. The case
  // that would break it is a column sharing name, length, first and last value
  // with the one before -- the four parts of the remount key this page used to
  // carry -- dropped straight onto the dropzone without the "Upload another
  // file" reset.
  //
  // It passes against that old key as well, and that is worth recording rather
  // than dressing up: what actually resets the panels is UploadPanel clearing
  // its selection before the request, so `column` goes through null and both
  // unmount regardless. The test stays because that property is load-bearing
  // and nothing else pins it -- remove the intermediate null and this is what
  // catches it (T-0071).
  const edited = {
    ...INGEST,
    columns: [
      {
        name: "measurement",
        values: VALUES.map((v, i) =>
          i === 0 || i === VALUES.length - 1 ? v : Number((v + 0.5).toFixed(4)),
        ),
        dropped_missing: 0,
      },
    ],
  };

  await mockApi(page);
  await gotoReady(page, "/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "first.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n"),
  });
  await page.getByLabel("LSL").fill("9.7");
  await page.getByLabel("USL").fill("10.3");
  await page.getByRole("button", { name: "Compute capability" }).click();
  await expect(page.getByText("1.310")).toBeVisible();

  await page.route("**/ingest", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(edited),
    }),
  );
  await page.locator('input[type="file"]').setInputFiles({
    name: "second.csv",
    mimeType: "text/csv",
    buffer: Buffer.from("measurement\n10.0\n"),
  });

  await expect(page.getByText(/Parsed/)).toContainText("second.csv");
  // The old report described data that is no longer loaded.
  await expect(page.getByText("1.310")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Compute capability" }),
  ).toBeVisible();
});
