import { test, expect, type Page } from "@playwright/test";

// Faithful-shaped SamplingPlanOut / SamplingPlanReportOut / OCCurveOut /
// LotDecisionOut. The page is pre-filled with the published example that
// designs to n = 144, Ac = 4, so a single click posts real inputs and these
// stand in for the API's replies.
const PLAN = {
  sample_size: 144,
  acceptance_number: 4,
  lot_size: 5000,
  rejection_number: 5,
};

const REPORT = {
  plan: PLAN,
  model: "binomial",
  aql: 0.01,
  ltpd: 0.05,
  producer_risk: 0.01534843,
  consumer_risk: 0.1487162,
  probability_accept_at_aql: 0.98465157,
  probability_accept_at_ltpd: 0.1487162,
  indifference_quality: 0.03242,
  aoql: { aoql: 0.0182, at_fraction_defective: 0.0243 },
  ati_at_aql: 218.5,
  warnings: [
    "AOQ, the AOQL and ATI describe rectifying inspection -- rejected lots screened 100 % and their defectives replaced. Without that screening they do not apply.",
    "the AOQL (0.0182) is the worst *average* outgoing quality over a stream of lots. Individual outgoing lots can be worse; it bounds no single lot.",
  ],
};

const CURVE = {
  plan: PLAN,
  model: "binomial",
  fraction_defective: [0.0, 0.01, 0.02, 0.03, 0.05, 0.08],
  probability_accept: [1.0, 0.98465157, 0.81, 0.5656415, 0.1487162, 0.004],
};

const DECISION = {
  plan: PLAN,
  defectives: 2,
  accepted: true,
  sample_fraction_defective: 0.0139,
  warnings: [
    "accepting this lot is a decision about a stream of lots, not evidence that this lot is good: a plan is chosen so that lots as bad as the LTPD are usually caught, and 'usually' is the whole guarantee.",
  ],
};

const json = (body: unknown) => ({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify(body),
});

async function mockApi(page: Page) {
  // One route per endpoint the page calls: an unmocked fetch would hang, since
  // no Python backend runs during e2e.
  await page.route("**/compute/acceptance-sampling/design", (r) =>
    r.fulfill(json(PLAN)),
  );
  await page.route("**/compute/acceptance-sampling/evaluate", (r) =>
    r.fulfill(json(REPORT)),
  );
  await page.route("**/compute/acceptance-sampling/oc-curve", (r) =>
    r.fulfill(json(CURVE)),
  );
  await page.route("**/compute/acceptance-sampling/inspect", (r) =>
    r.fulfill(json(DECISION)),
  );
}

test("acceptance sampling: design the pre-filled plan and show the risks", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/acceptance-sampling");

  await page.getByRole("button", { name: "Design the plan" }).click();

  await expect(page.getByText("Sample size")).toBeVisible();
  // exact: the intro paragraph mentions n = 144 too.
  await expect(page.getByText("144", { exact: true })).toBeVisible();
  await expect(page.getByText("4 or fewer")).toBeVisible();
  // exact: the input labels above are "Producer risk %" / "Consumer risk %";
  // these two are the result cards, which is what the click produced.
  await expect(page.getByText("Producer risk", { exact: true })).toBeVisible();
  await expect(page.getByText("Consumer risk", { exact: true })).toBeVisible();
  // The OC curve is the substance of the page, and it is an SVG. Scope the
  // locator to the panel: Next's dev overlay injects SVGs of its own.
  await expect(
    page.locator('[aria-label="Acceptance sampling"] svg').first(),
  ).toBeVisible();
  // The warning that the AOQL bounds no single lot must survive to the page.
  await expect(page.getByText(/bounds no single lot/)).toBeVisible();
});

test("acceptance sampling: the plan actually posted is the one on screen", async ({
  page,
}) => {
  const requested: unknown[] = [];
  await mockApi(page);
  await page.route("**/compute/acceptance-sampling/evaluate", async (r) => {
    requested.push(r.request().postDataJSON());
    await r.fulfill(json(REPORT));
  });
  await page.goto("/acceptance-sampling");

  await page.getByRole("button", { name: "Judge this plan" }).click();

  // Percent in the boxes, fractions on the wire: the conversion is the one
  // place a unit slip would be invisible in the rendered output.
  expect(requested.at(-1)).toEqual({
    plan: { sample_size: 144, acceptance_number: 4, lot_size: 5000 },
    aql: 0.01,
    ltpd: 0.05,
    model: "binomial",
  });
});

test("acceptance sampling: a lot decision is accept or reject, and says so", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/acceptance-sampling");
  await page.getByRole("button", { name: "Judge this plan" }).click();

  await page.getByRole("button", { name: "Decide the lot" }).click();

  await expect(page.getByText("Accept", { exact: true })).toBeVisible();
  await expect(
    page.getByText(/not evidence that this lot is good/),
  ).toBeVisible();
});

test("acceptance sampling is reachable from the nav", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Acceptance sampling" }).click();
  await expect(page).toHaveURL(/\/acceptance-sampling$/);
  await expect(
    page.getByRole("button", { name: "Design the plan" }),
  ).toBeVisible();
});

test("acceptance sampling prints its report without the controls", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/acceptance-sampling");
  await page.getByRole("button", { name: "Design the plan" }).click();
  await expect(page.getByText("4 or fewer")).toBeVisible();

  await page.emulateMedia({ media: "print" });

  await expect(page.locator("nav")).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Design the plan" }),
  ).toBeHidden();
  await expect(page.getByLabel("Sampling model")).toBeHidden();
  // The result and its chart are what the printed page is for.
  await expect(page.getByText("4 or fewer")).toBeVisible();
  await expect(
    page.locator('[aria-label="Acceptance sampling"] svg').first(),
  ).toBeVisible();
});
